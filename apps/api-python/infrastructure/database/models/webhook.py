"""Webhook and WebhookDelivery models for TradingView integration"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .base import Base


class WebhookStatus(str, Enum):
    """Webhook status types"""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"


class WebhookDeliveryStatus(str, Enum):
    """Webhook delivery status types"""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class Webhook(Base):
    """Webhook configuration for TradingView alerts"""

    __tablename__ = "webhooks"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), comment="User-friendly webhook name")

    url_path: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, comment="Unique URL path for this webhook"
    )

    secret: Mapped[str] = mapped_column(
        String(255), comment="Webhook secret for HMAC validation"
    )

    # Status and configuration
    status: Mapped[WebhookStatus] = mapped_column(
        SQLEnum(WebhookStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=WebhookStatus.ACTIVE,
        comment="Webhook status"
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Allow unauthenticated access"
    )

    # Rate limiting
    rate_limit_per_minute: Mapped[int] = mapped_column(
        default=60, comment="Rate limit per minute"
    )

    rate_limit_per_hour: Mapped[int] = mapped_column(
        default=1000, comment="Rate limit per hour"
    )

    # Retry configuration
    max_retries: Mapped[int] = mapped_column(
        default=3, comment="Maximum retry attempts for failed deliveries"
    )

    retry_delay_seconds: Mapped[int] = mapped_column(
        default=60, comment="Delay between retry attempts"
    )

    # Filtering and validation
    allowed_ips: Mapped[Optional[str]] = mapped_column(
        Text, comment="JSON array of allowed IP addresses"
    )

    required_headers: Mapped[Optional[str]] = mapped_column(
        Text, comment="JSON object of required headers"
    )

    payload_validation_schema: Mapped[Optional[str]] = mapped_column(
        Text, comment="JSON schema for payload validation"
    )

    # Statistics
    total_deliveries: Mapped[int] = mapped_column(
        default=0, comment="Total webhook deliveries"
    )

    successful_deliveries: Mapped[int] = mapped_column(
        default=0, comment="Successful deliveries count"
    )

    failed_deliveries: Mapped[int] = mapped_column(
        default=0, comment="Failed deliveries count"
    )

    last_delivery_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Last delivery attempt timestamp"
    )

    last_success_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Last successful delivery timestamp"
    )

    # Configuration
    auto_pause_on_errors: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Auto-pause webhook after consecutive errors"
    )

    error_threshold: Mapped[int] = mapped_column(
        default=10, comment="Error count threshold for auto-pause"
    )

    consecutive_errors: Mapped[int] = mapped_column(
        default=0, comment="Current consecutive error count"
    )

    # Trading Parameters
    market_type: Mapped[Optional[str]] = mapped_column(
        String(50), default="futures", comment="Market type: futures or spot"
    )

    default_margin_usd: Mapped[float] = mapped_column(
        default=100.00, comment="Default margin in USD to use per order (min: $10)"
    )

    default_leverage: Mapped[int] = mapped_column(
        default=10, comment="Default leverage multiplier (1x - 125x)"
    )

    default_stop_loss_pct: Mapped[float] = mapped_column(
        default=3.00, comment="Default stop loss percentage (0.1% - 100%)"
    )

    default_take_profit_pct: Mapped[float] = mapped_column(
        default=5.00, comment="Default take profit percentage (0.1% - 1000%)"
    )

    # Relationships
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        comment="User owner ID",
    )

    user: Mapped["User"] = relationship("User", back_populates="webhooks")

    deliveries: Mapped[List["WebhookDelivery"]] = relationship(
        "WebhookDelivery",
        back_populates="webhook",
        cascade="all, delete-orphan",
        order_by="WebhookDelivery.created_at.desc()",
    )

    def __init__(self, **kwargs):
        """Initialize Webhook with default values"""
        # Set defaults
        kwargs.setdefault("status", WebhookStatus.ACTIVE)
        kwargs.setdefault("is_public", False)
        kwargs.setdefault("rate_limit_per_minute", 60)
        kwargs.setdefault("rate_limit_per_hour", 1000)
        kwargs.setdefault("max_retries", 3)
        kwargs.setdefault("retry_delay_seconds", 60)
        kwargs.setdefault("total_deliveries", 0)
        kwargs.setdefault("successful_deliveries", 0)
        kwargs.setdefault("failed_deliveries", 0)
        kwargs.setdefault("auto_pause_on_errors", True)
        kwargs.setdefault("error_threshold", 10)
        kwargs.setdefault("consecutive_errors", 0)
        # Trading parameters defaults
        kwargs.setdefault("market_type", "futures")
        kwargs.setdefault("default_margin_usd", 100.00)
        kwargs.setdefault("default_leverage", 10)
        kwargs.setdefault("default_stop_loss_pct", 3.00)
        kwargs.setdefault("default_take_profit_pct", 5.00)
        super().__init__(**kwargs)

    def activate(self) -> None:
        """Activate webhook"""
        self.status = WebhookStatus.ACTIVE
        self.consecutive_errors = 0

    def pause(self) -> None:
        """Pause webhook"""
        self.status = WebhookStatus.PAUSED

    def disable(self) -> None:
        """Disable webhook"""
        self.status = WebhookStatus.DISABLED

    def mark_error(self) -> None:
        """Mark webhook as having errors"""
        self.status = WebhookStatus.ERROR

    def increment_delivery_stats(self, success: bool) -> None:
        """Update delivery statistics"""
        self.total_deliveries += 1
        self.last_delivery_at = datetime.now(timezone.utc)

        if success:
            self.successful_deliveries += 1
            self.last_success_at = datetime.now(timezone.utc)
            self.consecutive_errors = 0
        else:
            self.failed_deliveries += 1
            self.consecutive_errors += 1

            # Auto-pause on error threshold
            if (
                self.auto_pause_on_errors
                and self.consecutive_errors >= self.error_threshold
            ):
                self.pause()

    def get_success_rate(self) -> float:
        """Calculate delivery success rate"""
        if self.total_deliveries == 0:
            return 0.0
        return (self.successful_deliveries / self.total_deliveries) * 100

    def is_active(self) -> bool:
        """Check if webhook is active"""
        return self.status == WebhookStatus.ACTIVE

    def can_receive_deliveries(self) -> bool:
        """Check if webhook can receive new deliveries"""
        return self.status in [WebhookStatus.ACTIVE, WebhookStatus.ERROR]


class WebhookDelivery(Base):
    """Individual webhook delivery record"""

    __tablename__ = "webhook_deliveries"

    # Delivery info
    status: Mapped[WebhookDeliveryStatus] = mapped_column(
        SQLEnum(WebhookDeliveryStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=WebhookDeliveryStatus.PENDING,
        comment="Delivery status",
    )

    # Request data
    payload: Mapped[dict] = mapped_column(JSONB, comment="Original webhook payload")

    headers: Mapped[dict] = mapped_column(JSONB, comment="Request headers")

    source_ip: Mapped[Optional[str]] = mapped_column(
        String(45), comment="Source IP address"
    )

    user_agent: Mapped[Optional[str]] = mapped_column(Text, comment="User agent string")

    # Processing results
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Processing start timestamp"
    )

    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Processing completion timestamp"
    )

    processing_duration_ms: Mapped[Optional[int]] = mapped_column(
        comment="Processing duration in milliseconds"
    )

    # Validation results
    hmac_valid: Mapped[Optional[bool]] = mapped_column(
        Boolean, comment="HMAC signature validation result"
    )

    ip_allowed: Mapped[Optional[bool]] = mapped_column(
        Boolean, comment="IP address validation result"
    )

    headers_valid: Mapped[Optional[bool]] = mapped_column(
        Boolean, comment="Required headers validation result"
    )

    payload_valid: Mapped[Optional[bool]] = mapped_column(
        Boolean, comment="Payload schema validation result"
    )

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, comment="Error message if processing failed"
    )

    error_details: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="Detailed error information"
    )

    retry_count: Mapped[int] = mapped_column(
        default=0, comment="Number of retry attempts"
    )

    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Next retry attempt timestamp"
    )

    # Business logic results
    orders_created: Mapped[int] = mapped_column(
        default=0, comment="Number of orders created from this delivery"
    )

    orders_executed: Mapped[int] = mapped_column(
        default=0, comment="Number of orders successfully executed"
    )

    orders_failed: Mapped[int] = mapped_column(
        default=0, comment="Number of orders that failed"
    )

    # Relationships
    webhook_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        comment="Parent webhook ID",
    )

    webhook: Mapped["Webhook"] = relationship("Webhook", back_populates="deliveries")

    def __init__(self, **kwargs):
        """Initialize WebhookDelivery with default values"""
        # Set defaults
        kwargs.setdefault("status", WebhookDeliveryStatus.PENDING)
        kwargs.setdefault("retry_count", 0)
        kwargs.setdefault("orders_created", 0)
        kwargs.setdefault("orders_executed", 0)
        kwargs.setdefault("orders_failed", 0)
        super().__init__(**kwargs)

    def mark_processing(self) -> None:
        """Mark delivery as processing"""
        self.status = WebhookDeliveryStatus.PROCESSING
        self.processing_started_at = datetime.now(timezone.utc)

    def mark_success(self) -> None:
        """Mark delivery as successful"""
        self.status = WebhookDeliveryStatus.SUCCESS
        self.processing_completed_at = datetime.now(timezone.utc)
        if self.processing_started_at:
            duration = datetime.now(timezone.utc) - self.processing_started_at
            self.processing_duration_ms = int(duration.total_seconds() * 1000)

    def mark_failed(self, error: str, details: Optional[dict] = None) -> None:
        """Mark delivery as failed"""
        self.status = WebhookDeliveryStatus.FAILED
        self.processing_completed_at = datetime.now(timezone.utc)
        self.error_message = error
        if details:
            self.error_details = details
        if self.processing_started_at:
            duration = datetime.now(timezone.utc) - self.processing_started_at
            self.processing_duration_ms = int(duration.total_seconds() * 1000)

    def schedule_retry(self, delay_seconds: int) -> None:
        """Schedule delivery for retry"""
        from datetime import timedelta

        self.status = WebhookDeliveryStatus.RETRYING
        self.retry_count += 1
        self.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

    def set_validation_results(
        self,
        hmac_valid: bool,
        ip_allowed: bool,
        headers_valid: bool,
        payload_valid: bool,
    ) -> None:
        """Set validation results"""
        self.hmac_valid = hmac_valid
        self.ip_allowed = ip_allowed
        self.headers_valid = headers_valid
        self.payload_valid = payload_valid

    def update_order_stats(self, created: int, executed: int, failed: int) -> None:
        """Update order statistics"""
        self.orders_created = created
        self.orders_executed = executed
        self.orders_failed = failed

    def is_ready_for_retry(self) -> bool:
        """Check if delivery is ready for retry"""
        return (
            self.status == WebhookDeliveryStatus.RETRYING
            and self.next_retry_at is not None
            and datetime.now(timezone.utc) >= self.next_retry_at
        )
