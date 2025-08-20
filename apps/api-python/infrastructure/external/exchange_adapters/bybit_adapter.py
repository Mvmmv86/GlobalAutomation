"""Bybit exchange adapter"""

import hmac
import hashlib
import time
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import aiohttp
import json

from .base_adapter import (
    BaseExchangeAdapter,
    OrderResponse,
    Balance,
    Position,
    ExchangeInfo,
    OrderType,
    OrderSide,
    OrderStatus,
    ExchangeError,
)


class BybitAdapter(BaseExchangeAdapter):
    """Bybit exchange adapter"""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        super().__init__(api_key, api_secret, testnet)
        self.base_url = (
            "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
        )
        self.session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "bybit"

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

    def _sign_request(self, params: Dict[str, Any], timestamp: int) -> str:
        """Sign request with API secret"""
        param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        sign_str = f"{timestamp}{self.api_key}{param_str}"
        signature = hmac.new(
            self.api_secret.encode("utf-8"), sign_str.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return signature

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """Make HTTP request to Bybit API"""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        if params is None:
            params = {}

        headers = {"Content-Type": "application/json"}

        if signed:
            timestamp = int(time.time() * 1000)
            headers["X-BAPI-API-KEY"] = self.api_key
            headers["X-BAPI-TIMESTAMP"] = str(timestamp)
            headers["X-BAPI-SIGN"] = self._sign_request(params, timestamp)

        try:
            if method == "GET":
                async with session.get(url, params=params, headers=headers) as response:
                    data = await response.json()
            elif method == "POST":
                async with session.post(url, json=params, headers=headers) as response:
                    data = await response.json()
            elif method == "DELETE":
                async with session.delete(
                    url, json=params, headers=headers
                ) as response:
                    data = await response.json()
            else:
                raise ExchangeError(f"Unsupported HTTP method: {method}")

            if data.get("retCode") != 0:
                error_msg = data.get("retMsg", f"API error {data.get('retCode')}")
                error_code = str(data.get("retCode"))
                raise ExchangeError(error_msg, error_code, data)

            return data.get("result", {})

        except aiohttp.ClientError as e:
            raise ExchangeError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise ExchangeError(f"Invalid JSON response: {str(e)}")

    async def test_connection(self) -> bool:
        """Test API connection"""
        try:
            await self._make_request("GET", "/v5/market/time")
            return True
        except ExchangeError:
            return False

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        return await self._make_request("GET", "/v5/account/info", signed=True)

    async def get_balances(self) -> List[Balance]:
        """Get account balances"""
        params = {"accountType": "UNIFIED"}  # For unified trading account
        response = await self._make_request(
            "GET", "/v5/account/wallet-balance", params, signed=True
        )

        balances = []
        for account in response.get("list", []):
            for balance_data in account.get("coin", []):
                free = Decimal(balance_data.get("availableToWithdraw", "0"))
                locked = Decimal(balance_data.get("locked", "0"))

                if free > 0 or locked > 0:  # Only include non-zero balances
                    balances.append(
                        Balance(
                            asset=balance_data["coin"],
                            free=free,
                            locked=locked,
                            total=free + locked,
                        )
                    )

        return balances

    async def get_positions(self) -> List[Position]:
        """Get open positions"""
        params = {"category": "linear", "settleCoin": "USDT"}
        response = await self._make_request(
            "GET", "/v5/position/list", params, signed=True
        )

        positions = []
        for pos_data in response.get("list", []):
            size = Decimal(pos_data.get("size", "0"))
            if size > 0:  # Only include open positions
                positions.append(
                    Position(
                        symbol=pos_data["symbol"],
                        side=pos_data["side"].lower(),
                        size=size,
                        entry_price=Decimal(pos_data.get("avgPrice", "0")),
                        mark_price=Decimal(pos_data.get("markPrice", "0")),
                        unrealized_pnl=Decimal(pos_data.get("unrealisedPnl", "0")),
                        percentage=Decimal(pos_data.get("unrealisedPnl", "0"))
                        / Decimal(pos_data.get("positionValue", "1"))
                        * 100,
                    )
                )

        return positions

    def _map_order_status(self, bybit_status: str) -> OrderStatus:
        """Map Bybit order status to our OrderStatus"""
        status_map = {
            "New": OrderStatus.OPEN,
            "PartiallyFilled": OrderStatus.PARTIALLY_FILLED,
            "Filled": OrderStatus.FILLED,
            "Cancelled": OrderStatus.CANCELLED,
            "Rejected": OrderStatus.REJECTED,
            "Deactivated": OrderStatus.CANCELLED,
        }
        return status_map.get(bybit_status, OrderStatus.PENDING)

    def _map_order_type(self, order_type: OrderType) -> str:
        """Map our OrderType to Bybit order type"""
        type_map = {OrderType.MARKET: "Market", OrderType.LIMIT: "Limit"}
        return type_map.get(order_type, "Limit")

    def _map_order_side(self, side: OrderSide) -> str:
        """Map our OrderSide to Bybit side"""
        return side.value.capitalize()

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
        # Validate parameters first
        await self.validate_order_params(symbol, quantity, price)

        params = {
            "category": "spot",  # For spot trading
            "symbol": symbol,
            "side": self._map_order_side(side),
            "orderType": self._map_order_type(order_type),
            "qty": str(self.format_quantity(symbol, quantity)),
            "timeInForce": time_in_force,
        }

        if price is not None:
            params["price"] = str(self.format_price(symbol, price))

        if client_order_id:
            params["orderLinkId"] = client_order_id

        response = await self._make_request(
            "POST", "/v5/order/create", params, signed=True
        )

        return OrderResponse(
            order_id=response["orderId"],
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.PENDING,  # New orders start as pending
            created_at=datetime.now(),
            raw_response=response,
        )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order"""
        try:
            params = {"category": "spot", "symbol": symbol, "orderId": order_id}
            await self._make_request("POST", "/v5/order/cancel", params, signed=True)
            return True
        except ExchangeError:
            return False

    async def get_order(self, symbol: str, order_id: str) -> OrderResponse:
        """Get order status"""
        params = {"category": "spot", "symbol": symbol, "orderId": order_id}
        response = await self._make_request(
            "GET", "/v5/order/realtime", params, signed=True
        )

        order_list = response.get("list", [])
        if not order_list:
            raise ExchangeError(f"Order {order_id} not found")

        order_data = order_list[0]

        return OrderResponse(
            order_id=order_data["orderId"],
            symbol=order_data["symbol"],
            side=OrderSide(order_data["side"].lower()),
            order_type=OrderType.LIMIT
            if order_data["orderType"] == "Limit"
            else OrderType.MARKET,
            quantity=Decimal(order_data["qty"]),
            price=Decimal(order_data["price"]) if order_data.get("price") else None,
            status=self._map_order_status(order_data["orderStatus"]),
            filled_quantity=Decimal(order_data.get("cumExecQty", "0")),
            average_price=Decimal(order_data["avgPrice"])
            if order_data.get("avgPrice")
            else None,
            created_at=datetime.fromtimestamp(int(order_data["createdTime"]) / 1000),
            updated_at=datetime.fromtimestamp(int(order_data["updatedTime"]) / 1000),
            raw_response=order_data,
        )

    async def get_open_orders(
        self, symbol: Optional[str] = None
    ) -> List[OrderResponse]:
        """Get open orders"""
        params = {"category": "spot"}
        if symbol:
            params["symbol"] = symbol

        response = await self._make_request(
            "GET", "/v5/order/realtime", params, signed=True
        )
        orders = []

        for order_data in response.get("list", []):
            orders.append(
                OrderResponse(
                    order_id=order_data["orderId"],
                    symbol=order_data["symbol"],
                    side=OrderSide(order_data["side"].lower()),
                    order_type=OrderType.LIMIT
                    if order_data["orderType"] == "Limit"
                    else OrderType.MARKET,
                    quantity=Decimal(order_data["qty"]),
                    price=Decimal(order_data["price"])
                    if order_data.get("price")
                    else None,
                    status=self._map_order_status(order_data["orderStatus"]),
                    filled_quantity=Decimal(order_data.get("cumExecQty", "0")),
                    average_price=Decimal(order_data["avgPrice"])
                    if order_data.get("avgPrice")
                    else None,
                    created_at=datetime.fromtimestamp(
                        int(order_data["createdTime"]) / 1000
                    ),
                    updated_at=datetime.fromtimestamp(
                        int(order_data["updatedTime"]) / 1000
                    ),
                    raw_response=order_data,
                )
            )

        return orders

    async def get_exchange_info(
        self, symbol: Optional[str] = None
    ) -> Dict[str, ExchangeInfo]:
        """Get exchange trading rules"""
        params = {"category": "spot"}
        if symbol:
            params["symbol"] = symbol

        response = await self._make_request(
            "GET", "/v5/market/instruments-info", params
        )

        exchange_info = {}
        for symbol_data in response.get("list", []):
            # Parse lot size filter
            lot_filter = symbol_data.get("lotSizeFilter", {})
            min_qty = Decimal(lot_filter.get("minOrderQty", "0"))
            max_qty = Decimal(lot_filter.get("maxOrderQty", "999999999"))
            qty_step = Decimal(lot_filter.get("qtyStep", "0.00000001"))

            # Parse price filter
            price_filter = symbol_data.get("priceFilter", {})
            min_price = Decimal(price_filter.get("minPrice", "0"))
            max_price = Decimal(price_filter.get("maxPrice", "999999999"))
            price_step = Decimal(price_filter.get("tickSize", "0.00000001"))

            # Min notional - may not be available in symbol info
            min_notional = Decimal("10")  # Default minimum for most pairs

            exchange_info[symbol_data["symbol"]] = ExchangeInfo(
                symbol=symbol_data["symbol"],
                base_asset=symbol_data["baseCoin"],
                quote_asset=symbol_data["quoteCoin"],
                min_quantity=min_qty,
                max_quantity=max_qty,
                quantity_step=qty_step,
                min_price=min_price,
                max_price=max_price,
                price_step=price_step,
                min_notional=min_notional,
            )

        # Cache the results
        self._exchange_info.update(exchange_info)
        return exchange_info

    async def get_ticker_price(self, symbol: str) -> Decimal:
        """Get current price for symbol"""
        params = {"category": "spot", "symbol": symbol}
        response = await self._make_request("GET", "/v5/market/tickers", params)

        ticker_list = response.get("list", [])
        if not ticker_list:
            raise ExchangeError(f"No ticker data for symbol {symbol}")

        return Decimal(ticker_list[0]["lastPrice"])
