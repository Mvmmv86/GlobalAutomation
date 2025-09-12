"""Webhook service with business logic"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import hmac
import hashlib
import json

from infrastructure.database.repositories import (
    WebhookRepository,
    WebhookDeliveryRepository,
    UserRepository,
)
from infrastructure.database.models.webhook import (
    Webhook,
    WebhookDelivery,
    WebhookDeliveryStatus,
)


class WebhookService:
    """Business logic for webhook operations"""

    def __init__(
        self,
        webhook_repository: WebhookRepository,
        webhook_delivery_repository: WebhookDeliveryRepository,
        user_repository: UserRepository,
    ):
        self.webhook_repository = webhook_repository
        self.webhook_delivery_repository = webhook_delivery_repository
        self.user_repository = user_repository

    def verify_webhook_signature(
        self, payload: str, signature: str, secret: str
    ) -> bool:
        """Verify HMAC signature for webhook security"""
        if not signature.startswith("sha256="):
            return False

        expected_signature = hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        received_signature = signature[7:]  # Remove 'sha256=' prefix

        return hmac.compare_digest(expected_signature, received_signature)

    async def create_webhook(
        self, user_id: UUID, webhook_data: Dict[str, Any]
    ) -> Webhook:
        """Create a new webhook for user"""
        # Verify user exists
        user = await self.user_repository.get(user_id)
        if not user:
            raise ValueError("User not found")

        webhook_data["user_id"] = str(user_id)
        return await self.webhook_repository.create(webhook_data)

    async def get_user_webhooks(self, user_id: UUID) -> List[Webhook]:
        """Get all webhooks for a user"""
        return await self.webhook_repository.get_user_webhooks(user_id)

    async def get_webhook_by_url_path(self, url_path: str) -> Optional[Webhook]:
        """Get webhook by URL path"""
        return await self.webhook_repository.get_by_url_path(url_path)

    async def process_webhook_delivery(
        self,
        webhook: Webhook,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        signature: Optional[str] = None,
    ) -> WebhookDelivery:
        """Process incoming webhook delivery"""

        # Create delivery record
        delivery_data = {
            "webhook_id": webhook.id,
            "payload": payload,
            "headers": headers,
            "status": WebhookDeliveryStatus.PROCESSING,
            "processing_started_at": datetime.now(),
        }

        delivery = await self.webhook_delivery_repository.create(delivery_data)

        try:
            # Verify HMAC signature if webhook has secret
            if webhook.secret and signature:
                if not self.verify_webhook_signature(
                    json.dumps(payload, separators=(",", ":"), sort_keys=True),
                    signature,
                    webhook.secret,
                ):
                    await self.webhook_delivery_repository.update_delivery_status(
                        delivery.id,
                        WebhookDeliveryStatus.FAILED,
                        error_message="Invalid HMAC signature",
                        error_details={"signature_provided": bool(signature)},
                    )
                    raise ValueError("Invalid HMAC signature")

            # Mark as processing
            await self.webhook_delivery_repository.update_delivery_status(
                delivery.id, WebhookDeliveryStatus.PROCESSING
            )

            # Process the webhook based on type
            result = await self._process_webhook_content(webhook, payload)

            # Update delivery with results
            processing_duration = int(
                (datetime.now() - delivery.processing_started_at).total_seconds() * 1000
            )

            await self.webhook_delivery_repository.update(
                delivery.id,
                {
                    "orders_created": result.get("orders_created", 0),
                    "orders_executed": result.get("orders_executed", 0),
                    "orders_failed": result.get("orders_failed", 0),
                    "processing_duration_ms": processing_duration,
                },
            )

            # Mark as success
            await self.webhook_delivery_repository.update_delivery_status(
                delivery.id, WebhookDeliveryStatus.SUCCESS
            )

            # Update webhook stats
            await self.webhook_repository.record_delivery_stats(webhook.id, True)

        except Exception as e:
            # Mark as failed
            await self.webhook_delivery_repository.update_delivery_status(
                delivery.id,
                WebhookDeliveryStatus.FAILED,
                error_message=str(e),
                error_details={"error_type": type(e).__name__},
            )

            # Update webhook stats
            await self.webhook_repository.record_delivery_stats(webhook.id, False)

            raise

        return delivery

    async def _process_webhook_content(
        self, webhook: Webhook, payload: Dict[str, Any]
    ) -> Dict[str, int]:
        """Process webhook content based on type - placeholder for business logic"""
        # This would contain the actual trading logic
        # For now, return dummy stats
        return {"orders_created": 1, "orders_executed": 1, "orders_failed": 0}

    async def retry_failed_delivery(
        self, delivery_id: UUID, delay_seconds: int = 300
    ) -> bool:
        """Retry a failed webhook delivery"""
        delivery = await self.webhook_delivery_repository.get(delivery_id)

        if not delivery or delivery.status != WebhookDeliveryStatus.FAILED:
            return False

        # Schedule retry
        return await self.webhook_delivery_repository.schedule_retry(
            delivery_id, delay_seconds
        )

    async def get_webhook_performance_stats(
        self, user_id: Optional[UUID] = None, days: int = 30
    ) -> Dict[str, Any]:
        """Get webhook performance statistics"""
        return await self.webhook_repository.get_performance_stats(user_id, days)

    async def get_delivery_stats(
        self, webhook_id: Optional[UUID] = None, days: int = 30
    ) -> Dict[str, Any]:
        """Get delivery statistics"""
        return await self.webhook_delivery_repository.get_delivery_stats(
            webhook_id, days
        )

    async def get_failed_deliveries(
        self, webhook_id: Optional[UUID] = None, max_retries: int = 3
    ) -> List[WebhookDelivery]:
        """Get failed deliveries that can be retried"""
        return await self.webhook_delivery_repository.get_failed_deliveries(
            webhook_id, max_retries
        )

    async def get_pending_retries(self) -> List[WebhookDelivery]:
        """Get deliveries that are ready for retry"""
        return await self.webhook_delivery_repository.get_pending_retries()

    async def update_webhook(
        self, webhook_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Webhook]:
        """Update webhook configuration"""
        # Remove sensitive fields that shouldn't be updated directly
        sensitive_fields = {
            "secret",
            "total_deliveries",
            "successful_deliveries",
            "failed_deliveries",
        }
        update_data = {
            k: v for k, v in update_data.items() if k not in sensitive_fields
        }

        return await self.webhook_repository.update(webhook_id, update_data)

    async def delete_webhook(self, webhook_id: UUID, user_id: UUID) -> bool:
        """Delete webhook (user must own it)"""
        webhook = await self.webhook_repository.get(webhook_id)

        if not webhook or webhook.user_id != str(user_id):
            return False

        return await self.webhook_repository.soft_delete(webhook_id)

    async def get_webhook_deliveries(
        self, webhook_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[WebhookDelivery]:
        """Get deliveries for a webhook"""
        return await self.webhook_delivery_repository.get_webhook_deliveries(
            webhook_id, skip=skip, limit=limit
        )

    async def cleanup_old_deliveries(
        self, days_old: int = 90, keep_failed: bool = True
    ) -> int:
        """Clean up old delivery records"""
        return await self.webhook_delivery_repository.cleanup_old_deliveries(
            days_old, keep_failed
        )
