"""Tests for Bybit adapter"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal

from infrastructure.external.exchange_adapters.bybit_adapter import BybitAdapter
from infrastructure.external.exchange_adapters.base_adapter import (
    OrderSide,
    OrderType,
    OrderStatus,
    ExchangeError,
    ExchangeInfo,
)


class TestBybitAdapter:
    """Test cases for BybitAdapter"""

    @pytest.fixture
    def adapter(self):
        """BybitAdapter instance for testing"""
        return BybitAdapter(
            api_key="test_api_key", api_secret="test_api_secret", testnet=True
        )

    @pytest.fixture
    def mock_response(self):
        """Mock HTTP response"""
        response = MagicMock()
        response.status = 200
        response.json = AsyncMock()
        return response

    def test_adapter_properties(self, adapter):
        """Test adapter basic properties"""
        assert adapter.name == "bybit"
        assert adapter.testnet is True
        assert adapter.base_url == "https://api-testnet.bybit.com"

    def test_sign_request(self, adapter):
        """Test request signing"""
        params = {"symbol": "BTCUSDT", "side": "Buy"}
        timestamp = 1640995200000
        signature = adapter._sign_request(params, timestamp)

        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest length

    @pytest.mark.asyncio
    async def test_test_connection_success(self, adapter):
        """Test successful connection test"""
        with patch.object(
            adapter, "_make_request", return_value={"timeNow": "1640995200"}
        ):
            result = await adapter.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, adapter):
        """Test failed connection test"""
        with patch.object(
            adapter, "_make_request", side_effect=ExchangeError("Connection failed")
        ):
            result = await adapter.test_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_make_request_success(self, adapter):
        """Test successful HTTP request"""
        # Mock the actual _make_request method
        with patch.object(adapter, "_make_request", return_value={"status": "OK"}):
            result = await adapter._make_request("GET", "/v5/market/time")
            assert result == {"status": "OK"}

    @pytest.mark.asyncio
    async def test_make_request_error_response(self, adapter):
        """Test HTTP request with error response"""
        # Mock the actual _make_request method to raise an exception
        error = ExchangeError("Invalid API key", "10001")
        with patch.object(adapter, "_make_request", side_effect=error):
            with pytest.raises(ExchangeError) as exc_info:
                await adapter._make_request("GET", "/v5/account/info")

            assert "Invalid API key" in str(exc_info.value)
            assert exc_info.value.error_code == "10001"

    @pytest.mark.asyncio
    async def test_get_balances(self, adapter):
        """Test getting account balances"""
        balance_data = {
            "list": [
                {
                    "coin": [
                        {"coin": "BTC", "availableToWithdraw": "1.5", "locked": "0.0"},
                        {
                            "coin": "USDT",
                            "availableToWithdraw": "1000.0",
                            "locked": "50.0",
                        },
                        {
                            "coin": "ETH",
                            "availableToWithdraw": "0.0",
                            "locked": "0.0",
                        },  # Zero balance
                    ]
                }
            ]
        }

        with patch.object(adapter, "_make_request", return_value=balance_data):
            balances = await adapter.get_balances()

            assert len(balances) == 2  # Only non-zero balances

            btc_balance = next(b for b in balances if b.asset == "BTC")
            assert btc_balance.free == Decimal("1.5")
            assert btc_balance.locked == Decimal("0.0")
            assert btc_balance.total == Decimal("1.5")

            usdt_balance = next(b for b in balances if b.asset == "USDT")
            assert usdt_balance.free == Decimal("1000.0")
            assert usdt_balance.locked == Decimal("50.0")
            assert usdt_balance.total == Decimal("1050.0")

    @pytest.mark.asyncio
    async def test_get_positions(self, adapter):
        """Test getting open positions"""
        positions_data = {
            "list": [
                {
                    "symbol": "BTCUSDT",
                    "side": "Buy",
                    "size": "0.1",
                    "avgPrice": "50000.0",
                    "markPrice": "50100.0",
                    "unrealisedPnl": "10.0",
                    "positionValue": "5000.0",
                },
                {
                    "symbol": "ETHUSDT",
                    "side": "Sell",
                    "size": "0",  # No position
                    "avgPrice": "0",
                    "markPrice": "4000.0",
                    "unrealisedPnl": "0",
                    "positionValue": "0",
                },
            ]
        }

        with patch.object(adapter, "_make_request", return_value=positions_data):
            positions = await adapter.get_positions()

            assert len(positions) == 1  # Only open positions

            btc_position = positions[0]
            assert btc_position.symbol == "BTCUSDT"
            assert btc_position.side == "buy"
            assert btc_position.size == Decimal("0.1")
            assert btc_position.entry_price == Decimal("50000.0")
            assert btc_position.unrealized_pnl == Decimal("10.0")

    def test_map_order_status(self, adapter):
        """Test order status mapping"""
        assert adapter._map_order_status("New") == OrderStatus.OPEN
        assert (
            adapter._map_order_status("PartiallyFilled") == OrderStatus.PARTIALLY_FILLED
        )
        assert adapter._map_order_status("Filled") == OrderStatus.FILLED
        assert adapter._map_order_status("Cancelled") == OrderStatus.CANCELLED
        assert adapter._map_order_status("Rejected") == OrderStatus.REJECTED
        assert adapter._map_order_status("Unknown") == OrderStatus.PENDING

    def test_map_order_type(self, adapter):
        """Test order type mapping"""
        assert adapter._map_order_type(OrderType.MARKET) == "Market"
        assert adapter._map_order_type(OrderType.LIMIT) == "Limit"
        assert adapter._map_order_type(OrderType.STOP) == "Limit"  # Default fallback

    def test_map_order_side(self, adapter):
        """Test order side mapping"""
        assert adapter._map_order_side(OrderSide.BUY) == "Buy"
        assert adapter._map_order_side(OrderSide.SELL) == "Sell"

    @pytest.mark.asyncio
    async def test_create_order_market(self, adapter):
        """Test creating market order"""
        order_response = {"orderId": "123456", "orderLinkId": ""}

        with (
            patch.object(adapter, "validate_order_params", return_value=True),
            patch.object(adapter, "format_quantity", return_value=Decimal("0.1")),
            patch.object(adapter, "_make_request", return_value=order_response),
        ):
            order = await adapter.create_order(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=Decimal("0.1"),
            )

            assert order.order_id == "123456"
            assert order.symbol == "BTCUSDT"
            assert order.side == OrderSide.BUY
            assert order.order_type == OrderType.MARKET
            assert order.quantity == Decimal("0.1")
            assert order.status == OrderStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_order_limit(self, adapter):
        """Test creating limit order"""
        order_response = {"orderId": "123457", "orderLinkId": ""}

        with (
            patch.object(adapter, "validate_order_params", return_value=True),
            patch.object(adapter, "format_quantity", return_value=Decimal("0.05")),
            patch.object(adapter, "format_price", return_value=Decimal("55000.0")),
            patch.object(adapter, "_make_request", return_value=order_response),
        ):
            order = await adapter.create_order(
                symbol="BTCUSDT",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=Decimal("0.05"),
                price=Decimal("55000.0"),
            )

            assert order.order_id == "123457"
            assert order.side == OrderSide.SELL
            assert order.order_type == OrderType.LIMIT
            assert order.price == Decimal("55000.0")
            assert order.status == OrderStatus.PENDING

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, adapter):
        """Test successful order cancellation"""
        cancel_response = {"orderId": "123456"}

        with patch.object(adapter, "_make_request", return_value=cancel_response):
            result = await adapter.cancel_order("BTCUSDT", "123456")
            assert result is True

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self, adapter):
        """Test failed order cancellation"""
        with patch.object(
            adapter, "_make_request", side_effect=ExchangeError("Order not found")
        ):
            result = await adapter.cancel_order("BTCUSDT", "999999")
            assert result is False

    @pytest.mark.asyncio
    async def test_get_order(self, adapter):
        """Test getting order status"""
        order_response = {
            "list": [
                {
                    "orderId": "123456",
                    "symbol": "BTCUSDT",
                    "side": "Buy",
                    "orderType": "Limit",
                    "qty": "0.1",
                    "price": "50000.0",
                    "orderStatus": "Filled",
                    "cumExecQty": "0.1",
                    "avgPrice": "50000.0",
                    "createdTime": "1640995200000",
                    "updatedTime": "1640995260000",
                }
            ]
        }

        with patch.object(adapter, "_make_request", return_value=order_response):
            order = await adapter.get_order("BTCUSDT", "123456")

            assert order.order_id == "123456"
            assert order.symbol == "BTCUSDT"
            assert order.status == OrderStatus.FILLED
            assert order.side == OrderSide.BUY
            assert order.order_type == OrderType.LIMIT
            assert order.created_at is not None
            assert order.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_order_not_found(self, adapter):
        """Test getting order that doesn't exist"""
        order_response = {"list": []}

        with patch.object(adapter, "_make_request", return_value=order_response):
            with pytest.raises(ExchangeError, match="Order .* not found"):
                await adapter.get_order("BTCUSDT", "999999")

    @pytest.mark.asyncio
    async def test_get_open_orders(self, adapter):
        """Test getting open orders"""
        orders_response = {
            "list": [
                {
                    "orderId": "123456",
                    "symbol": "BTCUSDT",
                    "side": "Buy",
                    "orderType": "Limit",
                    "qty": "0.1",
                    "price": "50000.0",
                    "orderStatus": "New",
                    "cumExecQty": "0",
                    "avgPrice": "",
                    "createdTime": "1640995200000",
                    "updatedTime": "1640995200000",
                },
                {
                    "orderId": "123457",
                    "symbol": "ETHUSDT",
                    "side": "Sell",
                    "orderType": "Limit",
                    "qty": "1.0",
                    "price": "4000.0",
                    "orderStatus": "New",
                    "cumExecQty": "0",
                    "avgPrice": "",
                    "createdTime": "1640995300000",
                    "updatedTime": "1640995300000",
                },
            ]
        }

        with patch.object(adapter, "_make_request", return_value=orders_response):
            orders = await adapter.get_open_orders()

            assert len(orders) == 2
            assert orders[0].order_id == "123456"
            assert orders[0].symbol == "BTCUSDT"
            assert orders[1].order_id == "123457"
            assert orders[1].symbol == "ETHUSDT"

    @pytest.mark.asyncio
    async def test_get_exchange_info(self, adapter):
        """Test getting exchange information"""
        exchange_response = {
            "list": [
                {
                    "symbol": "BTCUSDT",
                    "baseCoin": "BTC",
                    "quoteCoin": "USDT",
                    "lotSizeFilter": {
                        "minOrderQty": "0.00001",
                        "maxOrderQty": "1000",
                        "qtyStep": "0.00001",
                    },
                    "priceFilter": {
                        "minPrice": "0.01",
                        "maxPrice": "1000000",
                        "tickSize": "0.01",
                    },
                }
            ]
        }

        with patch.object(adapter, "_make_request", return_value=exchange_response):
            info = await adapter.get_exchange_info("BTCUSDT")

            assert "BTCUSDT" in info
            symbol_info = info["BTCUSDT"]
            assert symbol_info.symbol == "BTCUSDT"
            assert symbol_info.base_asset == "BTC"
            assert symbol_info.quote_asset == "USDT"
            assert symbol_info.min_quantity == Decimal("0.00001")
            assert symbol_info.min_notional == Decimal("10")  # Default value

    @pytest.mark.asyncio
    async def test_get_ticker_price(self, adapter):
        """Test getting ticker price"""
        price_response = {"list": [{"symbol": "BTCUSDT", "lastPrice": "50000.0"}]}

        with patch.object(adapter, "_make_request", return_value=price_response):
            price = await adapter.get_ticker_price("BTCUSDT")
            assert price == Decimal("50000.0")

    @pytest.mark.asyncio
    async def test_get_ticker_price_not_found(self, adapter):
        """Test getting ticker price for non-existent symbol"""
        price_response = {"list": []}

        with patch.object(adapter, "_make_request", return_value=price_response):
            with pytest.raises(ExchangeError, match="No ticker data for symbol"):
                await adapter.get_ticker_price("INVALIDPAIR")

    @pytest.mark.asyncio
    async def test_validate_order_params(self, adapter):
        """Test order parameter validation"""
        # Mock exchange info
        adapter._exchange_info["BTCUSDT"] = ExchangeInfo(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            min_quantity=Decimal("0.00001"),
            max_quantity=Decimal("1000"),
            quantity_step=Decimal("0.00001"),
            min_price=Decimal("0.01"),
            max_price=Decimal("1000000"),
            price_step=Decimal("0.01"),
            min_notional=Decimal("10.0"),
        )

        with patch.object(adapter, "get_ticker_price", return_value=Decimal("50000.0")):
            # Valid order
            result = await adapter.validate_order_params(
                "BTCUSDT", Decimal("0.001"), Decimal("50000.0")
            )
            assert result is True

            # Invalid quantity - too small
            with pytest.raises(ExchangeError, match="Quantity.*outside valid range"):
                await adapter.validate_order_params("BTCUSDT", Decimal("0.000001"))

            # Invalid price - too low
            with pytest.raises(ExchangeError, match="Price.*outside valid range"):
                await adapter.validate_order_params(
                    "BTCUSDT", Decimal("0.001"), Decimal("0.001")
                )

            # Invalid notional - too small
            with pytest.raises(ExchangeError, match="Notional value.*below minimum"):
                await adapter.validate_order_params("BTCUSDT", Decimal("0.0001"))

    @pytest.mark.asyncio
    async def test_close_session(self, adapter):
        """Test session cleanup"""
        # Create a mock session
        mock_session = AsyncMock()
        mock_session.closed = False
        adapter.session = mock_session

        await adapter.close()
        mock_session.close.assert_called_once()

    def test_format_quantity(self, adapter):
        """Test quantity formatting"""
        adapter._exchange_info["BTCUSDT"] = ExchangeInfo(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            min_quantity=Decimal("0.00001"),
            max_quantity=Decimal("1000"),
            quantity_step=Decimal("0.00001"),
            min_price=Decimal("0.01"),
            max_price=Decimal("1000000"),
            price_step=Decimal("0.01"),
            min_notional=Decimal("10.0"),
        )

        formatted = adapter.format_quantity("BTCUSDT", Decimal("0.123456"))
        assert formatted == Decimal("0.12345")  # Rounded to step size

    def test_format_price(self, adapter):
        """Test price formatting"""
        adapter._exchange_info["BTCUSDT"] = ExchangeInfo(
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            min_quantity=Decimal("0.00001"),
            max_quantity=Decimal("1000"),
            quantity_step=Decimal("0.00001"),
            min_price=Decimal("0.01"),
            max_price=Decimal("1000000"),
            price_step=Decimal("0.01"),
            min_notional=Decimal("10.0"),
        )

        formatted = adapter.format_price("BTCUSDT", Decimal("50000.789"))
        assert formatted == Decimal("50000.78")  # Rounded to step size
