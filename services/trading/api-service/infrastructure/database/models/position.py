"""Position model for tracking trading positions"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, NUMERIC

from .base import Base


class PositionSide(str, Enum):
    """Position side enumeration"""

    LONG = "long"
    SHORT = "short"


class PositionStatus(str, Enum):
    """Position status enumeration"""

    OPEN = "open"  # Active position
    CLOSED = "closed"  # Fully closed position
    CLOSING = "closing"  # In process of closing
    LIQUIDATED = "liquidated"  # Force liquidated by exchange


class Position(Base):
    """Position model for tracking trading positions"""

    __tablename__ = "positions"

    # Position identification
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255), index=True, comment="Exchange-provided position ID"
    )

    # Basic position info
    symbol: Mapped[str] = mapped_column(
        String(50), index=True, comment="Trading symbol (e.g., BTCUSDT)"
    )

    side: Mapped[PositionSide] = mapped_column(
        SQLEnum(PositionSide), comment="Position side (long/short)"
    )

    status: Mapped[PositionStatus] = mapped_column(
        SQLEnum(PositionStatus),
        default=PositionStatus.OPEN,
        index=True,
        comment="Current position status",
    )

    # Size and pricing
    size: Mapped[Decimal] = mapped_column(
        NUMERIC(precision=20, scale=8), comment="Position size (absolute value)"
    )

    entry_price: Mapped[Decimal] = mapped_column(
        NUMERIC(precision=20, scale=8), comment="Average entry price"
    )

    mark_price: Mapped[Optional[Decimal]] = mapped_column(
        NUMERIC(precision=20, scale=8), comment="Current mark price"
    )

    # PnL tracking
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        NUMERIC(precision=20, scale=8),
        default=Decimal("0"),
        comment="Current unrealized PnL",
    )

    realized_pnl: Mapped[Decimal] = mapped_column(
        NUMERIC(precision=20, scale=8),
        default=Decimal("0"),
        comment="Realized PnL from partial closes",
    )

    # Margin and leverage
    initial_margin: Mapped[Decimal] = mapped_column(
        NUMERIC(precision=20, scale=8), comment="Initial margin required"
    )

    maintenance_margin: Mapped[Decimal] = mapped_column(
        NUMERIC(precision=20, scale=8), comment="Maintenance margin required"
    )

    leverage: Mapped[Decimal] = mapped_column(
        NUMERIC(precision=5, scale=2), comment="Position leverage"
    )

    # Risk management
    liquidation_price: Mapped[Optional[Decimal]] = mapped_column(
        NUMERIC(precision=20, scale=8), comment="Estimated liquidation price"
    )

    bankruptcy_price: Mapped[Optional[Decimal]] = mapped_column(
        NUMERIC(precision=20, scale=8), comment="Bankruptcy price"
    )

    # Timestamps
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now,
        comment="Position opening timestamp",
    )

    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Position closing timestamp"
    )

    last_update_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now,
        comment="Last position update timestamp",
    )

    # Fee tracking
    total_fees: Mapped[Decimal] = mapped_column(
        NUMERIC(precision=20, scale=8),
        default=Decimal("0"),
        comment="Total fees paid for this position",
    )

    funding_fees: Mapped[Decimal] = mapped_column(
        NUMERIC(precision=20, scale=8),
        default=Decimal("0"),
        comment="Total funding fees paid/received",
    )

    # Exchange metadata
    exchange_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, comment="Raw exchange position data"
    )

    # Relationships
    exchange_account_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("exchange_accounts.id", ondelete="CASCADE"),
        comment="Exchange account holding this position",
    )

    exchange_account: Mapped["ExchangeAccount"] = relationship(
        "ExchangeAccount", back_populates="positions"
    )

    def __init__(self, **kwargs):
        """Initialize Position with default values"""
        from decimal import Decimal

        # Set defaults
        kwargs.setdefault("status", PositionStatus.OPEN)
        kwargs.setdefault("unrealized_pnl", Decimal("0"))
        kwargs.setdefault("realized_pnl", Decimal("0"))
        kwargs.setdefault("total_fees", Decimal("0"))
        kwargs.setdefault("funding_fees", Decimal("0"))
        if "opened_at" not in kwargs:
            kwargs["opened_at"] = datetime.now()
        if "last_update_at" not in kwargs:
            kwargs["last_update_at"] = datetime.now()
        super().__init__(**kwargs)

    # Business methods
    def update_size(self, new_size: Decimal, avg_price: Decimal) -> None:
        """Update position size and entry price"""
        if new_size == 0:
            self.close()
            return

        # Calculate new average entry price
        if self.size == 0:
            # New position
            self.entry_price = avg_price
        else:
            # Update existing position
            total_cost = (self.size * self.entry_price) + (
                abs(new_size - self.size) * avg_price
            )
            self.entry_price = total_cost / new_size

        self.size = new_size
        self.last_update_at = datetime.now()

    def update_pnl(
        self, unrealized: Decimal, realized: Optional[Decimal] = None
    ) -> None:
        """Update PnL values"""
        self.unrealized_pnl = unrealized
        if realized is not None:
            self.realized_pnl += realized
        self.last_update_at = datetime.now()

    def update_margin(self, initial: Decimal, maintenance: Decimal) -> None:
        """Update margin requirements"""
        self.initial_margin = initial
        self.maintenance_margin = maintenance
        self.last_update_at = datetime.now()

    def update_liquidation_price(self, liquidation: Decimal) -> None:
        """Update liquidation price"""
        self.liquidation_price = liquidation
        self.last_update_at = datetime.now()

    def update_mark_price(self, mark_price: Decimal) -> None:
        """Update mark price and recalculate unrealized PnL"""
        self.mark_price = mark_price

        # Calculate unrealized PnL
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (mark_price - self.entry_price) * self.size
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - mark_price) * self.size

        self.last_update_at = datetime.now()

    def add_fee(self, fee: Decimal, fee_type: str = "trading") -> None:
        """Add fee to position"""
        self.total_fees += fee
        if fee_type == "funding":
            self.funding_fees += fee
        self.last_update_at = datetime.now()

    def close(self, final_pnl: Optional[Decimal] = None) -> None:
        """Close position"""
        self.status = PositionStatus.CLOSED
        self.closed_at = datetime.now()
        self.last_update_at = datetime.now()

        if final_pnl is not None:
            self.realized_pnl += final_pnl
            self.unrealized_pnl = Decimal("0")

    def mark_closing(self) -> None:
        """Mark position as closing"""
        self.status = PositionStatus.CLOSING
        self.last_update_at = datetime.now()

    def liquidate(self, liquidation_price: Decimal) -> None:
        """Mark position as liquidated"""
        self.status = PositionStatus.LIQUIDATED
        self.closed_at = datetime.now()
        self.last_update_at = datetime.now()

        # Calculate final PnL at liquidation price
        if self.side == PositionSide.LONG:
            liquidation_pnl = (liquidation_price - self.entry_price) * self.size
        else:  # SHORT
            liquidation_pnl = (self.entry_price - liquidation_price) * self.size

        self.realized_pnl += liquidation_pnl
        self.unrealized_pnl = Decimal("0")

    def get_total_pnl(self) -> Decimal:
        """Get total PnL (realized + unrealized)"""
        return self.realized_pnl + self.unrealized_pnl

    def get_pnl_percentage(self) -> float:
        """Get PnL as percentage of initial investment"""
        if self.initial_margin == 0:
            return 0.0
        return float((self.get_total_pnl() / self.initial_margin) * 100)

    def get_roe(self) -> float:
        """Get Return on Equity (ROE) percentage"""
        if self.initial_margin == 0:
            return 0.0
        return float((self.get_total_pnl() / self.initial_margin) * 100)

    def is_profitable(self) -> bool:
        """Check if position is currently profitable"""
        return self.get_total_pnl() > 0

    def is_at_risk(self, threshold_percentage: float = 80.0) -> bool:
        """Check if position is at risk of liquidation"""
        if self.liquidation_price is None or self.mark_price is None:
            return False

        if self.side == PositionSide.LONG:
            risk_percentage = (
                (self.entry_price - self.mark_price)
                / (self.entry_price - self.liquidation_price)
            ) * 100
        else:  # SHORT
            risk_percentage = (
                (self.mark_price - self.entry_price)
                / (self.liquidation_price - self.entry_price)
            ) * 100

        return risk_percentage >= threshold_percentage

    def is_open(self) -> bool:
        """Check if position is open"""
        return self.status in [PositionStatus.OPEN, PositionStatus.CLOSING]

    def is_closed(self) -> bool:
        """Check if position is closed"""
        return self.status in [PositionStatus.CLOSED, PositionStatus.LIQUIDATED]
