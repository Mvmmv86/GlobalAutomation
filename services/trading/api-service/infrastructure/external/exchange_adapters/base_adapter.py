"""Base exchange adapter interface"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class OrderResponse:
    """Exchange order response"""

    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal]
    status: OrderStatus
    filled_quantity: Decimal = Decimal("0")
    average_price: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    fees: Optional[Dict[str, Decimal]] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class Balance:
    """Account balance"""

    asset: str
    free: Decimal
    locked: Decimal
    total: Decimal


@dataclass
class Position:
    """Trading position"""

    symbol: str
    side: str  # 'long' or 'short'
    size: Decimal
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    percentage: Decimal


@dataclass
class ExchangeInfo:
    """Exchange symbol information"""

    symbol: str
    base_asset: str
    quote_asset: str
    min_quantity: Decimal
    max_quantity: Decimal
    quantity_step: Decimal
    min_price: Decimal
    max_price: Decimal
    price_step: Decimal
    min_notional: Decimal


class ExchangeError(Exception):
    """Base exchange error"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        raw_error: Optional[Dict] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.raw_error = raw_error


class BaseExchangeAdapter(ABC):
    """Base class for exchange adapters"""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self._exchange_info: Dict[str, ExchangeInfo] = {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Exchange name"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test API connection"""
        pass

    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        pass

    @abstractmethod
    async def get_balances(self) -> List[Balance]:
        """Get account balances"""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get open positions"""
        pass

    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
        client_order_id: Optional[str] = None,
    ) -> OrderResponse:
        """Create a new order"""
        pass

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order"""
        pass

    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> OrderResponse:
        """Get order status"""
        pass

    @abstractmethod
    async def get_open_orders(
        self, symbol: Optional[str] = None
    ) -> List[OrderResponse]:
        """Get open orders"""
        pass

    @abstractmethod
    async def get_exchange_info(
        self, symbol: Optional[str] = None
    ) -> Dict[str, ExchangeInfo]:
        """Get exchange trading rules"""
        pass

    @abstractmethod
    async def get_ticker_price(self, symbol: str) -> Decimal:
        """Get current price for symbol"""
        pass

    async def validate_order_params(
        self, symbol: str, quantity: Decimal, price: Optional[Decimal] = None
    ) -> bool:
        """Validate order parameters against exchange rules"""
        if symbol not in self._exchange_info:
            self._exchange_info.update(await self.get_exchange_info(symbol))

        info = self._exchange_info.get(symbol)
        if not info:
            raise ExchangeError(f"Symbol {symbol} not found")

        # Validate quantity
        if quantity < info.min_quantity or quantity > info.max_quantity:
            raise ExchangeError(
                f"Quantity {quantity} outside valid range [{info.min_quantity}, {info.max_quantity}]"
            )

        # Validate price if provided
        if price is not None:
            if price < info.min_price or price > info.max_price:
                raise ExchangeError(
                    f"Price {price} outside valid range [{info.min_price}, {info.max_price}]"
                )

        # Validate notional value
        current_price = price or await self.get_ticker_price(symbol)
        notional = quantity * current_price
        if notional < info.min_notional:
            raise ExchangeError(
                f"Notional value {notional} below minimum {info.min_notional}"
            )

        return True

    def format_quantity(self, symbol: str, quantity: Decimal) -> Decimal:
        """Format quantity according to exchange rules"""
        if symbol not in self._exchange_info:
            return quantity

        info = self._exchange_info[symbol]
        # Round to step size
        return Decimal(
            str(
                float(quantity) // float(info.quantity_step) * float(info.quantity_step)
            )
        )

    def format_price(self, symbol: str, price: Decimal) -> Decimal:
        """Format price according to exchange rules"""
        if symbol not in self._exchange_info:
            return price

        info = self._exchange_info[symbol]
        # Round to step size
        return Decimal(
            str(float(price) // float(info.price_step) * float(info.price_step))
        )
