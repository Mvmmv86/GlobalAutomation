"""TradingView webhook processing service"""

import hmac
import hashlib
import json
from typing import Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime

from infrastructure.database.repositories import (
    WebhookRepository,
    WebhookDeliveryRepository,
    UserRepository,
    OrderRepository,
)
from infrastructure.database.models.webhook import (
    Webhook,
    WebhookDelivery,
    WebhookDeliveryStatus,
)
from presentation.schemas.tradingview import (
    TradingViewWebhookBase,
    TradingViewOrderWebhook,
    TradingViewPositionWebhook,
    TradingViewSignalWebhook,
    WebhookValidationError,
)


class TradingViewService:
    """Service for TradingView webhook processing"""

    def __init__(
        self,
        webhook_repository: WebhookRepository,
        webhook_delivery_repository: WebhookDeliveryRepository,
        user_repository: UserRepository,
        order_repository: OrderRepository,
    ):
        self.webhook_repository = webhook_repository
        self.webhook_delivery_repository = webhook_delivery_repository
        self.user_repository = user_repository
        self.order_repository = order_repository

    def verify_hmac_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature for webhook security"""
        if not signature or not secret:
            return False

        # Handle different signature formats
        if signature.startswith("sha256="):
            signature = signature[7:]  # Remove 'sha256=' prefix
        elif signature.startswith("sha1="):
            signature = signature[5:]  # Remove 'sha1=' prefix
            # Use SHA1 for compatibility
            expected_signature = hmac.new(
                secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1
            ).hexdigest()
            return hmac.compare_digest(expected_signature, signature)

        # Default to SHA256
        expected_signature = hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    def parse_tradingview_webhook(
        self, payload: Dict[str, Any]
    ) -> Tuple[Optional[TradingViewWebhookBase], Optional[WebhookValidationError]]:
        """Parse and validate TradingView webhook payload"""
        try:
            # Determine webhook type based on payload content
            if "quantity" in payload or "order_type" in payload:
                # Order webhook
                webhook = TradingViewOrderWebhook(**payload)
            elif "size" in payload or "pnl" in payload:
                # Position webhook
                webhook = TradingViewPositionWebhook(**payload)
            elif "signal_strength" in payload or "rsi" in payload:
                # Signal webhook
                webhook = TradingViewSignalWebhook(**payload)
            else:
                # Basic webhook
                webhook = TradingViewWebhookBase(**payload)

            return webhook, None

        except ValueError as e:
            return None, WebhookValidationError(
                error_type="format", message=str(e), code="INVALID_FORMAT"
            )
        except Exception as e:
            return None, WebhookValidationError(
                error_type="payload",
                message=f"Invalid payload: {str(e)}",
                code="PAYLOAD_ERROR",
            )

    async def process_webhook_delivery(
        self,
        webhook_url_path: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        signature: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Process incoming webhook delivery"""
        processing_start = datetime.now()

        # Find webhook by URL path
        webhook = await self.webhook_repository.get_by_url_path(webhook_url_path)

        if not webhook:
            return False, {"error": "Webhook not found", "code": "WEBHOOK_NOT_FOUND"}

        if not webhook.is_active:
            return False, {"error": "Webhook is not active", "code": "WEBHOOK_INACTIVE"}

        # Create delivery record
        delivery_data = {
            "webhook_id": webhook.id,
            "payload": payload,
            "headers": headers,
            "status": WebhookDeliveryStatus.PROCESSING,
            "processing_started_at": processing_start,
        }

        delivery = await self.webhook_delivery_repository.create(delivery_data)

        try:
            # Verify HMAC signature if webhook has secret
            if webhook.secret and signature:
                payload_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
                if not self.verify_hmac_signature(
                    payload_str, signature, webhook.secret
                ):
                    await self._mark_delivery_failed(
                        delivery.id,
                        "Invalid HMAC signature",
                        {"signature_provided": bool(signature)},
                    )
                    return False, {
                        "error": "Invalid signature",
                        "code": "INVALID_SIGNATURE",
                    }

            # Parse TradingView webhook
            parsed_webhook, validation_error = self.parse_tradingview_webhook(payload)

            if validation_error:
                await self._mark_delivery_failed(
                    delivery.id,
                    validation_error.message,
                    {"validation_error": validation_error.dict()},
                )
                return False, {
                    "error": validation_error.message,
                    "code": validation_error.code,
                }

            # Process the webhook based on type
            processing_result = await self._process_webhook_content(
                webhook, parsed_webhook, delivery
            )

            # Calculate processing duration
            processing_duration = int(
                (datetime.now() - processing_start).total_seconds() * 1000
            )

            # Update delivery with results
            await self.webhook_delivery_repository.update(
                delivery.id,
                {
                    "orders_created": processing_result.get("orders_created", 0),
                    "orders_executed": processing_result.get("orders_executed", 0),
                    "orders_failed": processing_result.get("orders_failed", 0),
                    "processing_duration_ms": processing_duration,
                },
            )

            # Mark as success
            await self.webhook_delivery_repository.update_delivery_status(
                delivery.id, WebhookDeliveryStatus.SUCCESS
            )

            # Update webhook stats
            await self.webhook_repository.record_delivery_stats(webhook.id, True)

            return True, {
                "message": "Webhook processed successfully",
                "delivery_id": str(delivery.id),
                "processing_time_ms": processing_duration,
                "orders_created": processing_result.get("orders_created", 0),
                "orders_executed": processing_result.get("orders_executed", 0),
            }

        except Exception as e:
            # Mark as failed
            await self._mark_delivery_failed(
                delivery.id, str(e), {"error_type": type(e).__name__}
            )

            # Update webhook stats
            await self.webhook_repository.record_delivery_stats(webhook.id, False)

            return False, {
                "error": f"Processing failed: {str(e)}",
                "code": "PROCESSING_ERROR",
                "delivery_id": str(delivery.id),
            }

    async def _process_webhook_content(
        self,
        webhook: Webhook,
        parsed_webhook: TradingViewWebhookBase,
        delivery: WebhookDelivery,
    ) -> Dict[str, int]:
        """Process webhook content based on type"""

        # This is where the actual trading logic would go
        # For now, return mock statistics

        orders_created = 0
        orders_executed = 0
        orders_failed = 0

        try:
            # Determine action based on webhook type
            if isinstance(parsed_webhook, TradingViewOrderWebhook):
                # Handle order webhook
                result = await self._process_order_webhook(webhook, parsed_webhook)
                orders_created = result.get("created", 0)
                orders_executed = result.get("executed", 0)
                orders_failed = result.get("failed", 0)

            elif isinstance(parsed_webhook, TradingViewPositionWebhook):
                # Handle position webhook
                result = await self._process_position_webhook(webhook, parsed_webhook)

            elif isinstance(parsed_webhook, TradingViewSignalWebhook):
                # Handle signal webhook
                result = await self._process_signal_webhook(webhook, parsed_webhook)

            else:
                # Handle basic webhook
                orders_created = 1  # Mock order creation

        except Exception as e:
            orders_failed = 1
            raise e

        return {
            "orders_created": orders_created,
            "orders_executed": orders_executed,
            "orders_failed": orders_failed,
        }

    async def _process_order_webhook(
        self, webhook: Webhook, order_webhook: TradingViewOrderWebhook
    ) -> Dict[str, int]:
        """Process order-specific webhook"""
        # Mock implementation - in production, this would:
        # 1. Select appropriate exchange account
        # 2. Calculate position size based on risk management
        # 3. Create order through exchange adapter
        # 4. Handle stop loss / take profit orders

        return {
            "created": 1,
            "executed": 0 if order_webhook.order_type == "limit" else 1,
            "failed": 0,
        }

    async def _process_position_webhook(
        self, webhook: Webhook, position_webhook: TradingViewPositionWebhook
    ) -> Dict[str, int]:
        """Process position-specific webhook"""
        # Mock implementation - would handle position management

        if position_webhook.action == "close":
            return {"created": 1, "executed": 1, "failed": 0}

        return {"created": 0, "executed": 0, "failed": 0}

    async def _process_signal_webhook(
        self, webhook: Webhook, signal_webhook: TradingViewSignalWebhook
    ) -> Dict[str, int]:
        """Process signal-specific webhook"""
        # Mock implementation - would handle trading signals

        # Only act on strong signals
        if signal_webhook.signal_strength == "strong":
            return {"created": 1, "executed": 1, "failed": 0}

        return {"created": 0, "executed": 0, "failed": 0}

    async def _mark_delivery_failed(
        self,
        delivery_id: UUID,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark delivery as failed with error details"""
        await self.webhook_delivery_repository.update_delivery_status(
            delivery_id,
            WebhookDeliveryStatus.FAILED,
            error_message=error_message,
            error_details=error_details,
        )

    async def get_webhook_by_url_path(self, url_path: str) -> Optional[Webhook]:
        """Get webhook by URL path"""
        return await self.webhook_repository.get_by_url_path(url_path)

    async def get_delivery_status(self, delivery_id: UUID) -> Optional[WebhookDelivery]:
        """Get delivery status"""
        return await self.webhook_delivery_repository.get(delivery_id)

    async def retry_failed_delivery(
        self, delivery_id: UUID, delay_seconds: int = 300
    ) -> bool:
        """Retry failed delivery"""
        delivery = await self.webhook_delivery_repository.get(delivery_id)

        if not delivery or delivery.status != WebhookDeliveryStatus.FAILED:
            return False

        # Reset to pending and schedule retry
        await self.webhook_delivery_repository.update_delivery_status(
            delivery_id, WebhookDeliveryStatus.RETRYING
        )

        return await self.webhook_delivery_repository.schedule_retry(
            delivery_id, delay_seconds
        )

    async def get_webhook_stats(
        self, webhook_id: UUID, days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive webhook statistics"""

        # Get webhook performance stats
        performance_stats = await self.webhook_repository.get_performance_stats(
            None,  # user_id - not filtering by user
            days,
        )

        # Get delivery stats
        delivery_stats = await self.webhook_delivery_repository.get_delivery_stats(
            webhook_id, days
        )

        return {**performance_stats, **delivery_stats, "period_days": days}

    async def cleanup_old_deliveries(
        self, days_old: int = 90, keep_failed: bool = True
    ) -> int:
        """Clean up old delivery records"""
        return await self.webhook_delivery_repository.cleanup_old_deliveries(
            days_old, keep_failed
        )
