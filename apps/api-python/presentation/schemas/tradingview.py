"""TradingView webhook schemas"""

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from decimal import Decimal
from datetime import datetime


class TradingViewWebhookBase(BaseModel):
    """Base TradingView webhook schema"""

    # TradingView standard fields
    ticker: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    action: Literal["buy", "sell", "close"] = Field(..., description="Trading action")

    # Optional standard fields
    exchange: Optional[str] = Field(None, description="Exchange name")
    time: Optional[str] = Field(None, description="Timestamp from TradingView")

    # Alert identification
    strategy: Optional[str] = Field(None, description="Strategy name")
    alert_name: Optional[str] = Field(None, description="Alert name")

    @validator("ticker")
    def validate_ticker(cls, v):
        """Validate ticker format"""
        if not v or not v.strip():
            raise ValueError("Ticker cannot be empty")
        return v.upper().strip()

    @validator("action")
    def validate_action(cls, v):
        """Validate action"""
        if v not in ["buy", "sell", "close"]:
            raise ValueError("Action must be buy, sell, or close")
        return v.lower()


class TradingViewOrderWebhook(TradingViewWebhookBase):
    """TradingView webhook for order placement"""

    # Order parameters
    quantity: Optional[Decimal] = Field(None, gt=0, description="Order quantity")
    price: Optional[Decimal] = Field(
        None, gt=0, description="Order price (for limit orders)"
    )

    # Order type
    order_type: Optional[Literal["market", "limit", "stop", "stop_limit"]] = Field(
        "market", description="Order type"
    )

    # Risk management
    stop_loss: Optional[Decimal] = Field(None, gt=0, description="Stop loss price")
    take_profit: Optional[Decimal] = Field(None, gt=0, description="Take profit price")

    # Position sizing
    percent: Optional[float] = Field(
        None, ge=0, le=100, description="Percentage of balance to use"
    )
    leverage: Optional[int] = Field(
        None, ge=1, le=125, description="Leverage multiplier"
    )

    @validator("order_type")
    def validate_order_type(cls, v):
        """Validate order type"""
        if v not in ["market", "limit", "stop", "stop_limit"]:
            raise ValueError("Invalid order type")
        return v.lower()

    @validator("price")
    def validate_price_for_limit(cls, v, values):
        """Validate price for limit orders"""
        if values.get("order_type") == "limit" and not v:
            raise ValueError("Price required for limit orders")
        return v


class TradingViewPositionWebhook(TradingViewWebhookBase):
    """TradingView webhook for position management"""

    # Position parameters
    size: Optional[Decimal] = Field(None, description="Position size")
    entry_price: Optional[Decimal] = Field(None, gt=0, description="Entry price")
    current_price: Optional[Decimal] = Field(
        None, gt=0, description="Current market price"
    )

    # P&L information
    pnl: Optional[Decimal] = Field(None, description="Unrealized P&L")
    pnl_percent: Optional[float] = Field(None, description="P&L percentage")

    # Risk levels
    risk_level: Optional[Literal["low", "medium", "high"]] = Field(
        None, description="Risk assessment"
    )


class TradingViewSignalWebhook(TradingViewWebhookBase):
    """TradingView webhook for trading signals"""

    # Signal strength
    signal_strength: Optional[Literal["weak", "medium", "strong"]] = Field(
        None, description="Signal strength"
    )

    # Technical indicators
    rsi: Optional[float] = Field(None, ge=0, le=100, description="RSI value")
    macd: Optional[float] = Field(None, description="MACD value")
    volume: Optional[Decimal] = Field(None, gt=0, description="Volume")

    # Market conditions
    trend: Optional[Literal["bullish", "bearish", "sideways"]] = Field(
        None, description="Market trend"
    )

    # Custom indicators
    custom_data: Optional[Dict[str, Any]] = Field(
        None, description="Custom indicator data"
    )


class WebhookProcessingRequest(BaseModel):
    """Webhook processing request"""

    webhook_id: str = Field(..., description="Webhook ID")
    payload: Dict[str, Any] = Field(..., description="Raw webhook payload")
    headers: Dict[str, str] = Field(..., description="Request headers")
    signature: Optional[str] = Field(None, description="HMAC signature")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Processing timestamp"
    )


class WebhookProcessingResponse(BaseModel):
    """Webhook processing response"""

    success: bool = Field(..., description="Processing success")
    message: str = Field(..., description="Processing message")

    # Processing details
    delivery_id: str = Field(..., description="Delivery record ID")
    webhook_id: str = Field(..., description="Webhook ID")

    # Execution results
    orders_created: int = Field(0, description="Number of orders created")
    orders_executed: int = Field(0, description="Number of orders executed")
    orders_failed: int = Field(0, description="Number of orders failed")

    # Processing metrics
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")

    # Error details (if any)
    errors: Optional[list[str]] = Field(None, description="Processing errors")
    warnings: Optional[list[str]] = Field(None, description="Processing warnings")


class WebhookValidationError(BaseModel):
    """Webhook validation error"""

    error_type: Literal["signature", "payload", "format", "business"] = Field(
        ..., description="Error type"
    )
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    code: Optional[str] = Field(None, description="Error code")


class WebhookDeliveryStatus(BaseModel):
    """Webhook delivery status response"""

    delivery_id: str = Field(..., description="Delivery ID")
    webhook_id: str = Field(..., description="Webhook ID")
    status: Literal["pending", "processing", "success", "failed", "retrying"] = Field(
        ..., description="Delivery status"
    )

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    # Retry information
    retry_count: int = Field(0, description="Number of retry attempts")
    next_retry_at: Optional[datetime] = Field(None, description="Next retry timestamp")

    # Processing results
    orders_created: int = Field(0, description="Orders created")
    orders_executed: int = Field(0, description="Orders executed")
    orders_failed: int = Field(0, description="Orders failed")

    # Error information
    error_message: Optional[str] = Field(None, description="Error message")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Error details")


class WebhookStatsResponse(BaseModel):
    """Webhook statistics response"""

    webhook_id: str = Field(..., description="Webhook ID")

    # Delivery statistics
    total_deliveries: int = Field(0, description="Total deliveries")
    successful_deliveries: int = Field(0, description="Successful deliveries")
    failed_deliveries: int = Field(0, description="Failed deliveries")

    # Success rate
    success_rate: float = Field(
        0.0, ge=0, le=100, description="Success rate percentage"
    )

    # Performance metrics
    average_processing_time_ms: float = Field(
        0.0, description="Average processing time"
    )

    # Trading statistics
    total_orders_created: int = Field(0, description="Total orders created")
    total_orders_executed: int = Field(0, description="Total orders executed")

    # Time range
    period_days: int = Field(30, description="Statistics period in days")
