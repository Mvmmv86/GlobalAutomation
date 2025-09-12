"""Webhook and WebhookDelivery repositories"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import and_, select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.models.webhook import (
    Webhook,
    WebhookDelivery,
    WebhookStatus,
    WebhookDeliveryStatus,
)
from infrastructure.database.repositories.base import BaseRepository


class WebhookRepository(BaseRepository[Webhook]):
    """Repository for Webhook operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(Webhook, session)

    async def get_by_url_path(self, url_path: str) -> Optional[Webhook]:
        """Get webhook by URL path"""
        result = await self.session.execute(
            select(Webhook).where(Webhook.url_path == url_path)
        )
        return result.scalar_one_or_none()

    async def get_user_webhooks(
        self, user_id: Union[str, UUID], status: Optional[WebhookStatus] = None
    ) -> List[Webhook]:
        """Get all webhooks for a user"""
        filters = {"user_id": str(user_id)}
        if status:
            filters["status"] = status

        return await self.get_multi(filters=filters, order_by="-created_at")

    async def get_active_webhooks(
        self, user_id: Optional[Union[str, UUID]] = None
    ) -> List[Webhook]:
        """Get all active webhooks"""
        filters = {"status": WebhookStatus.ACTIVE}
        if user_id:
            filters["user_id"] = str(user_id)

        return await self.get_multi(filters=filters)

    async def get_with_deliveries(
        self, webhook_id: Union[str, UUID], limit_deliveries: int = 50
    ) -> Optional[Webhook]:
        """Get webhook with recent deliveries"""
        result = await self.session.execute(
            select(Webhook)
            .options(selectinload(Webhook.deliveries).limit(limit_deliveries))
            .where(Webhook.id == str(webhook_id))
        )
        return result.scalar_one_or_none()

    async def get_webhooks_needing_attention(self) -> List[Webhook]:
        """Get webhooks that need attention (errors, high failure rate)"""
        result = await self.session.execute(
            select(Webhook).where(
                or_(
                    Webhook.status == WebhookStatus.ERROR,
                    and_(
                        Webhook.consecutive_errors >= Webhook.error_threshold,
                        Webhook.status == WebhookStatus.PAUSED,
                    ),
                )
            )
        )
        return list(result.scalars().all())

    async def record_delivery_stats(
        self, webhook_id: Union[str, UUID], success: bool
    ) -> bool:
        """Record delivery statistics"""
        webhook = await self.get(webhook_id)
        if webhook:
            webhook.increment_delivery_stats(success)
            await self.session.flush()
            return True
        return False

    async def get_performance_stats(
        self, user_id: Optional[Union[str, UUID]] = None, days: int = 30
    ) -> Dict[str, Any]:
        """Get webhook performance statistics"""
        base_query = select(Webhook)

        if user_id:
            base_query = base_query.where(Webhook.user_id == str(user_id))

        # Basic stats
        stats_result = await self.session.execute(
            base_query.with_only_columns(
                func.count(Webhook.id).label("total_webhooks"),
                func.sum(Webhook.total_deliveries).label("total_deliveries"),
                func.sum(Webhook.successful_deliveries).label("successful_deliveries"),
                func.sum(Webhook.failed_deliveries).label("failed_deliveries"),
                func.avg(
                    Webhook.successful_deliveries
                    * 100.0
                    / func.nullif(Webhook.total_deliveries, 0)
                ).label("avg_success_rate"),
            )
        )

        stats = stats_result.first()

        # Status distribution
        status_result = await self.session.execute(
            base_query.with_only_columns(
                Webhook.status, func.count(Webhook.id).label("count")
            ).group_by(Webhook.status)
        )

        status_distribution = {row.status.value: row.count for row in status_result}

        return {
            "total_webhooks": stats.total_webhooks or 0,
            "total_deliveries": stats.total_deliveries or 0,
            "successful_deliveries": stats.successful_deliveries or 0,
            "failed_deliveries": stats.failed_deliveries or 0,
            "average_success_rate": float(stats.avg_success_rate or 0),
            "status_distribution": status_distribution,
        }

    async def get_most_active_webhooks(
        self, limit: int = 10, user_id: Optional[Union[str, UUID]] = None
    ) -> List[Webhook]:
        """Get most active webhooks by delivery count"""
        query = select(Webhook).order_by(Webhook.total_deliveries.desc()).limit(limit)

        if user_id:
            query = query.where(Webhook.user_id == str(user_id))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_webhooks(
        self,
        search_term: str,
        user_id: Optional[Union[str, UUID]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Webhook]:
        """Search webhooks by name or URL path"""
        query = (
            self._build_query(
                filters={"user_id": str(user_id)} if user_id else None,
                search=search_term,
                search_fields=["name", "url_path"],
            )
            .offset(skip)
            .limit(limit)
            .order_by(Webhook.created_at.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())


class WebhookDeliveryRepository(BaseRepository[WebhookDelivery]):
    """Repository for WebhookDelivery operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(WebhookDelivery, session)

    async def get_webhook_deliveries(
        self,
        webhook_id: Union[str, UUID],
        status: Optional[WebhookDeliveryStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WebhookDelivery]:
        """Get deliveries for a specific webhook"""
        filters = {"webhook_id": str(webhook_id)}
        if status:
            filters["status"] = status

        return await self.get_multi(
            filters=filters, skip=skip, limit=limit, order_by="-created_at"
        )

    async def get_failed_deliveries(
        self,
        webhook_id: Optional[Union[str, UUID]] = None,
        max_retries: Optional[int] = None,
    ) -> List[WebhookDelivery]:
        """Get failed deliveries for retry"""
        conditions = [WebhookDelivery.status == WebhookDeliveryStatus.FAILED]

        if webhook_id:
            conditions.append(WebhookDelivery.webhook_id == str(webhook_id))
        if max_retries is not None:
            conditions.append(WebhookDelivery.retry_count < max_retries)

        result = await self.session.execute(
            select(WebhookDelivery)
            .options(selectinload(WebhookDelivery.webhook))
            .where(and_(*conditions))
            .order_by(WebhookDelivery.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_pending_retries(self) -> List[WebhookDelivery]:
        """Get deliveries ready for retry"""
        result = await self.session.execute(
            select(WebhookDelivery)
            .options(selectinload(WebhookDelivery.webhook))
            .where(
                and_(
                    WebhookDelivery.status == WebhookDeliveryStatus.RETRYING,
                    WebhookDelivery.next_retry_at <= func.now(),
                )
            )
            .order_by(WebhookDelivery.next_retry_at.asc())
        )
        return list(result.scalars().all())

    async def get_deliveries_by_timeframe(
        self,
        start_time: datetime,
        end_time: datetime,
        webhook_id: Optional[Union[str, UUID]] = None,
        status: Optional[WebhookDeliveryStatus] = None,
    ) -> List[WebhookDelivery]:
        """Get deliveries within a time frame"""
        conditions = [
            WebhookDelivery.created_at >= start_time,
            WebhookDelivery.created_at <= end_time,
        ]

        if webhook_id:
            conditions.append(WebhookDelivery.webhook_id == str(webhook_id))
        if status:
            conditions.append(WebhookDelivery.status == status)

        result = await self.session.execute(
            select(WebhookDelivery)
            .where(and_(*conditions))
            .order_by(WebhookDelivery.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_processing_deliveries(
        self, timeout_minutes: int = 30
    ) -> List[WebhookDelivery]:
        """Get deliveries that are stuck in processing state"""
        timeout_time = datetime.now() - timedelta(minutes=timeout_minutes)

        result = await self.session.execute(
            select(WebhookDelivery).where(
                and_(
                    WebhookDelivery.status == WebhookDeliveryStatus.PROCESSING,
                    WebhookDelivery.processing_started_at < timeout_time,
                )
            )
        )
        return list(result.scalars().all())

    async def update_delivery_status(
        self,
        delivery_id: Union[str, UUID],
        status: WebhookDeliveryStatus,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update delivery status"""
        delivery = await self.get(delivery_id)
        if not delivery:
            return False

        if status == WebhookDeliveryStatus.PROCESSING:
            delivery.mark_processing()
        elif status == WebhookDeliveryStatus.SUCCESS:
            delivery.mark_success()
        elif status == WebhookDeliveryStatus.FAILED:
            delivery.mark_failed(error_message or "Unknown error", error_details)

        await self.session.flush()
        return True

    async def schedule_retry(
        self, delivery_id: Union[str, UUID], delay_seconds: int
    ) -> bool:
        """Schedule delivery for retry"""
        delivery = await self.get(delivery_id)
        if delivery:
            delivery.schedule_retry(delay_seconds)
            await self.session.flush()
            return True
        return False

    async def get_delivery_stats(
        self, webhook_id: Optional[Union[str, UUID]] = None, days: int = 30
    ) -> Dict[str, Any]:
        """Get delivery statistics"""
        start_time = datetime.now() - timedelta(days=days)
        base_query = select(WebhookDelivery).where(
            WebhookDelivery.created_at >= start_time
        )

        if webhook_id:
            base_query = base_query.where(WebhookDelivery.webhook_id == str(webhook_id))

        # Basic stats
        stats_result = await self.session.execute(
            base_query.with_only_columns(
                func.count(WebhookDelivery.id).label("total_deliveries"),
                func.avg(WebhookDelivery.processing_duration_ms).label(
                    "avg_processing_time"
                ),
                func.max(WebhookDelivery.processing_duration_ms).label(
                    "max_processing_time"
                ),
                func.min(WebhookDelivery.processing_duration_ms).label(
                    "min_processing_time"
                ),
                func.sum(WebhookDelivery.orders_created).label("total_orders_created"),
                func.sum(WebhookDelivery.orders_executed).label(
                    "total_orders_executed"
                ),
                func.sum(WebhookDelivery.orders_failed).label("total_orders_failed"),
            )
        )

        stats = stats_result.first()

        # Status distribution
        status_result = await self.session.execute(
            base_query.with_only_columns(
                WebhookDelivery.status, func.count(WebhookDelivery.id).label("count")
            ).group_by(WebhookDelivery.status)
        )

        status_distribution = {row.status.value: row.count for row in status_result}

        # Hourly distribution
        hourly_result = await self.session.execute(
            base_query.with_only_columns(
                func.extract("hour", WebhookDelivery.created_at).label("hour"),
                func.count(WebhookDelivery.id).label("count"),
            )
            .group_by(func.extract("hour", WebhookDelivery.created_at))
            .order_by(func.extract("hour", WebhookDelivery.created_at))
        )

        hourly_distribution = {int(row.hour): row.count for row in hourly_result}

        return {
            "total_deliveries": stats.total_deliveries or 0,
            "average_processing_time_ms": float(stats.avg_processing_time or 0),
            "max_processing_time_ms": stats.max_processing_time or 0,
            "min_processing_time_ms": stats.min_processing_time or 0,
            "total_orders_created": stats.total_orders_created or 0,
            "total_orders_executed": stats.total_orders_executed or 0,
            "total_orders_failed": stats.total_orders_failed or 0,
            "status_distribution": status_distribution,
            "hourly_distribution": hourly_distribution,
        }

    async def cleanup_old_deliveries(
        self, days_old: int = 90, keep_failed: bool = True
    ) -> int:
        """Clean up old delivery records"""
        cutoff_date = datetime.now() - timedelta(days=days_old)

        conditions = [WebhookDelivery.created_at < cutoff_date]

        if keep_failed:
            conditions.append(WebhookDelivery.status != WebhookDeliveryStatus.FAILED)

        result = await self.session.execute(
            select(func.count(WebhookDelivery.id)).where(and_(*conditions))
        )
        count = result.scalar() or 0

        # Perform the deletion
        await self.session.execute(delete(WebhookDelivery).where(and_(*conditions)))

        return count
