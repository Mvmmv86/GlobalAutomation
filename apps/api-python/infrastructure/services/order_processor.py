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
        # NOTE: Connector será criado dinamicamente para cada webhook
        # baseado na conta do usuário que enviou o webhook
        pass

    async def process_tradingview_webhook(
        self, webhook_payload: Dict[str, Any], webhook_delivery_id: Optional[int] = None, market_type: str = "spot"
    ) -> Dict[str, Any]:
        """
        Processa webhook do TradingView e cria ordem na exchange

        Args:
            webhook_payload: Payload recebido do TradingView
            webhook_delivery_id: ID do webhook delivery no banco
            market_type: Tipo de mercado ("spot" ou "futures")

        Returns:
            Dict com resultado do processamento
        """

        try:
            # Validar e normalizar payload
            validation_result = self._validate_webhook_payload(webhook_payload)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "stage": "validation",
                }

            # Usar payload normalizado para extrair dados
            normalized_payload = validation_result.get("normalized_payload", webhook_payload)
            order_data = self._extract_order_data(normalized_payload)

            # Log da ordem recebida
            logger.info(
                f"Processing order: {order_data['symbol']} {order_data['side']} {order_data['quantity']}"
            )

            # Criar ordem no banco (status: pending)
            order_id = await self._create_order_in_database(
                order_data, webhook_delivery_id
            )

            # Executar ordem na exchange (passando market_type)
            exchange_result = await self._execute_order_on_exchange(order_data, market_type)

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
        """Valida payload do webhook - aceita múltiplos formatos"""

        # Normalizar payload para formato padrão
        normalized_payload = self._normalize_payload(payload)

        # Verificar campos obrigatórios
        required_fields = ["ticker", "action"]
        missing_fields = [field for field in required_fields if field not in normalized_payload]

        if missing_fields:
            return {
                "valid": False,
                "error": f"Missing required fields: {missing_fields}",
            }

        # Validar action
        action = normalized_payload["action"].lower()
        if action not in ["buy", "sell", "compra", "venda"]:
            return {
                "valid": False,
                "error": f"Invalid action: {normalized_payload['action']}. Must be 'buy' or 'sell'",
            }

        # Validar ticker
        ticker = normalized_payload["ticker"].upper()
        if not ticker.endswith("USDT"):
            return {
                "valid": False,
                "error": f"Only USDT pairs supported. Got: {ticker}",
            }

        return {"valid": True, "normalized_payload": normalized_payload}

    def _normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza payload para formato padrão, independente da origem.
        Aceita formatos: simples (TradingView) e complexo (Indicadores customizados)
        """
        normalized = {}

        # 1. TICKER/SYMBOL - Priorizar 'ticker', fallback para 'symbol'
        if "ticker" in payload:
            normalized["ticker"] = payload["ticker"]
        elif "symbol" in payload:
            normalized["ticker"] = payload["symbol"]
        else:
            # Último recurso: extrair de position.symbol
            if "position" in payload and isinstance(payload["position"], dict):
                # Pode estar em position como objeto ou string
                normalized["ticker"] = payload.get("symbol", "")

        # 2. ACTION - Normalizar "Compra"/"Venda" para "buy"/"sell"
        action = payload.get("action", "").lower()
        if action in ["compra", "buy", "long"]:
            normalized["action"] = "buy"
        elif action in ["venda", "sell", "short"]:
            normalized["action"] = "sell"
        else:
            normalized["action"] = action

        # 3. PRICE - Extrair de diferentes locais
        if "price" in payload:
            normalized["price"] = payload["price"]
        elif "position" in payload and isinstance(payload["position"], dict):
            # Tentar entry_price do position
            pos = payload["position"]
            if "entry_price" in pos:
                normalized["price"] = pos["entry_price"]

        # 4. QUANTITY - Extrair de diferentes locais
        if "quantity" in payload:
            normalized["quantity"] = payload["quantity"]
        elif "position" in payload and isinstance(payload["position"], dict):
            pos = payload["position"]
            # Pode estar em quantity ou size_usdt
            if "quantity" in pos:
                normalized["quantity"] = pos["quantity"]
            elif "size_usdt" in pos:
                # Se temos size_usdt e price, calcular quantity
                if "entry_price" in pos:
                    size_usdt = float(pos["size_usdt"])
                    entry_price = float(pos["entry_price"])
                    normalized["quantity"] = size_usdt / entry_price

        # 5. STOP LOSS E TAKE PROFIT - Extrair de risk_management
        if "risk_management" in payload and isinstance(payload["risk_management"], dict):
            rm = payload["risk_management"]

            # Stop Loss
            if "stop_loss" in rm and isinstance(rm["stop_loss"], dict):
                normalized["stop_loss"] = rm["stop_loss"].get("price")

            # Take Profit (pegar o primeiro, se houver múltiplos)
            if "take_profit_1" in rm and isinstance(rm["take_profit_1"], dict):
                normalized["take_profit"] = rm["take_profit_1"].get("price")
            elif "take_profit" in rm:
                normalized["take_profit"] = rm["take_profit"]

        # 6. TIMESTAMP
        if "timestamp" in payload:
            normalized["timestamp"] = payload["timestamp"]

        # 7. Preservar payload original para referência
        normalized["_original_payload"] = payload

        return normalized

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
        self, order_data: Dict[str, Any], market_type: str = "spot"
    ) -> Dict[str, Any]:
        """Executa ordem na exchange"""

        try:
            # Por enquanto, apenas market orders
            if order_data["order_type"] != "market":
                return {
                    "success": False,
                    "error": f"Order type {order_data['order_type']} not yet supported",
                }

            # Executar ordem de acordo com o market_type
            if market_type.lower() == "futures":
                # Executar ordem no mercado de FUTURES
                # Extrair leverage do payload original (nested dentro de _original_payload)
                original_payload = order_data["raw_payload"].get("_original_payload", {})
                leverage = original_payload.get("leverage", 1)

                logger.info(f"Creating FUTURES order: {order_data['symbol']} {order_data['side']} {order_data['quantity']} @ {leverage}x leverage")
                result = await self.binance_connector.create_futures_order(
                    symbol=order_data["symbol"],
                    side=order_data["side"].upper(),
                    order_type="MARKET",
                    quantity=order_data["quantity"],
                    leverage=leverage,
                )
            else:
                # Executar ordem no mercado SPOT (padrão)
                logger.info(f"Creating SPOT order: {order_data['symbol']} {order_data['side']} {order_data['quantity']}")
                result = await self.binance_connector.create_market_order(
                    symbol=order_data["symbol"],
                    side=order_data["side"],
                    quantity=order_data["quantity"],
                )

            logger.info(f"Exchange order result ({market_type}): {result.get('order_id', 'unknown')}")
            return result

        except Exception as e:
            logger.error(f"Error executing order on exchange ({market_type}): {e}")
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
# NOTE: Desabilitado temporariamente - requer refatoração para buscar
# credenciais da conta do usuário ao invés de usar connector global
# order_processor = OrderProcessor()
order_processor = None  # Será criado sob demanda quando necessário
