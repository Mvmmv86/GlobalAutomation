#!/usr/bin/env python3
"""
Bridge to connect TradingView webhooks to real exchange integration
This bridges the legacy system to the enhanced multi-exchange system
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID
import structlog

from infrastructure.database.connection_transaction_mode import transaction_db
from application.services.secure_exchange_service import SecureExchangeService
from application.services.exchange_credentials_service import ExchangeCredentialsService
from infrastructure.security.encryption_service import EncryptionService

logger = structlog.get_logger()


class RealExchangeBridge:
    """Bridge between TradingView webhooks and real exchange integration"""

    def __init__(self):
        """Initialize the bridge with required services"""
        # Initialize encryption service
        encryption_service = EncryptionService()
        
        # Initialize credentials service
        self.credentials_service = ExchangeCredentialsService(encryption_service)
        
        # Initialize secure exchange service
        self.secure_exchange_service = SecureExchangeService(self.credentials_service)

    async def process_tradingview_webhook(
        self, webhook_payload: Dict[str, Any], webhook_delivery_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process TradingView webhook using real exchange integration
        
        Args:
            webhook_payload: Payload from TradingView
            webhook_delivery_id: ID of webhook delivery record
            
        Returns:
            Processing result with order details
        """
        try:
            logger.info("🌉 Processing webhook via REAL exchange bridge")
            
            # Step 1: Validate payload
            validation_result = self._validate_webhook_payload(webhook_payload)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "stage": "validation",
                }

            # Step 2: Extract order data
            order_data = self._extract_order_data(webhook_payload)
            logger.info(
                f"📊 Processing order: {order_data['symbol']} {order_data['side']} {order_data['quantity']}"
            )

            # Step 3: Get user's active exchange accounts
            user_id = await self._get_default_user_id()  # For demo, use default user
            if not user_id:
                return {
                    "success": False,
                    "error": "No user found for exchange integration",
                    "stage": "user_lookup",
                }

            # Step 4: Get exchange accounts
            exchange_accounts = await self._get_user_exchange_accounts(user_id)
            if not exchange_accounts:
                return {
                    "success": False,
                    "error": "No active exchange accounts found",
                    "stage": "account_lookup",
                }

            # Step 5: Select exchange account (use first active Binance account)
            selected_account = self._select_exchange_account(exchange_accounts, order_data)
            if not selected_account:
                return {
                    "success": False,
                    "error": "No suitable exchange account found",
                    "stage": "account_selection",
                }

            logger.info(f"🏦 Using exchange account: {selected_account['name']} ({selected_account['exchange']})")

            # Step 6: Create order record in database
            order_id = await self._create_order_in_database(order_data, webhook_delivery_id)

            # Step 7: Execute order via SecureExchangeService
            try:
                exchange_result = await self.secure_exchange_service.create_order(
                    account_id=UUID(selected_account['id']),
                    user_id=user_id,
                    symbol=order_data['symbol'],
                    side=order_data['side'],
                    order_type=order_data['order_type'],
                    quantity=str(order_data['quantity']),
                    price=str(order_data['price']) if order_data['price'] else None,
                )
                
                logger.info(f"🎯 Exchange order result: {exchange_result.get('order_id', 'unknown')}")
                
                # Step 8: Update order record with result
                await self._update_order_with_result(order_id, exchange_result)
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "exchange_result": exchange_result,
                    "exchange_account": selected_account['name'],
                    "exchange_type": selected_account['exchange'],
                    "processing_stage": "completed",
                    "message": "Order processed via real exchange integration",
                }
                
            except Exception as e:
                logger.error(f"❌ Exchange execution failed: {e}")
                await self._update_order_with_error(order_id, str(e))
                
                return {
                    "success": False,
                    "error": f"Exchange execution failed: {e}",
                    "order_id": order_id,
                    "stage": "exchange_execution",
                }

        except Exception as e:
            logger.error(f"❌ Bridge processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "stage": "bridge_processing",
            }

    def _validate_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate webhook payload"""
        required_fields = ["ticker", "action"]
        missing_fields = [field for field in required_fields if field not in payload]

        if missing_fields:
            return {
                "valid": False,
                "error": f"Missing required fields: {missing_fields}",
            }

        # Validate action
        if payload["action"].lower() not in ["buy", "sell", "close"]:
            return {
                "valid": False,
                "error": f"Invalid action: {payload['action']}. Must be 'buy', 'sell', or 'close'",
            }

        return {"valid": True}

    def _extract_order_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract order data from webhook payload"""
        symbol = payload["ticker"].upper()
        side = payload["action"].lower()

        # Default quantity for testing
        quantity = Decimal("0.001")  
        
        if "quantity" in payload:
            quantity = Decimal(str(payload["quantity"]))
        elif "position" in payload and "size" in payload["position"]:
            quantity = Decimal(str(payload["position"]["size"]))

        # Price (optional for market orders)
        price = None
        if "price" in payload:
            price = Decimal(str(payload["price"]))

        # Order type
        order_type = payload.get("order_type", "market").lower()

        return {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "order_type": order_type,
            "raw_payload": payload,
        }

    async def _get_default_user_id(self) -> Optional[UUID]:
        """Get default user ID for demo purposes"""
        try:
            # Get the first active user
            user = await transaction_db.fetchrow("""
                SELECT id FROM users WHERE is_active = true LIMIT 1
            """)
            
            if user:
                return UUID(user['id'])
            return None
            
        except Exception as e:
            logger.error(f"Error getting default user: {e}")
            return None

    async def _get_user_exchange_accounts(self, user_id: UUID) -> list:
        """Get user's active exchange accounts"""
        try:
            accounts = await transaction_db.fetch("""
                SELECT id, name, exchange, testnet, is_active
                FROM exchange_accounts 
                WHERE user_id = $1 AND is_active = true
                ORDER BY name
            """, str(user_id))
            
            return [dict(account) for account in accounts]
            
        except Exception as e:
            logger.error(f"Error getting exchange accounts: {e}")
            return []

    def _select_exchange_account(self, accounts: list, order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select appropriate exchange account for the order"""
        # Priority: Binance testnet accounts first
        binance_testnet = [acc for acc in accounts if acc['exchange'] == 'binance' and acc['testnet']]
        if binance_testnet:
            return binance_testnet[0]
        
        # Fallback: any Binance account
        binance_accounts = [acc for acc in accounts if acc['exchange'] == 'binance']
        if binance_accounts:
            return binance_accounts[0]
        
        # Fallback: first account
        return accounts[0] if accounts else None

    async def _create_order_in_database(
        self, order_data: Dict[str, Any], webhook_delivery_id: Optional[int]
    ) -> int:
        """Create order record in database"""
        order_id = await transaction_db.fetchval(
            """
            INSERT INTO trading_orders (
                webhook_delivery_id,
                symbol,
                side,
                order_type,
                quantity,
                price,
                status,
                exchange,
                raw_response
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """,
            webhook_delivery_id,
            order_data["symbol"],
            order_data["side"],
            order_data["order_type"],
            float(order_data["quantity"]),
            float(order_data["price"]) if order_data["price"] else None,
            "pending",
            "binance",  # Default to Binance for now
            json.dumps(order_data["raw_payload"]),
        )

        logger.info(f"📝 Order created in database: ID {order_id}")
        return order_id

    async def _update_order_with_result(self, order_id: int, exchange_result: Dict[str, Any]):
        """Update order record with exchange result"""
        if exchange_result.get("success", False):
            await transaction_db.execute(
                """
                UPDATE trading_orders 
                SET 
                    status = $1,
                    exchange_order_id = $2,
                    filled_quantity = $3,
                    average_price = $4,
                    raw_response = $5,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = $6
            """,
                exchange_result.get("status", "filled"),
                exchange_result.get("order_id"),
                float(exchange_result.get("filled_quantity", 0)) if exchange_result.get("filled_quantity") else None,
                float(exchange_result.get("average_price", 0)) if exchange_result.get("average_price") else None,
                json.dumps(exchange_result),
                order_id,
            )
        else:
            await self._update_order_with_error(order_id, exchange_result.get("error", "Unknown error"))

    async def _update_order_with_error(self, order_id: int, error_message: str):
        """Update order record with error"""
        await transaction_db.execute(
            """
            UPDATE trading_orders 
            SET 
                status = 'failed',
                error_message = $1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $2
        """,
            error_message,
            order_id,
        )
        logger.error(f"❌ Order {order_id} failed: {error_message}")


# Global bridge instance
real_exchange_bridge = RealExchangeBridge()


async def test_bridge():
    """Test the bridge functionality"""
    print("🧪 Testing Real Exchange Bridge")
    
    # Test payload
    test_payload = {
        "ticker": "BTCUSDT",
        "action": "buy",
        "quantity": "0.001",
        "order_type": "market"
    }
    
    result = await real_exchange_bridge.process_tradingview_webhook(test_payload)
    print(f"📊 Test result: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_bridge())