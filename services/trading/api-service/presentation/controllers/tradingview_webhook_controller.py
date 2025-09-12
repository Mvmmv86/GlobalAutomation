"""Enhanced TradingView Webhook Controller"""

from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog

from infrastructure.di.container import get_container
from application.services.tradingview_webhook_service import TradingViewWebhookService
from presentation.schemas.tradingview import TradingViewOrderWebhook


logger = structlog.get_logger()


def create_tradingview_webhook_router() -> APIRouter:
    """Create TradingView webhook router"""
    router = APIRouter(tags=["TradingView Webhooks"])

    async def get_tradingview_service() -> TradingViewWebhookService:
        """Dependency to get TradingView webhook service"""
        container = await get_container()
        return container.get("tradingview_webhook_service")

    @router.post("/webhooks/tradingview/{webhook_id}")
    async def process_tradingview_webhook(
        webhook_id: str,
        request: Request,
        background_tasks: BackgroundTasks,
        tradingview_service: TradingViewWebhookService = Depends(
            get_tradingview_service
        ),
    ) -> JSONResponse:
        """
        Process TradingView webhook with enhanced security and error handling

        Args:
            webhook_id: Webhook configuration ID
            request: HTTP request
            background_tasks: FastAPI background tasks
            tradingview_service: TradingView webhook service

        Returns:
            JSON response with processing status
        """
        client_ip = request.client.host if request.client else "unknown"
        start_time = logger.info(
            "TradingView webhook received", webhook_id=webhook_id, client_ip=client_ip
        )

        try:
            # Validate webhook_id format
            try:
                webhook_uuid = UUID(webhook_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid webhook ID format")

            # Get request body and headers
            try:
                body = await request.body()
                if not body:
                    raise HTTPException(status_code=400, detail="Empty request body")

                # Parse JSON payload
                import json

                payload = json.loads(body.decode("utf-8"))

            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON in webhook payload", error=str(e))
                raise HTTPException(
                    status_code=400, detail=f"Invalid JSON payload: {str(e)}"
                )
            except Exception as e:
                logger.error("Error reading request body", error=str(e))
                raise HTTPException(
                    status_code=400, detail="Error reading request body"
                )

            # Extract headers
            headers = dict(request.headers)

            # Process webhook (this is fast, but can be moved to background if needed)
            result = await tradingview_service.process_tradingview_webhook(
                webhook_id=webhook_uuid,
                payload=payload,
                headers=headers,
                user_ip=client_ip,
            )

            # Determine response status
            if result.get("success"):
                status_code = 200
                response_data = {
                    "status": "success",
                    "message": "Webhook processed successfully",
                    "processing_time_ms": result.get("processing_time_ms", 0),
                    "orders_created": result.get("orders_created", 0),
                    "orders_executed": result.get("orders_executed", 0),
                    "webhook_id": webhook_id,
                }

                # Add order details if available (but not sensitive data)
                if "order_details" in result:
                    order_details = result["order_details"]
                    if order_details.get("success"):
                        response_data["order_id"] = order_details.get("order_id")
                        response_data["exchange"] = result.get(
                            "exchange_type", "unknown"
                        )

            else:
                status_code = 422  # Unprocessable Entity
                error_msg = result.get("error", "Unknown processing error")

                # Don't expose internal errors to external callers
                if "internal" in error_msg.lower() or "database" in error_msg.lower():
                    public_error = "Processing error occurred"
                else:
                    public_error = error_msg

                response_data = {
                    "status": "error",
                    "message": public_error,
                    "processing_time_ms": result.get("processing_time_ms", 0),
                    "webhook_id": webhook_id,
                }

            logger.info(
                "TradingView webhook response sent",
                webhook_id=webhook_id,
                status_code=status_code,
                success=result.get("success", False),
            )

            return JSONResponse(status_code=status_code, content=response_data)

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(
                "Unhandled error in webhook processing",
                webhook_id=webhook_id,
                error=str(e),
                exc_info=True,
            )

            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Internal server error",
                    "webhook_id": webhook_id,
                },
            )

    @router.post("/webhooks/tradingview/{webhook_id}/test")
    async def test_tradingview_webhook(
        webhook_id: str,
        test_payload: TradingViewOrderWebhook,
        request: Request,
        tradingview_service: TradingViewWebhookService = Depends(
            get_tradingview_service
        ),
    ) -> JSONResponse:
        """
        Test TradingView webhook with sample payload (for development/testing)

        Args:
            webhook_id: Webhook configuration ID
            test_payload: Test TradingView payload
            request: HTTP request
            tradingview_service: TradingView webhook service

        Returns:
            JSON response with test results
        """
        try:
            webhook_uuid = UUID(webhook_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid webhook ID format")

        # Convert Pydantic model to dict
        payload = test_payload.dict()
        headers = dict(request.headers)

        # Add test marker
        headers["X-Test-Mode"] = "true"
        payload["_test"] = True

        logger.info(
            "Testing TradingView webhook", webhook_id=webhook_id, test_payload=payload
        )

        try:
            result = await tradingview_service.process_tradingview_webhook(
                webhook_id=webhook_uuid,
                payload=payload,
                headers=headers,
                user_ip=request.client.host if request.client else "test",
            )

            return JSONResponse(
                status_code=200,
                content={
                    "status": "test_completed",
                    "result": result,
                    "webhook_id": webhook_id,
                    "test_payload": payload,
                },
            )

        except Exception as e:
            logger.error("Webhook test failed", webhook_id=webhook_id, error=str(e))

            return JSONResponse(
                status_code=422,
                content={
                    "status": "test_failed",
                    "error": str(e),
                    "webhook_id": webhook_id,
                },
            )

    @router.get("/webhooks/tradingview/{webhook_id}/stats")
    async def get_webhook_stats(
        webhook_id: str,
        days: int = 7,
        tradingview_service: TradingViewWebhookService = Depends(
            get_tradingview_service
        ),
    ) -> JSONResponse:
        """
        Get webhook performance statistics

        Args:
            webhook_id: Webhook configuration ID
            days: Number of days for statistics (default: 7)
            tradingview_service: TradingView webhook service

        Returns:
            JSON response with webhook statistics
        """
        try:
            webhook_uuid = UUID(webhook_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid webhook ID format")

        try:
            # For now, get user stats (would need to get user_id from webhook_id in production)
            # This is a simplified version
            stats = {
                "webhook_id": webhook_id,
                "period_days": days,
                "message": "Statistics feature requires user authentication",
                "available_endpoints": [
                    "POST /webhooks/tradingview/{webhook_id}",
                    "POST /webhooks/tradingview/{webhook_id}/test",
                    "GET /webhooks/tradingview/{webhook_id}/stats",
                ],
            }

            return JSONResponse(status_code=200, content=stats)

        except Exception as e:
            logger.error(
                "Failed to get webhook stats", webhook_id=webhook_id, error=str(e)
            )

            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Failed to retrieve statistics",
                    "webhook_id": webhook_id,
                },
            )

    @router.post("/webhooks/tradingview/{webhook_id}/retry")
    async def retry_webhook_delivery(
        webhook_id: str,
        delivery_id: str,
        tradingview_service: TradingViewWebhookService = Depends(
            get_tradingview_service
        ),
    ) -> JSONResponse:
        """
        Retry failed webhook delivery

        Args:
            webhook_id: Webhook configuration ID
            delivery_id: Webhook delivery ID to retry
            tradingview_service: TradingView webhook service

        Returns:
            JSON response with retry status
        """
        try:
            webhook_uuid = UUID(webhook_id)
            delivery_uuid = UUID(delivery_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")

        try:
            success = await tradingview_service.retry_failed_delivery(delivery_uuid)

            return JSONResponse(
                status_code=200,
                content={
                    "status": "retry_completed" if success else "retry_failed",
                    "success": success,
                    "webhook_id": webhook_id,
                    "delivery_id": delivery_id,
                },
            )

        except Exception as e:
            logger.error(
                "Webhook retry failed",
                webhook_id=webhook_id,
                delivery_id=delivery_id,
                error=str(e),
            )

            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Retry operation failed",
                    "webhook_id": webhook_id,
                    "delivery_id": delivery_id,
                },
            )

    return router
