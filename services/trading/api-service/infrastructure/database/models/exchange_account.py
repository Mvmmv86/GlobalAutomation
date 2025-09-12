"""Exchange Account model for trading connections"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class ExchangeType(str, Enum):
    """Supported exchange types"""

    BINANCE = "binance"
    BYBIT = "bybit"
    # Future exchanges can be added here


class ExchangeEnvironment(str, Enum):
    """Exchange environment types"""

    TESTNET = "testnet"
    MAINNET = "mainnet"


class ExchangeAccount(Base):
    """Exchange account model for storing API credentials and trading configuration"""

    __tablename__ = "exchange_accounts"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), comment="User-friendly account name")

    exchange_type: Mapped[ExchangeType] = mapped_column(
        SQLEnum(ExchangeType), comment="Exchange platform type"
    )

    environment: Mapped[ExchangeEnvironment] = mapped_column(
        SQLEnum(ExchangeEnvironment),
        default=ExchangeEnvironment.TESTNET,
        comment="Trading environment (testnet/mainnet)",
    )

    # API credentials (encrypted)
    api_key_encrypted: Mapped[str] = mapped_column(
        Text, comment="Encrypted exchange API key"
    )

    api_secret_encrypted: Mapped[str] = mapped_column(
        Text, comment="Encrypted exchange API secret"
    )

    passphrase_encrypted: Mapped[Optional[str]] = mapped_column(
        Text, comment="Encrypted passphrase (for exchanges that require it)"
    )

    # Status and configuration
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Account active status"
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Default account for this exchange"
    )

    # Trading configuration
    max_position_size: Mapped[Optional[str]] = mapped_column(
        String(50), comment="Maximum position size (decimal string)"
    )

    max_daily_volume: Mapped[Optional[str]] = mapped_column(
        String(50), comment="Maximum daily trading volume (decimal string)"
    )

    allowed_symbols: Mapped[Optional[str]] = mapped_column(
        Text, comment="JSON array of allowed trading symbols"
    )

    risk_level: Mapped[str] = mapped_column(
        String(20), default="medium", comment="Risk level: low, medium, high"
    )

    # Health and monitoring
    last_health_check: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Last successful health check"
    )

    health_status: Mapped[str] = mapped_column(
        String(20),
        default="unknown",
        comment="Health status: healthy, warning, error, unknown",
    )

    last_error: Mapped[Optional[str]] = mapped_column(
        Text, comment="Last API error message"
    )

    # Usage statistics
    total_orders: Mapped[int] = mapped_column(
        default=0, comment="Total orders placed through this account"
    )

    successful_orders: Mapped[int] = mapped_column(
        default=0, comment="Successful orders count"
    )

    failed_orders: Mapped[int] = mapped_column(default=0, comment="Failed orders count")

    last_trade_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Last successful trade timestamp"
    )

    # Rate limiting
    rate_limit_window: Mapped[int] = mapped_column(
        default=60, comment="Rate limit window in seconds"
    )

    rate_limit_requests: Mapped[int] = mapped_column(
        default=1200, comment="Max requests per window"
    )

    # Relationships
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        comment="User owner ID",
    )

    user: Mapped["User"] = relationship("User", back_populates="exchange_accounts")

    orders: Mapped[List["Order"]] = relationship(
        "Order", back_populates="exchange_account", cascade="all, delete-orphan"
    )

    positions: Mapped[List["Position"]] = relationship(
        "Position", back_populates="exchange_account", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        """Initialize ExchangeAccount with default values"""
        # Set defaults
        kwargs.setdefault("environment", ExchangeEnvironment.TESTNET)
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("is_default", False)
        kwargs.setdefault("health_status", "unknown")
        kwargs.setdefault("total_orders", 0)
        kwargs.setdefault("successful_orders", 0)
        kwargs.setdefault("failed_orders", 0)
        kwargs.setdefault("rate_limit_window", 60)
        kwargs.setdefault("rate_limit_requests", 1200)
        super().__init__(**kwargs)

    def activate(self) -> None:
        """Activate exchange account"""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate exchange account"""
        self.is_active = False

    def set_as_default(self) -> None:
        """Mark as default account for this exchange"""
        self.is_default = True

    def unset_as_default(self) -> None:
        """Unmark as default account"""
        self.is_default = False

    def update_health_status(self, status: str, error: Optional[str] = None) -> None:
        """Update account health status"""
        self.health_status = status
        self.last_health_check = datetime.now()
        if error:
            self.last_error = error

    def increment_order_stats(self, success: bool) -> None:
        """Update order statistics"""
        self.total_orders += 1
        if success:
            self.successful_orders += 1
            self.last_trade_at = datetime.now()
        else:
            self.failed_orders += 1

    def get_success_rate(self) -> float:
        """Calculate order success rate"""
        if self.total_orders == 0:
            return 0.0
        return (self.successful_orders / self.total_orders) * 100

    def is_healthy(self) -> bool:
        """Check if account is healthy"""
        return self.is_active and self.health_status in ["healthy", "warning"]

    def can_trade(self) -> bool:
        """Check if account can execute trades"""
        return self.is_active and self.health_status == "healthy"
