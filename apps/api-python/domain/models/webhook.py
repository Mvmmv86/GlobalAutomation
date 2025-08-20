"""TradingView Webhook domain model"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class ActionType(str, Enum):
    """Trading actions from TradingView"""

    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"
    CANCEL = "cancel"


class OrderType(str, Enum):
    """Order types supported"""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class TradingViewWebhook:
    """TradingView webhook payload"""

    alert_id: str
    strategy: str
    action: ActionType
    symbol: str
    quantity: float
    exchange: str
    timestamp: datetime

    # Optional fields
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    order_type: OrderType = OrderType.MARKET
    account_id: Optional[str] = None
    leverage: Optional[float] = None
    reduce_only: bool = False

    def __post_init__(self):
        """Validate webhook data"""
        if not self.alert_id or len(self.alert_id.strip()) == 0:
            raise ValueError("Alert ID is required")

        if not self.strategy or len(self.strategy.strip()) == 0:
            raise ValueError("Strategy name is required")

        if not self.symbol or len(self.symbol.strip()) == 0:
            raise ValueError("Symbol is required")

        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")

        if self.leverage is not None and self.leverage <= 0:
            raise ValueError("Leverage must be positive")

        if self.price is not None and self.price <= 0:
            raise ValueError("Price must be positive")

        # Validate limit orders have price
        if (
            self.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]
            and self.price is None
        ):
            raise ValueError(f"{self.order_type} orders require a price")

    def is_market_order(self) -> bool:
        """Check if this is a market order"""
        return self.order_type == OrderType.MARKET

    def is_limit_order(self) -> bool:
        """Check if this is a limit order"""
        return self.order_type == OrderType.LIMIT

    def has_stop_loss(self) -> bool:
        """Check if stop loss is set"""
        return self.stop_loss is not None and self.stop_loss > 0

    def has_take_profit(self) -> bool:
        """Check if take profit is set"""
        return self.take_profit is not None and self.take_profit > 0

    def requires_margin(self) -> bool:
        """Check if order requires margin calculation"""
        return self.leverage is not None and self.leverage > 1


@dataclass
class WebhookJob:
    """Job entity for processing webhooks"""

    id: UUID
    alert_id: str
    account_id: UUID
    user_id: UUID
    webhook: TradingViewWebhook
    status: str  # pending, processing, completed, failed
    retry_count: int
    last_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate job data"""
        if self.retry_count < 0:
            raise ValueError("Retry count cannot be negative")

    def mark_processing(self) -> None:
        """Mark job as processing"""
        self.status = "processing"
        self.updated_at = datetime.utcnow()

    def mark_completed(self) -> None:
        """Mark job as completed"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error_message: str) -> None:
        """Mark job as failed with error"""
        self.status = "failed"
        self.last_error = error_message
        self.retry_count += 1
        self.updated_at = datetime.utcnow()

    def can_retry(self, max_retries: int = 3) -> bool:
        """Check if job can be retried"""
        return self.retry_count < max_retries and self.status == "failed"
