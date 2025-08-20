"""Webhook API schemas - Pydantic models for requests/responses"""

from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field, validator


class WebhookPayload(BaseModel):
    """TradingView webhook payload schema"""

    alert_id: str = Field(..., min_length=1, max_length=255)
    strategy: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., pattern="^(buy|sell|close|cancel)$")
    symbol: str = Field(..., min_length=1, max_length=20)
    quantity: float = Field(..., gt=0)
    exchange: str = Field(..., min_length=1, max_length=50)
    timestamp: str

    # Optional fields
    price: Optional[float] = Field(None, gt=0)
    order_type: str = Field(
        default="market", pattern="^(market|limit|stop|stop_limit)$"
    )
    stop_loss: Optional[float] = Field(None, gt=0)
    take_profit: Optional[float] = Field(None, gt=0)
    account_id: Optional[str] = None
    leverage: Optional[float] = Field(None, gt=0)
    reduce_only: bool = False

    @validator("quantity")
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @validator("price")
    def validate_price(cls, v, values):
        if v is not None and v <= 0:
            raise ValueError("Price must be positive")

        # Validate limit orders have price
        order_type = values.get("order_type", "market")
        if order_type in ["limit", "stop_limit"] and v is None:
            raise ValueError(f"{order_type} orders require a price")

        return v

    @validator("leverage")
    def validate_leverage(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Leverage must be positive")
        return v


class AccountInfo(BaseModel):
    """Selected account information"""

    id: str
    name: str
    selection_reason: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook processing response"""

    message: str
    job_id: str
    alert_id: str
    selected_account: Optional[AccountInfo] = None


class JobStatusResponse(BaseModel):
    """Job status response"""

    job_id: str
    alert_id: str
    status: str
    retry_count: int
    last_error: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema"""

    error: str
    detail: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str
    environment: str
    services: Dict[str, str] = Field(default_factory=dict)
