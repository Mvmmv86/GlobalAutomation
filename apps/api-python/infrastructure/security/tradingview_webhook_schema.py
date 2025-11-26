"""TradingView Webhook Payload Validation with Pydantic"""

from typing import Optional, Literal
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator
import structlog

logger = structlog.get_logger(__name__)


class TradingViewWebhookPayload(BaseModel):
    """
    Pydantic model for TradingView webhook payload validation.

    Standard TradingView alert message format:
    {
        "action": "buy" | "sell" | "close",
        "symbol": "BTCUSDT",
        "price": 50000.00,
        "quantity": 0.001,
        "timestamp": 1234567890,
        "strategy": "My Strategy Name",
        "order_type": "market" | "limit",
        "stop_loss": 49000.00,  // optional
        "take_profit": 51000.00,  // optional
        "leverage": 10,  // optional
        "position_side": "LONG" | "SHORT",  // optional for futures
        "nonce": "unique-request-id",  // for replay attack prevention
        "passphrase": "secret-key"  // optional authentication
    }
    """

    # Required fields
    action: Literal["buy", "sell", "close", "close_long", "close_short"]
    symbol: str = Field(..., min_length=3, max_length=20)

    # Trading parameters
    price: Optional[Decimal] = Field(None, gt=0)
    quantity: Optional[Decimal] = Field(None, gt=0)
    order_type: Literal["market", "limit", "stop_market", "stop_limit"] = "market"

    # Risk management
    stop_loss: Optional[Decimal] = Field(None, gt=0)
    take_profit: Optional[Decimal] = Field(None, gt=0)
    leverage: Optional[int] = Field(None, ge=1, le=125)

    # Futures-specific
    position_side: Optional[Literal["LONG", "SHORT", "BOTH"]] = None

    # Metadata
    timestamp: int = Field(..., description="Unix timestamp")
    strategy: Optional[str] = Field(None, max_length=100)
    nonce: str = Field(..., min_length=16, max_length=128)

    # Authentication
    passphrase: Optional[str] = Field(None, min_length=8, max_length=256)

    # Additional fields
    timeframe: Optional[str] = Field(None, max_length=10)  # e.g., "1h", "4h"
    exchange: Optional[str] = Field(None, max_length=50)
    account: Optional[str] = Field(None, max_length=100)

    class Config:
        """Pydantic config"""
        json_encoders = {
            Decimal: lambda v: float(v)
        }

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        """Validate symbol format"""
        # Remove common separators
        v = v.upper().replace('/', '').replace('-', '').replace('_', '')

        # Check if it's a valid symbol (alphanumeric)
        if not v.isalnum():
            raise ValueError(f"Invalid symbol format: {v}")

        return v

    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        """Validate and normalize action"""
        v = v.lower()
        valid_actions = ["buy", "sell", "close", "close_long", "close_short"]

        if v not in valid_actions:
            raise ValueError(f"Invalid action: {v}. Must be one of {valid_actions}")

        return v

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        """Validate timestamp is not too old or in the future"""
        import time
        now = int(time.time())
        max_drift = 300  # 5 minutes

        time_diff = abs(now - v)
        if time_diff > max_drift:
            raise ValueError(
                f"Timestamp drift too large: {time_diff}s (max: {max_drift}s)"
            )

        return v

    @field_validator('leverage')
    @classmethod
    def validate_leverage(cls, v):
        """Validate leverage is reasonable"""
        if v is not None:
            if v < 1:
                raise ValueError("Leverage must be at least 1x")
            if v > 125:
                raise ValueError("Leverage cannot exceed 125x")
        return v

    @model_validator(mode='after')
    def validate_order_consistency(self):
        """Validate order parameters are consistent"""
        # Limit orders require price
        if self.order_type == 'limit' and self.price is None:
            raise ValueError("Limit orders require a price")

        # Buy/Sell orders require quantity
        if self.action in ['buy', 'sell'] and self.quantity is None:
            raise ValueError(f"Action '{self.action}' requires quantity")

        # Stop loss must be below entry for long, above for short
        if self.stop_loss and self.take_profit:
            if self.action == 'buy' or self.position_side == 'LONG':
                if self.stop_loss >= self.take_profit:
                    raise ValueError(
                        "For LONG positions: stop_loss must be < take_profit"
                    )
            elif self.action == 'sell' or self.position_side == 'SHORT':
                if self.stop_loss <= self.take_profit:
                    raise ValueError(
                        "For SHORT positions: stop_loss must be > take_profit"
                    )

        return self

    @model_validator(mode='after')
    def validate_futures_fields(self):
        """Validate futures-specific fields"""
        # If leverage is specified, position_side should be too (for futures)
        if self.leverage and self.leverage > 1 and not self.position_side:
            logger.warning(
                "Leverage specified without position_side, defaulting to BOTH",
                leverage=self.leverage
            )
            self.position_side = 'BOTH'

        return self

    def to_order_params(self) -> dict:
        """
        Convert webhook payload to exchange order parameters.

        Returns:
            Dictionary with standardized order parameters
        """
        params = {
            'symbol': self.symbol,
            'action': self.action,
            'order_type': self.order_type,
            'quantity': float(self.quantity) if self.quantity else None,
            'price': float(self.price) if self.price else None,
        }

        # Add optional parameters
        if self.stop_loss:
            params['stop_loss'] = float(self.stop_loss)
        if self.take_profit:
            params['take_profit'] = float(self.take_profit)
        if self.leverage:
            params['leverage'] = self.leverage
        if self.position_side:
            params['position_side'] = self.position_side
        if self.strategy:
            params['strategy'] = self.strategy

        return params


class WebhookAuthPayload(BaseModel):
    """
    Authentication payload for webhook requests.

    Used to validate webhook authenticity.
    """
    webhook_id: str = Field(..., min_length=1)
    timestamp: int
    nonce: str = Field(..., min_length=16)
    signature: Optional[str] = Field(None, min_length=64)

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        """Validate timestamp"""
        import time
        now = int(time.time())
        max_drift = 300  # 5 minutes

        if abs(now - v) > max_drift:
            raise ValueError("Timestamp drift too large")

        return v


class WebhookResponse(BaseModel):
    """Standard webhook response"""
    success: bool
    message: str
    order_id: Optional[str] = None
    execution_time: Optional[float] = None
    warnings: Optional[list] = None

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
