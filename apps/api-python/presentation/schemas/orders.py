"""
Order schemas for request/response validation
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class UpdateSLTPRequest(BaseModel):
    """Request schema for updating SL/TP orders"""

    exchange_account_id: str = Field(..., description="Exchange account ID")
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    position_side: Literal["LONG", "SHORT"] = Field(..., description="Position side")
    order_type: Literal["STOP_LOSS", "TAKE_PROFIT"] = Field(..., description="Order type to update")
    new_price: float = Field(..., gt=0, description="New price for the order")
    old_order_id: Optional[str] = Field(None, description="Existing order ID to cancel")
    quantity: float = Field(..., gt=0, description="Position quantity")

    @validator('new_price')
    def validate_price(cls, v):
        """Ensure price has reasonable precision"""
        # Convert to string to check decimal places
        price_str = str(v)
        if '.' in price_str:
            decimal_places = len(price_str.split('.')[1])
            if decimal_places > 8:  # Max 8 decimal places
                raise ValueError(f"Price has too many decimal places: {decimal_places}")
        return v

    @validator('symbol')
    def validate_symbol(cls, v):
        """Ensure symbol is uppercase"""
        return v.upper()


class UpdateSLTPResponse(BaseModel):
    """Response schema for SL/TP update operation"""

    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Stop loss updated successfully",
                "data": {
                    "cancelled_order_id": "123456",
                    "new_order_id": "789012",
                    "symbol": "BTCUSDT",
                    "order_type": "STOP_LOSS",
                    "new_price": 65000.0
                }
            }
        }


class OrderData(BaseModel):
    """Order data model"""

    id: Optional[str] = None
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: str
    exchange: str
    exchange_order_id: Optional[str] = None
    operation_type: str
    source: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTCUSDT",
                "side": "SELL",
                "order_type": "STOP_MARKET",
                "quantity": 0.001,
                "stop_price": 65000,
                "status": "pending",
                "exchange": "bingx",
                "exchange_order_id": "1234567890",
                "operation_type": "futures",
                "source": "EXCHANGE_API"
            }
        }