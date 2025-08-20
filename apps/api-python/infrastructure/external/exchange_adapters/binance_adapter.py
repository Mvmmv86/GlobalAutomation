"""Binance exchange adapter"""

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


class BinanceAdapter(BaseExchangeAdapter):
    """Binance exchange adapter"""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        super().__init__(api_key, api_secret, testnet)
        self.base_url = (
            "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        )
        self.session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "binance"

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

    def _sign_request(self, params: Dict[str, Any]) -> str:
        """Sign request with API secret"""
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """Make HTTP request to Binance API"""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"

        if params is None:
            params = {}

        headers = {"X-MBX-APIKEY": self.api_key}

        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._sign_request(params)

        try:
            if method == "GET":
                async with session.get(url, params=params, headers=headers) as response:
                    data = await response.json()
            elif method == "POST":
                async with session.post(url, data=params, headers=headers) as response:
                    data = await response.json()
            elif method == "DELETE":
                async with session.delete(
                    url, params=params, headers=headers
                ) as response:
                    data = await response.json()
            else:
                raise ExchangeError(f"Unsupported HTTP method: {method}")

            if response.status != 200:
                error_msg = data.get("msg", f"HTTP {response.status}")
                error_code = str(data.get("code", response.status))
                raise ExchangeError(error_msg, error_code, data)

            return data

        except aiohttp.ClientError as e:
            raise ExchangeError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            raise ExchangeError(f"Invalid JSON response: {str(e)}")

    async def test_connection(self) -> bool:
        """Test API connection"""
        try:
            await self._make_request("GET", "/api/v3/ping")
            return True
        except ExchangeError:
            return False

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        return await self._make_request("GET", "/api/v3/account", signed=True)

    async def get_balances(self) -> List[Balance]:
        """Get account balances"""
        account_info = await self.get_account_info()
        balances = []

        for balance_data in account_info.get("balances", []):
            free = Decimal(balance_data["free"])
            locked = Decimal(balance_data["locked"])

            if free > 0 or locked > 0:  # Only include non-zero balances
                balances.append(
                    Balance(
                        asset=balance_data["asset"],
                        free=free,
                        locked=locked,
                        total=free + locked,
                    )
                )

        return balances

    async def get_positions(self) -> List[Position]:
        """Get open positions (futures only)"""
        # For spot trading, positions don't exist
        # This would be implemented for futures trading
        return []

    def _map_order_status(self, binance_status: str) -> OrderStatus:
        """Map Binance order status to our OrderStatus"""
        status_map = {
            "NEW": OrderStatus.OPEN,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.CANCELLED,
        }
        return status_map.get(binance_status, OrderStatus.PENDING)

    def _map_order_type(self, order_type: OrderType) -> str:
        """Map our OrderType to Binance order type"""
        type_map = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.STOP: "STOP_LOSS",
            OrderType.STOP_LIMIT: "STOP_LOSS_LIMIT",
        }
        return type_map[order_type]

    def _map_order_side(self, side: OrderSide) -> str:
        """Map our OrderSide to Binance side"""
        return side.value.upper()

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
            "symbol": symbol,
            "side": self._map_order_side(side),
            "type": self._map_order_type(order_type),
            "quantity": str(self.format_quantity(symbol, quantity)),
            "timeInForce": time_in_force,
        }

        if price is not None:
            params["price"] = str(self.format_price(symbol, price))

        if stop_price is not None:
            params["stopPrice"] = str(self.format_price(symbol, stop_price))

        if client_order_id:
            params["newClientOrderId"] = client_order_id

        response = await self._make_request(
            "POST", "/api/v3/order", params, signed=True
        )

        return OrderResponse(
            order_id=str(response["orderId"]),
            symbol=response["symbol"],
            side=OrderSide(response["side"].lower()),
            order_type=order_type,
            quantity=Decimal(response["origQty"]),
            price=Decimal(response["price"]) if response.get("price") else None,
            status=self._map_order_status(response["status"]),
            filled_quantity=Decimal(response.get("executedQty", "0")),
            average_price=Decimal(response["cummulativeQuoteQty"])
            / Decimal(response["executedQty"])
            if Decimal(response.get("executedQty", "0")) > 0
            else None,
            created_at=datetime.fromtimestamp(response["transactTime"] / 1000),
            raw_response=response,
        )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order"""
        try:
            params = {"symbol": symbol, "orderId": order_id}
            await self._make_request("DELETE", "/api/v3/order", params, signed=True)
            return True
        except ExchangeError:
            return False

    async def get_order(self, symbol: str, order_id: str) -> OrderResponse:
        """Get order status"""
        params = {"symbol": symbol, "orderId": order_id}
        response = await self._make_request("GET", "/api/v3/order", params, signed=True)

        return OrderResponse(
            order_id=str(response["orderId"]),
            symbol=response["symbol"],
            side=OrderSide(response["side"].lower()),
            order_type=OrderType.LIMIT
            if response["type"] == "LIMIT"
            else OrderType.MARKET,
            quantity=Decimal(response["origQty"]),
            price=Decimal(response["price"]) if response.get("price") else None,
            status=self._map_order_status(response["status"]),
            filled_quantity=Decimal(response.get("executedQty", "0")),
            average_price=Decimal(response["cummulativeQuoteQty"])
            / Decimal(response["executedQty"])
            if Decimal(response.get("executedQty", "0")) > 0
            else None,
            created_at=datetime.fromtimestamp(response["time"] / 1000),
            updated_at=datetime.fromtimestamp(response["updateTime"] / 1000),
            raw_response=response,
        )

    async def get_open_orders(
        self, symbol: Optional[str] = None
    ) -> List[OrderResponse]:
        """Get open orders"""
        params = {}
        if symbol:
            params["symbol"] = symbol

        response = await self._make_request(
            "GET", "/api/v3/openOrders", params, signed=True
        )
        orders = []

        for order_data in response:
            orders.append(
                OrderResponse(
                    order_id=str(order_data["orderId"]),
                    symbol=order_data["symbol"],
                    side=OrderSide(order_data["side"].lower()),
                    order_type=OrderType.LIMIT
                    if order_data["type"] == "LIMIT"
                    else OrderType.MARKET,
                    quantity=Decimal(order_data["origQty"]),
                    price=Decimal(order_data["price"])
                    if order_data.get("price")
                    else None,
                    status=self._map_order_status(order_data["status"]),
                    filled_quantity=Decimal(order_data.get("executedQty", "0")),
                    created_at=datetime.fromtimestamp(order_data["time"] / 1000),
                    updated_at=datetime.fromtimestamp(order_data["updateTime"] / 1000),
                    raw_response=order_data,
                )
            )

        return orders

    async def get_exchange_info(
        self, symbol: Optional[str] = None
    ) -> Dict[str, ExchangeInfo]:
        """Get exchange trading rules"""
        response = await self._make_request("GET", "/api/v3/exchangeInfo")

        exchange_info = {}
        for symbol_data in response["symbols"]:
            if symbol and symbol_data["symbol"] != symbol:
                continue

            # Parse filters
            min_qty = Decimal("0")
            max_qty = Decimal("999999999")
            qty_step = Decimal("0.00000001")
            min_price = Decimal("0")
            max_price = Decimal("999999999")
            price_step = Decimal("0.00000001")
            min_notional = Decimal("0")

            for filter_data in symbol_data.get("filters", []):
                if filter_data["filterType"] == "LOT_SIZE":
                    min_qty = Decimal(filter_data["minQty"])
                    max_qty = Decimal(filter_data["maxQty"])
                    qty_step = Decimal(filter_data["stepSize"])
                elif filter_data["filterType"] == "PRICE_FILTER":
                    min_price = Decimal(filter_data["minPrice"])
                    max_price = Decimal(filter_data["maxPrice"])
                    price_step = Decimal(filter_data["tickSize"])
                elif filter_data["filterType"] == "MIN_NOTIONAL":
                    min_notional = Decimal(filter_data["minNotional"])

            exchange_info[symbol_data["symbol"]] = ExchangeInfo(
                symbol=symbol_data["symbol"],
                base_asset=symbol_data["baseAsset"],
                quote_asset=symbol_data["quoteAsset"],
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
        params = {"symbol": symbol}
        response = await self._make_request("GET", "/api/v3/ticker/price", params)
        return Decimal(response["price"])
