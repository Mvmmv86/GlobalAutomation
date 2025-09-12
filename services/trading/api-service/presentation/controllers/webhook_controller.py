"""Webhook controller - HTTP handlers for webhook endpoints"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends, status, Request
from fastapi.responses import JSONResponse
from uuid import UUID
import json

from application.services.webhook_service import WebhookService
from application.services.tradingview_service import TradingViewService
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


def get_tradingview_service(
    webhook_service: WebhookService = Depends(get_webhook_service),
) -> TradingViewService:
    """Get TradingViewService instance"""
    # In production, this would be properly injected
    # For now, create it with the webhook service's repositories
    return TradingViewService(
        webhook_service.webhook_repository,
        webhook_service.webhook_delivery_repository,
        webhook_service.user_repository,
        None,  # order_repository - would be injected
    )


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

    @router.post("/tv/{webhook_path:path}", response_model=WebhookProcessingResponse)
    async def receive_tradingview_webhook(
        webhook_path: str,
        request: Request,
        x_tradingview_signature: Optional[str] = Header(
            None, alias="x-tradingview-signature"
        ),
        tradingview_service: TradingViewService = Depends(get_tradingview_service),
    ):
        """
        Receive TradingView webhook

        - **HMAC signature verification** (if webhook has secret)
        - **Multiple payload formats supported**
        - **Rate limiting applied**
        """
        try:
            # Get request body as JSON
            body = await request.body()

            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON payload",
                )

            # Get request headers
            headers = dict(request.headers)

            # Process webhook
            success, result = await tradingview_service.process_webhook_delivery(
                webhook_url_path=webhook_path,
                payload=payload,
                headers=headers,
                signature=x_tradingview_signature,
            )

            if not success:
                error_code = result.get("code", "PROCESSING_ERROR")

                if error_code == "WEBHOOK_NOT_FOUND":
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=result.get("error", "Webhook not found"),
                    )
                elif error_code == "INVALID_SIGNATURE":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=result.get("error", "Invalid signature"),
                    )
                elif error_code in ["INVALID_FORMAT", "PAYLOAD_ERROR"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=result.get("error", "Invalid payload"),
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=result.get("error", "Processing failed"),
                    )

            return WebhookProcessingResponse(
                success=True,
                message=result.get("message", "Webhook processed successfully"),
                delivery_id=result.get("delivery_id", ""),
                webhook_id="",  # Would be filled from result
                orders_created=result.get("orders_created", 0),
                orders_executed=result.get("orders_executed", 0),
                processing_time_ms=result.get("processing_time_ms", 0),
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}",
            )

    @router.get("/deliveries/{delivery_id}", response_model=WebhookDeliveryStatus)
    async def get_delivery_status(
        delivery_id: UUID,
        current_user_id: Optional[UUID] = Depends(get_optional_current_user_id),
        tradingview_service: TradingViewService = Depends(get_tradingview_service),
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

    @router.post("/deliveries/{delivery_id}/retry")
    async def retry_delivery(
        delivery_id: UUID,
        current_user_id: UUID = Depends(get_current_user_id),
        tradingview_service: TradingViewService = Depends(get_tradingview_service),
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

    @router.get("/stats/{webhook_id}", response_model=WebhookStatsResponse)
    async def get_webhook_stats(
        webhook_id: UUID,
        days: int = 30,
        current_user_id: UUID = Depends(get_current_user_id),
        tradingview_service: TradingViewService = Depends(get_tradingview_service),
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
