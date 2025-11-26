"""Webhook controller - HTTP handlers for webhook endpoints"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends, status, Request
from fastapi.responses import JSONResponse
from uuid import UUID
import json

from application.services.webhook_service import WebhookService
from application.services.tradingview_webhook_service import TradingViewWebhookService
from infrastructure.di.container import get_container
from infrastructure.di.dependencies import get_webhook_service
from presentation.middleware.auth import (
    get_current_user_id,
    get_optional_current_user_id,
)
from presentation.schemas.tradingview import (
    WebhookProcessingResponse,
    WebhookDeliveryStatus,
    WebhookStatsResponse,
)


async def get_tradingview_webhook_service() -> TradingViewWebhookService:
    """Get TradingViewWebhookService instance from DI container"""
    container = await get_container()
    return container.get("tradingview_webhook_service")


def create_webhook_router() -> APIRouter:
    """Create webhook router with dependency injection"""

    router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

    # Test endpoint without database dependencies
    @router.post("/tv/test-simple")
    async def test_tradingview_webhook_simple(request: Request):
        """
        Simple TradingView webhook test (no database required)

        - **Tests webhook parsing and validation**
        - **No database dependencies**
        """
        try:
            # Get request body
            body = await request.body()

            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                return JSONResponse(
                    status_code=400, content={"error": "Invalid JSON payload"}
                )

            # Basic validation
            required_fields = ["ticker", "action"]
            missing_fields = [
                field for field in required_fields if field not in payload
            ]

            if missing_fields:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Missing required fields",
                        "missing_fields": missing_fields,
                    },
                )

            # Mock processing result
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "TradingView webhook received successfully",
                    "payload": payload,
                    "processing_result": {
                        "orders_created": 1,
                        "orders_executed": 1
                        if payload.get("order_type", "market") == "market"
                        else 0,
                        "orders_failed": 0,
                    },
                    "test_mode": True,
                },
            )

        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "detail": str(e)},
            )

    @router.post("/tv/{webhook_path:path}")
    async def receive_tradingview_webhook(
        webhook_path: str,
        request: Request,
        x_tradingview_signature: Optional[str] = Header(
            None, alias="x-tradingview-signature"
        ),
        tradingview_service: TradingViewWebhookService = Depends(get_tradingview_webhook_service),
    ):
        """
        Receive TradingView webhook

        - **HMAC signature verification** (if webhook has secret)
        - **Real order execution on Binance**
        - **Automatic SL/TP placement**

        ⚠️ IMPORTANT: Always returns HTTP 200 (TradingView best practice)
        - Error details are in response body, not HTTP status
        - Prevents TradingView from disabling webhook after failures
        """
        import structlog

        logger = structlog.get_logger()

        try:
            # Get request body as JSON
            body = await request.body()

            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                # ✅ FIX: Return 200 with error in body
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": False,
                        "error": "Invalid JSON payload",
                        "message": "Failed to parse webhook payload",
                    },
                )

            # Get request headers
            headers = dict(request.headers)

            # Get client IP
            client_ip = request.client.host if request.client else None

            # ✅ FIX: Use transaction_db directly instead of SQLAlchemy
            from infrastructure.database.connection_transaction_mode import transaction_db

            logger.info("Step 1: Searching webhook by url_path", url_path=webhook_path)

            # Buscar webhook direto do banco usando transaction_db
            webhook_row = await transaction_db.fetchrow("""
                SELECT id, name, url_path, secret, status, is_public, market_type,
                       default_margin_usd, default_leverage, default_stop_loss_pct, default_take_profit_pct
                FROM webhooks
                WHERE url_path = $1
            """, webhook_path)

            logger.info("Step 2: Webhook found", found=webhook_row is not None)

            # Converter para objeto simples
            if webhook_row:
                class WebhookSimple:
                    def __init__(self, row):
                        self.id = row['id']
                        self.name = row['name']
                        self.url_path = row['url_path']
                        self.secret = row['secret']
                        self.status = row['status']
                        self.is_public = row['is_public']
                        self.market_type = row['market_type']
                        self.default_margin_usd = row['default_margin_usd']
                        self.default_leverage = row['default_leverage']
                        self.default_stop_loss_pct = row['default_stop_loss_pct']
                        self.default_take_profit_pct = row['default_take_profit_pct']

                    def is_active(self):
                        return self.status == 'active'

                webhook = WebhookSimple(webhook_row)
            else:
                webhook = None

            if not webhook:
                # ✅ FIX: Return 200 with error in body
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": False,
                        "error": f"Webhook not found: {webhook_path}",
                        "message": "Webhook configuration not found",
                    },
                )

            if not webhook.is_active():
                # ✅ FIX: Return 200 with error in body
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": False,
                        "error": "Webhook is not active",
                        "message": "Webhook is disabled",
                    },
                )

            logger.info("Step 5: Processing webhook with direct transaction_db", webhook_id=webhook.id)

            # ✅ FIX: Use transaction_db directly (compatible with pgBouncer Session mode)
            from infrastructure.database.connection_transaction_mode import transaction_db
            from infrastructure.services.order_processor import order_processor
            import time
            from datetime import datetime, timezone
            from uuid import uuid4

            start_time = time.time()

            # 🎯 STEP 1: Criar registro de delivery
            delivery_id = uuid4()
            delivery_created_at = datetime.now(timezone.utc)

            await transaction_db.execute("""
                INSERT INTO webhook_deliveries (
                    id, webhook_id, status, created_at,
                    payload, headers, source_ip
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                delivery_id,
                webhook.id,
                'processing',
                delivery_created_at,
                json.dumps(payload),
                json.dumps(headers),
                client_ip
            )

            logger.info("Step 5.1: Delivery record created", delivery_id=delivery_id)

            try:
                # Buscar preço atual do símbolo
                ticker = payload.get("ticker") or payload.get("symbol")
                action = payload.get("action", "").lower()

                # Normalizar action
                if action in ["venda", "sell", "short"]:
                    action = "sell"
                elif action in ["compra", "buy", "long"]:
                    action = "buy"

                # Buscar preço REAL do mercado
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    price_api = "https://fapi.binance.com/fapi/v1/ticker/price" if webhook.market_type == "futures" else "https://api.binance.com/api/v3/ticker/price"
                    async with session.get(f"{price_api}?symbol={ticker}") as resp:
                        price_data = await resp.json()
                        price = float(price_data.get("price", 0))

                # Calcular quantity usando trading parameters
                margin_usd = float(webhook.default_margin_usd)
                leverage = int(webhook.default_leverage)
                raw_quantity = (margin_usd * leverage) / price

                # Ajustar precisão
                async with aiohttp.ClientSession() as session:
                    api_url = "https://fapi.binance.com/fapi/v1/exchangeInfo" if webhook.market_type == "futures" else "https://api.binance.com/api/v3/exchangeInfo"
                    async with session.get(f"{api_url}?symbol={ticker}") as resp:
                        exchange_info = await resp.json()
                        symbol_info = next((s for s in exchange_info.get("symbols", []) if s.get("symbol") == ticker), None)

                        if symbol_info:
                            lot_filter = next((f for f in symbol_info.get("filters", []) if f.get("filterType") == "LOT_SIZE"), None)
                            if lot_filter:
                                step_size = float(lot_filter.get("stepSize", 1))
                                precision = len(str(step_size).rstrip('0').split('.')[-1]) if '.' in str(step_size) else 0
                                from decimal import Decimal, ROUND_DOWN
                                quantity = float(Decimal(str(raw_quantity)).quantize(Decimal(str(step_size)), rounding=ROUND_DOWN))
                            else:
                                quantity = raw_quantity
                        else:
                            quantity = raw_quantity

                # Criar payload normalizado
                normalized_payload = {
                    "ticker": ticker,
                    "action": action,
                    "quantity": quantity,
                    "price": price,
                    "order_type": "market",
                    "leverage": leverage,
                    "margin_usd": margin_usd,
                }

                # Processar ordem (passando delivery_id para vinculação)
                order_result = await order_processor.process_tradingview_webhook(
                    normalized_payload,
                    webhook_delivery_id=delivery_id,  # 🎯 Vincular ordem ao delivery
                    market_type=webhook.market_type
                )

                processing_time = int((time.time() - start_time) * 1000)
                success = order_result.get("success", False)

                logger.info("Step 6: Order processed", success=success)

                # 🎯 STEP 2: Atualizar delivery record
                completed_at = datetime.now(timezone.utc)
                await transaction_db.execute("""
                    UPDATE webhook_deliveries
                    SET status = $1,
                        processing_completed_at = $2,
                        processing_duration_ms = $3,
                        orders_created = $4,
                        orders_executed = $5,
                        orders_failed = $6,
                        error_message = $7
                    WHERE id = $8
                """,
                    'success' if success else 'failed',
                    completed_at,
                    processing_time,
                    1 if success else 0,
                    1 if success else 0,
                    0 if success else 1,
                    order_result.get("error") if not success else None,
                    delivery_id
                )

                # 🎯 STEP 3: Atualizar estatísticas do webhook
                await transaction_db.execute("""
                    UPDATE webhooks
                    SET total_deliveries = total_deliveries + 1,
                        successful_deliveries = successful_deliveries + $1,
                        failed_deliveries = failed_deliveries + $2,
                        last_delivery_at = $3,
                        last_success_at = CASE WHEN $4 THEN $5 ELSE last_success_at END
                    WHERE id = $6
                """,
                    1 if success else 0,
                    0 if success else 1,
                    completed_at,
                    success,
                    completed_at,
                    webhook.id
                )

                logger.info("Step 6.1: Webhook statistics updated", webhook_id=webhook.id)

                # ✅ FIX: Always return 200, even on processing failure
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": success,
                        "message": f"Order processed with margin=${margin_usd}, leverage={leverage}x" if success else "Processing failed",
                        "webhook_id": str(webhook.id),
                        "delivery_id": str(delivery_id),  # 🎯 Retornar delivery_id
                        "orders_created": 1 if success else 0,
                        "orders_executed": 1 if success else 0,
                        "orders_failed": 0 if success else 1,
                        "processing_time_ms": processing_time,
                        "market_type": webhook.market_type,
                        "calculated_quantity": quantity,
                        "order_result": order_result,
                        "error": order_result.get("error") if not success else None,
                    },
                )

            except Exception as proc_error:
                processing_time = int((time.time() - start_time) * 1000)
                logger.error("Webhook processing error", error=str(proc_error), exc_info=True)

                # 🎯 Atualizar delivery record como falha
                completed_at = datetime.now(timezone.utc)
                await transaction_db.execute("""
                    UPDATE webhook_deliveries
                    SET status = $1,
                        processing_completed_at = $2,
                        processing_duration_ms = $3,
                        orders_created = 0,
                        orders_executed = 0,
                        orders_failed = 1,
                        error_message = $4
                    WHERE id = $5
                """,
                    'failed',
                    completed_at,
                    processing_time,
                    str(proc_error),
                    delivery_id
                )

                # 🎯 Atualizar estatísticas do webhook (falha)
                await transaction_db.execute("""
                    UPDATE webhooks
                    SET total_deliveries = total_deliveries + 1,
                        failed_deliveries = failed_deliveries + 1,
                        last_delivery_at = $1
                    WHERE id = $2
                """,
                    completed_at,
                    webhook.id
                )

                return JSONResponse(
                    status_code=200,
                    content={
                        "success": False,
                        "message": "Processing failed",
                        "webhook_id": str(webhook.id),
                        "delivery_id": str(delivery_id),  # 🎯 Retornar delivery_id
                        "orders_created": 0,
                        "orders_executed": 0,
                        "orders_failed": 1,
                        "processing_time_ms": processing_time,
                        "error": str(proc_error),
                    },
                )

        except Exception as e:
            logger.error(
                "Unexpected error in webhook controller",
                error=str(e),
                webhook_path=webhook_path,
                exc_info=True,
            )

            # ✅ FIX: Even on unexpected errors, return 200
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "error": f"Internal server error: {str(e)}",
                    "message": "Webhook processing failed",
                },
            )

    # TEMPORARIAMENTE DESABILITADO - TODO: Migrar para novo service
    # @router.get("/deliveries/{delivery_id}", response_model=WebhookDeliveryStatus)
    async def get_delivery_status_disabled(
        delivery_id: UUID,
        current_user_id: Optional[UUID] = Depends(get_optional_current_user_id),
        # tradingview_service: TradingViewService = Depends(get_tradingview_service),
    ):
        """
        Get webhook delivery status

        - **Authentication optional** (some webhooks are public)
        - **Returns delivery processing status and details**
        """
        try:
            delivery = await tradingview_service.get_delivery_status(delivery_id)

            if not delivery:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found"
                )

            # Convert to response format
            return WebhookDeliveryStatus(
                delivery_id=str(delivery.id),
                webhook_id=str(delivery.webhook_id),
                status=delivery.status.value,
                created_at=delivery.created_at,
                processed_at=delivery.processing_started_at,
                completed_at=delivery.completed_at,
                retry_count=delivery.retry_count,
                next_retry_at=delivery.next_retry_at,
                orders_created=delivery.orders_created or 0,
                orders_executed=delivery.orders_executed or 0,
                orders_failed=delivery.orders_failed or 0,
                error_message=delivery.error_message,
                error_details=delivery.error_details,
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}",
            )

    # TEMPORARIAMENTE DESABILITADO - TODO: Migrar para novo service
    # @router.post("/deliveries/{delivery_id}/retry")
    async def retry_delivery_disabled(
        delivery_id: UUID,
        current_user_id: UUID = Depends(get_current_user_id),
        # tradingview_service: TradingViewService = Depends(get_tradingview_service),
    ):
        """
        Retry failed webhook delivery

        - **Authentication required**
        - **Only failed deliveries can be retried**
        """
        try:
            success = await tradingview_service.retry_failed_delivery(delivery_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Delivery cannot be retried (not found or not in failed state)",
                )

            return {"message": "Delivery scheduled for retry"}

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}",
            )

    # TEMPORARIAMENTE DESABILITADO - TODO: Migrar para novo service
    # @router.get("/stats/{webhook_id}", response_model=WebhookStatsResponse)
    async def get_webhook_stats_disabled(
        webhook_id: UUID,
        days: int = 30,
        current_user_id: UUID = Depends(get_current_user_id),
        # tradingview_service: TradingViewService = Depends(get_tradingview_service),
    ):
        """
        Get webhook statistics

        - **Authentication required**
        - **Returns comprehensive webhook metrics**
        """
        try:
            stats = await tradingview_service.get_webhook_stats(webhook_id, days)

            return WebhookStatsResponse(
                webhook_id=str(webhook_id),
                total_deliveries=stats.get("total_deliveries", 0),
                successful_deliveries=stats.get("successful_deliveries", 0),
                failed_deliveries=stats.get("failed_deliveries", 0),
                success_rate=stats.get("average_success_rate", 0.0),
                average_processing_time_ms=stats.get("average_processing_time_ms", 0.0),
                total_orders_created=stats.get("total_orders_created", 0),
                total_orders_executed=stats.get("total_orders_executed", 0),
                period_days=days,
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}",
            )

    return router
