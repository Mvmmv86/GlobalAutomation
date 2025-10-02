"""
Order Processing Service
Processa webhooks do TradingView e cria ordens reais na exchange
"""

import json
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
import structlog

from ..database.connection_transaction_mode import transaction_db
from ..exchanges.binance_connector import create_binance_connector

logger = structlog.get_logger()


class OrderProcessor:
    """Processa ordens do TradingView para exchanges"""

    def __init__(self):
        # IMPORTANTE: Usar REAL trading (testnet=False)
        self.binance_connector = create_binance_connector(
            testnet=False
        )

    async def process_tradingview_webhook(
        self, webhook_payload: Dict[str, Any], webhook_delivery_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Processa webhook do TradingView e cria ordem na exchange

        Args:
            webhook_payload: Payload recebido do TradingView
            webhook_delivery_id: ID do webhook delivery no banco

        Returns:
            Dict com resultado do processamento
        """

        try:
            # Validar payload básico
            validation_result = self._validate_webhook_payload(webhook_payload)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "stage": "validation",
                }

            # Extrair dados do webhook
            order_data = self._extract_order_data(webhook_payload)

            # Log da ordem recebida
            logger.info(
                f"Processing order: {order_data['symbol']} {order_data['side']} {order_data['quantity']}"
            )

            # Criar ordem no banco (status: pending)
            order_id = await self._create_order_in_database(
                order_data, webhook_delivery_id
            )

            # Executar ordem na exchange
            exchange_result = await self._execute_order_on_exchange(order_data)

            # Atualizar ordem no banco com resultado
            await self._update_order_with_result(order_id, exchange_result)

            # Resultado final
            result = {
                "success": True,
                "order_id": order_id,
                "exchange_result": exchange_result,
                "processing_stage": "completed",
                "message": "Order processed successfully",
            }

            if exchange_result.get("success"):
                result["exchange_order_id"] = exchange_result.get("order_id")
                result["status"] = exchange_result.get("status", "unknown")
            else:
                result["success"] = False
                result["error"] = exchange_result.get(
                    "error", "Exchange execution failed"
                )

            return result

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")

            # Se temos order_id, atualizar com erro
            if "order_id" in locals():
                try:
                    await self._update_order_with_error(order_id, str(e))
                except:
                    pass

            return {"success": False, "error": str(e), "stage": "processing"}

    def _validate_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Valida payload do webhook"""

        required_fields = ["ticker", "action"]
        missing_fields = [field for field in required_fields if field not in payload]

        if missing_fields:
            return {
                "valid": False,
                "error": f"Missing required fields: {missing_fields}",
            }

        # Validar action
        if payload["action"].lower() not in ["buy", "sell"]:
            return {
                "valid": False,
                "error": f"Invalid action: {payload['action']}. Must be 'buy' or 'sell'",
            }

        # Validar ticker
        ticker = payload["ticker"].upper()
        if not ticker.endswith("USDT"):
            return {
                "valid": False,
                "error": f"Only USDT pairs supported. Got: {ticker}",
            }

        return {"valid": True}

    def _extract_order_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai dados da ordem do payload"""

        # Dados básicos
        symbol = payload["ticker"].upper()
        side = payload["action"].lower()

        # Quantidade (com fallbacks)
        quantity = Decimal("0.001")  # Default mínimo

        if "quantity" in payload:
            quantity = Decimal(str(payload["quantity"]))
        elif "position" in payload and "size" in payload["position"]:
            quantity = Decimal(str(payload["position"]["size"]))

        # Preço (opcional para market orders)
        price = None
        if "price" in payload:
            price = Decimal(str(payload["price"]))

        # Tipo de ordem
        order_type = payload.get("order_type", "market").lower()

        return {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "order_type": order_type,
            "raw_payload": payload,
        }

    async def _create_order_in_database(
        self, order_data: Dict[str, Any], webhook_delivery_id: Optional[int]
    ) -> int:
        """Cria ordem no banco de dados"""

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

        logger.info(f"Order created in database: ID {order_id}")
        return order_id

    async def _execute_order_on_exchange(
        self, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executa ordem na exchange"""

        try:
            # Por enquanto, apenas market orders
            if order_data["order_type"] != "market":
                return {
                    "success": False,
                    "error": f"Order type {order_data['order_type']} not yet supported",
                }

            # Executar ordem market na Binance
            result = await self.binance_connector.create_market_order(
                symbol=order_data["symbol"],
                side=order_data["side"],
                quantity=order_data["quantity"],
            )

            logger.info(f"Exchange order result: {result.get('order_id', 'unknown')}")
            return result

        except Exception as e:
            logger.error(f"Error executing order on exchange: {e}")
            return {"success": False, "error": str(e)}

    async def _update_order_with_result(
        self, order_id: int, exchange_result: Dict[str, Any]
    ):
        """Atualiza ordem no banco com resultado da exchange"""

        if exchange_result.get("success"):
            # Ordem bem-sucedida
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
                float(exchange_result.get("filled_quantity", 0))
                if exchange_result.get("filled_quantity")
                else None,
                float(exchange_result.get("average_price", 0))
                if exchange_result.get("average_price")
                else None,
                json.dumps(exchange_result),
                order_id,
            )
        else:
            # Ordem falhou
            await self._update_order_with_error(
                order_id, exchange_result.get("error", "Unknown error")
            )

    async def _update_order_with_error(self, order_id: int, error_message: str):
        """Atualiza ordem com erro"""

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

        logger.error(f"Order {order_id} failed: {error_message}")

    async def get_order_status(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Busca status de uma ordem"""

        try:
            order = await transaction_db.fetchrow(
                """
                SELECT 
                    id,
                    symbol,
                    side,
                    order_type,
                    quantity,
                    price,
                    status,
                    exchange,
                    exchange_order_id,
                    filled_quantity,
                    average_price,
                    error_message,
                    created_at,
                    updated_at
                FROM trading_orders 
                WHERE id = $1
            """,
                order_id,
            )

            if not order:
                return None

            return dict(order)

        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None

    async def get_recent_orders(self, limit: int = 10) -> list:
        """Busca ordens recentes"""

        try:
            orders = await transaction_db.fetch(
                """
                SELECT 
                    id,
                    symbol,
                    side,
                    order_type,
                    quantity,
                    status,
                    exchange,
                    exchange_order_id,
                    created_at
                FROM trading_orders 
                ORDER BY created_at DESC 
                LIMIT $1
            """,
                limit,
            )

            return [dict(order) for order in orders]

        except Exception as e:
            logger.error(f"Error getting recent orders: {e}")
            return []


# Instância global do processador
order_processor = OrderProcessor()
