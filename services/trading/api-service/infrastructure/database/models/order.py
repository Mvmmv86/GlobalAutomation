"""Order model for trading operations"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, NUMERIC

from .base import Base


class OrderType(str, Enum):
    """Order type enumeration"""

    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """Order side enumeration"""

    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order status enumeration"""

    PENDING = "pending"  # Created but not sent to exchange
    SUBMITTED = "submitted"  # Sent to exchange
    OPEN = "open"  # Active on exchange
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"  # Completely filled
    CANCELED = "canceled"  # Canceled by user or system
    REJECTED = "rejected"  # Rejected by exchange
    EXPIRED = "expired"  # Expired (for time-in-force orders)
    FAILED = "failed"  # Failed to submit or execute


class TimeInForce(str, Enum):
    """Time in force enumeration"""

    GTC = "gtc"  # Good Till Canceled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill
    GTD = "gtd"  # Good Till Date


class Order(Base):
    """Order model for tracking trading operations"""

    __tablename__ = "orders"

    # Order identification
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255), index=True, comment="Exchange-provided order ID"
    )

    client_order_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, comment="Client-generated unique order ID"
    )

    # Basic order info
    symbol: Mapped[str] = mapped_column(
        String(50), index=True, comment="Trading symbol (e.g., BTCUSDT)"
    )

    side: Mapped[OrderSide] = mapped_column(
        SQLEnum(OrderSide), comment="Order side (buy/sell)"
    )

    type: Mapped[OrderType] = mapped_column(SQLEnum(OrderType), comment="Order type")

    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus),
        default=OrderStatus.PENDING,
        index=True,
        comment="Current order status",
    )

    # Quantities and pricing
    quantity: Mapped[Decimal] = mapped_column(
        NUMERIC(precision=20, scale=8), comment="Order quantity"
    )

    price: Mapped[Optional[Decimal]] = mapped_column(
        NUMERIC(precision=20, scale=8), comment="Order price (null for market orders)"
    )

    stop_price: Mapped[Optional[Decimal]] = mapped_column(
        NUMERIC(precision=20, scale=8), comment="Stop price (for stop orders)"
    )

    # Execution details
    filled_quantity: Mapped[Decimal] = mapped_column(
        NUMERIC(precision=20, scale=8),
        default=Decimal("0"),
        comment="Quantity filled so far",
    )

    average_fill_price: Mapped[Optional[Decimal]] = mapped_column(
        NUMERIC(precision=20, scale=8), comment="Average fill price"
    )

    fees_paid: Mapped[Decimal] = mapped_column(
        NUMERIC(precision=20, scale=8), default=Decimal("0"), comment="Total fees paid"
    )

    fee_currency: Mapped[Optional[str]] = mapped_column(
        String(10), comment="Currency in which fees were paid"
    )

    # Time constraints
    time_in_force: Mapped[TimeInForce] = mapped_column(
        SQLEnum(TimeInForce), default=TimeInForce.GTC, comment="Time in force"
    )

    good_till_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Good till date (for GTD orders)"
    )

    # Timestamps
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="When order was submitted to exchange"
    )

    first_fill_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="First fill timestamp"
    )

    last_fill_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Last fill timestamp"
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Order completion timestamp"
    )

    # Source and context
    source: Mapped[str] = mapped_column(
        String(50),
        default="webhook",
        comment="Order source (webhook, api, manual, etc.)",
    )

    webhook_delivery_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("webhook_deliveries.id", ondelete="SET NULL"),
        comment="Source webhook delivery ID",
    )

    original_payload: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="Original webhook/API payload"
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, comment="Error message if order failed"
    )

    error_code: Mapped[Optional[str]] = mapped_column(
        String(50), comment="Exchange-specific error code"
    )

    retry_count: Mapped[int] = mapped_column(
        default=0, comment="Number of submission retry attempts"
    )

    # Exchange response
    exchange_response: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="Raw exchange API response"
    )

    # Trading configuration
    reduce_only: Mapped[bool] = mapped_column(
        default=False, comment="Reduce-only order flag"
    )

    post_only: Mapped[bool] = mapped_column(
        default=False, comment="Post-only order flag"
    )

    # Relationships
    exchange_account_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("exchange_accounts.id", ondelete="CASCADE"),
        comment="Exchange account used for this order",
    )

    exchange_account: Mapped["ExchangeAccount"] = relationship(
        "ExchangeAccount", back_populates="orders"
    )

    def __init__(self, **kwargs):
        """Initialize Order with default values"""
        from decimal import Decimal

        # Set defaults
        kwargs.setdefault("status", OrderStatus.PENDING)
        kwargs.setdefault("filled_quantity", Decimal("0"))
        kwargs.setdefault("fees_paid", Decimal("0"))
        kwargs.setdefault("time_in_force", TimeInForce.GTC)
        kwargs.setdefault("source", "webhook")
        kwargs.setdefault("retry_count", 0)
        kwargs.setdefault("reduce_only", False)
        kwargs.setdefault("post_only", False)
        super().__init__(**kwargs)

    # Business methods
    def submit(self, external_id: Optional[str] = None) -> None:
        """Mark order as submitted to exchange"""
        self.status = OrderStatus.SUBMITTED
        self.submitted_at = datetime.now()
        if external_id:
            self.external_id = external_id

    def mark_open(self) -> None:
        """Mark order as open on exchange"""
        self.status = OrderStatus.OPEN

    def add_fill(
        self,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal = Decimal("0"),
        fee_currency: Optional[str] = None,
    ) -> None:
        """Add a fill to this order"""
        # Update filled quantity
        self.filled_quantity += quantity

        # Update average fill price
        if self.average_fill_price is None:
            self.average_fill_price = price
        else:
            total_value = (
                self.average_fill_price * (self.filled_quantity - quantity)
            ) + (price * quantity)
            self.average_fill_price = total_value / self.filled_quantity

        # Update fees
        self.fees_paid += fee
        if fee_currency:
            self.fee_currency = fee_currency

        # Update timestamps
        now = datetime.now()
        if self.first_fill_at is None:
            self.first_fill_at = now
        self.last_fill_at = now

        # Update status
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
            self.completed_at = now
        else:
            self.status = OrderStatus.PARTIALLY_FILLED

    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel order"""
        self.status = OrderStatus.CANCELED
        self.completed_at = datetime.now()
        if reason:
            self.error_message = reason

    def reject(self, reason: str, error_code: Optional[str] = None) -> None:
        """Reject order"""
        self.status = OrderStatus.REJECTED
        self.completed_at = datetime.now()
        self.error_message = reason
        if error_code:
            self.error_code = error_code

    def mark_failed(self, error: str, error_code: Optional[str] = None) -> None:
        """Mark order as failed"""
        self.status = OrderStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error
        if error_code:
            self.error_code = error_code

    def mark_expired(self) -> None:
        """Mark order as expired"""
        self.status = OrderStatus.EXPIRED
        self.completed_at = datetime.now()

    def increment_retry(self) -> None:
        """Increment retry counter"""
        self.retry_count += 1

    def get_remaining_quantity(self) -> Decimal:
        """Get remaining unfilled quantity"""
        return self.quantity - self.filled_quantity

    def get_fill_percentage(self) -> float:
        """Get fill percentage"""
        if self.quantity == 0:
            return 0.0
        return float((self.filled_quantity / self.quantity) * 100)

    def is_open(self) -> bool:
        """Check if order is open"""
        return self.status in [OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]

    def is_completed(self) -> bool:
        """Check if order is completed"""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
            OrderStatus.FAILED,
        ]

    def is_fillable(self) -> bool:
        """Check if order can receive fills"""
        return self.status in [OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]
