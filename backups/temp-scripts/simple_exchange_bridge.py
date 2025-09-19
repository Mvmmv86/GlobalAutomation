#!/usr/bin/env python3
"""
Simple Exchange Bridge - Direct TradingView to Exchange integration
Uses existing database exchange accounts with minimal dependencies
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
import structlog

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.security.encryption_service import EncryptionService

logger = structlog.get_logger()


class SimpleExchangeBridge:
    """Simple bridge that connects TradingView webhooks to exchange accounts"""

    def __init__(self):
        """Initialize the simple bridge"""
        self.encryption_service = EncryptionService()

    async def process_tradingview_webhook(
        self, webhook_payload: Dict[str, Any], webhook_delivery_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process TradingView webhook using available exchange accounts
        
        Args:
            webhook_payload: Payload from TradingView
            webhook_delivery_id: ID of webhook delivery record
            
        Returns:
            Processing result with order details
        """
        try:
            logger.info("🌉 Processing webhook via SIMPLE exchange bridge")
            
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

            # Step 3: Get available exchange accounts
            exchange_accounts = await self._get_available_exchange_accounts()
            if not exchange_accounts:
                return {
                    "success": False,
                    "error": "No exchange accounts found",
                    "stage": "account_lookup",
                }

            # Step 4: Select best account (prefer testnet Binance)
            selected_account = self._select_best_account(exchange_accounts, order_data)
            if not selected_account:
                return {
                    "success": False,
                    "error": "No suitable exchange account found",
                    "stage": "account_selection",
                }

            logger.info(f"🏦 Using account: {selected_account['name']} ({selected_account['exchange']})")

            # Step 5: Create database order record
            order_id = await self._create_order_record(order_data, webhook_delivery_id)

            # Step 6: Execute order on exchange
            try:
                exchange_result = await self._execute_order_on_exchange(
                    selected_account, order_data
                )
                
                # Step 7: Update database with result
                await self._update_order_record(order_id, exchange_result)
                
                return {
                    "success": exchange_result.get("success", False),
                    "order_id": order_id,
                    "exchange_result": exchange_result,
                    "exchange_account": selected_account['name'],
                    "exchange_type": selected_account['exchange'],
                    "bridge_type": "simple",
                    "processing_stage": "completed",
                    "message": "Order processed via simple exchange bridge",
                }
                
            except Exception as e:
                logger.error(f"❌ Exchange execution failed: {e}")
                await self._update_order_error(order_id, str(e))
                
                return {
                    "success": False,
                    "error": f"Exchange execution failed: {e}",
                    "order_id": order_id,
                    "stage": "exchange_execution",
                }

        except Exception as e:
            logger.error(f"❌ Simple bridge processing failed: {e}")
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
        valid_actions = ["buy", "sell", "close"]
        if payload["action"].lower() not in valid_actions:
            return {
                "valid": False,
                "error": f"Invalid action: {payload['action']}. Must be one of: {valid_actions}",
            }

        return {"valid": True}

    def _extract_order_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract order data from webhook payload"""
        symbol = payload["ticker"].upper()
        if not symbol.endswith("USDT"):
            symbol += "USDT"  # Ensure USDT pair
            
        side = payload["action"].lower()

        # Default small quantity for testing
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

    async def _get_available_exchange_accounts(self) -> list:
        """Get all available exchange accounts from database"""
        try:
            accounts = await transaction_db.fetch("""
                SELECT 
                    id, name, exchange, 
                    COALESCE(testnet, false) as testnet, 
                    COALESCE(is_active, true) as is_active,
                    user_id,
                    api_key, secret_key  -- Use existing columns
                FROM exchange_accounts 
                WHERE COALESCE(is_active, true) = true
                ORDER BY 
                    CASE WHEN COALESCE(testnet, false) THEN 0 ELSE 1 END,  -- Testnet first
                    CASE WHEN exchange = 'binance' THEN 0 ELSE 1 END,  -- Binance first
                    name
            """)
            
            return [dict(account) for account in accounts]
            
        except Exception as e:
            logger.error(f"Error getting exchange accounts: {e}")
            return []

    def _select_best_account(self, accounts: list, order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select the best exchange account for this order"""
        if not accounts:
            return None
            
        # Priority 1: Binance testnet with API keys
        for account in accounts:
            if (account['exchange'] == 'binance' and 
                account['testnet'] and 
                account.get('api_key') and 
                account.get('secret_key')):
                return account
        
        # Priority 2: Any Binance account with API keys
        for account in accounts:
            if (account['exchange'] == 'binance' and 
                account.get('api_key') and 
                account.get('secret_key')):
                return account
        
        # Priority 3: Any account with API keys
        for account in accounts:
            if account.get('api_key') and account.get('secret_key'):
                return account
        
        # Priority 4: Any Binance account (will use demo mode)
        for account in accounts:
            if account['exchange'] == 'binance':
                return account
        
        # Fallback: First account (will use demo mode)
        return accounts[0]

    async def _execute_order_on_exchange(
        self, account: Dict[str, Any], order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute order on the selected exchange"""
        
        if account['exchange'] != 'binance':
            return {
                "success": False,
                "error": f"Exchange {account['exchange']} not yet supported in simple bridge",
            }
        
        try:
            # Get encrypted credentials
            api_key_encrypted = account.get('api_key')
            secret_key_encrypted = account.get('secret_key')
            is_testnet = account.get('testnet', True)
            
            # Decrypt credentials if available
            api_key = None
            secret_key = None
            
            if api_key_encrypted and secret_key_encrypted:
                try:
                    api_key = self.encryption_service.decrypt_string(api_key_encrypted)
                    secret_key = self.encryption_service.decrypt_string(secret_key_encrypted)
                    logger.info(f"🔐 Successfully decrypted credentials for {account['name']}")
                except Exception as decrypt_error:
                    logger.warning(f"⚠️ Could not decrypt credentials for {account['name']}: {decrypt_error}")
                    # Fall back to checking plain text fields (for backward compatibility)
                    api_key = account.get('api_key')
                    secret_key = account.get('secret_key')
            else:
                # Check for plain text fields (backward compatibility)
                api_key = account.get('api_key')
                secret_key = account.get('secret_key')
                if api_key and secret_key:
                    logger.warning(f"⚠️ Using non-encrypted credentials for {account['name']} - SECURITY RISK!")
            
            # Create connector based on available credentials
            if api_key and secret_key and len(str(api_key)) > 10:
                logger.info(f"🔑 Using real API keys for {account['name']}")
                connector = BinanceConnector(
                    api_key=api_key,
                    api_secret=secret_key,
                    testnet=is_testnet
                )
            else:
                logger.info(f"🎯 Using demo mode for {account['name']}")
                connector = BinanceConnector(testnet=True)  # Demo mode
            
            # Execute order (only market orders for now)
            if order_data['order_type'] == 'market':
                result = await connector.create_market_order(
                    symbol=order_data['symbol'],
                    side=order_data['side'],
                    quantity=order_data['quantity']
                )
                
                logger.info(f"📈 Order result: {result.get('order_id', 'unknown')}")
                return result
            else:
                return {
                    "success": False,
                    "error": f"Order type {order_data['order_type']} not supported yet",
                }
                
        except Exception as e:
            logger.error(f"Exchange execution error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _create_order_record(
        self, order_data: Dict[str, Any], webhook_delivery_id: Optional[int]
    ) -> int:
        """Create order record in database"""
        try:
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
                "binance",  
                json.dumps(order_data["raw_payload"]),
            )

            logger.info(f"📝 Order record created: ID {order_id}")
            return order_id
            
        except Exception as e:
            logger.error(f"Database order creation failed: {e}")
            raise

    async def _update_order_record(self, order_id: int, exchange_result: Dict[str, Any]):
        """Update order record with exchange result"""
        try:
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
                logger.info(f"✅ Order {order_id} updated with success")
            else:
                await self._update_order_error(order_id, exchange_result.get("error", "Unknown error"))
                
        except Exception as e:
            logger.error(f"Database order update failed: {e}")

    async def _update_order_error(self, order_id: int, error_message: str):
        """Update order record with error"""
        try:
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
            logger.error(f"❌ Order {order_id} marked as failed: {error_message}")
            
        except Exception as e:
            logger.error(f"Database error update failed: {e}")


# Global bridge instance
simple_exchange_bridge = SimpleExchangeBridge()


async def test_simple_bridge():
    """Test the simple bridge functionality"""
    print("🧪 Testing Simple Exchange Bridge")
    
    # Test payload
    test_payload = {
        "ticker": "BTCUSDT",
        "action": "buy",
        "quantity": "0.001",
        "order_type": "market"
    }
    
    result = await simple_exchange_bridge.process_tradingview_webhook(test_payload)
    print(f"📊 Test result: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_simple_bridge())