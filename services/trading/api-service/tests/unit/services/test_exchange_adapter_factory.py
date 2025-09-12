"""Tests for ExchangeAdapterFactory"""

import pytest
from application.services.exchange_adapter_factory import ExchangeAdapterFactory
from infrastructure.external.exchange_adapters import (
    BinanceAdapter,
    BybitAdapter,
    BaseExchangeAdapter,
    ExchangeError,
)


class TestExchangeAdapterFactory:
    """Test cases for ExchangeAdapterFactory"""

    def test_create_binance_adapter(self):
        """Test creating Binance adapter"""
        adapter = ExchangeAdapterFactory.create_adapter(
            "binance", "test_key", "test_secret", testnet=True
        )

        assert isinstance(adapter, BinanceAdapter)
        assert adapter.name == "binance"
        assert adapter.api_key == "test_key"
        assert adapter.api_secret == "test_secret"
        assert adapter.testnet is True

    def test_create_bybit_adapter(self):
        """Test creating Bybit adapter"""
        adapter = ExchangeAdapterFactory.create_adapter(
            "bybit", "test_key", "test_secret", testnet=False
        )

        assert isinstance(adapter, BybitAdapter)
        assert adapter.name == "bybit"
        assert adapter.api_key == "test_key"
        assert adapter.api_secret == "test_secret"
        assert adapter.testnet is False

    def test_create_adapter_case_insensitive(self):
        """Test that exchange name is case insensitive"""
        adapter = ExchangeAdapterFactory.create_adapter(
            "BINANCE", "test_key", "test_secret"
        )

        assert isinstance(adapter, BinanceAdapter)

        adapter2 = ExchangeAdapterFactory.create_adapter(
            "Bybit", "test_key", "test_secret"
        )

        assert isinstance(adapter2, BybitAdapter)

    def test_create_unsupported_exchange(self):
        """Test creating adapter for unsupported exchange"""
        with pytest.raises(ExchangeError) as exc_info:
            ExchangeAdapterFactory.create_adapter("kraken", "test_key", "test_secret")

        assert "Unsupported exchange: kraken" in str(exc_info.value)
        assert "binance, bybit" in str(exc_info.value)

    def test_get_supported_exchanges(self):
        """Test getting list of supported exchanges"""
        exchanges = ExchangeAdapterFactory.get_supported_exchanges()

        assert "binance" in exchanges
        assert "bybit" in exchanges
        assert len(exchanges) == 2

    def test_is_supported(self):
        """Test checking if exchange is supported"""
        assert ExchangeAdapterFactory.is_supported("binance") is True
        assert ExchangeAdapterFactory.is_supported("BYBIT") is True
        assert ExchangeAdapterFactory.is_supported("kraken") is False
        assert ExchangeAdapterFactory.is_supported("coinbase") is False

    def test_register_new_adapter(self):
        """Test registering a new adapter"""

        class MockExchange(BaseExchangeAdapter):
            @property
            def name(self) -> str:
                return "mock"

            async def test_connection(self) -> bool:
                return True

            async def get_account_info(self):
                return {}

            async def get_balances(self):
                return []

            async def get_positions(self):
                return []

            async def create_order(
                self,
                symbol,
                side,
                order_type,
                quantity,
                price=None,
                stop_price=None,
                time_in_force="GTC",
                client_order_id=None,
            ):
                pass

            async def cancel_order(self, symbol, order_id):
                return True

            async def get_order(self, symbol, order_id):
                pass

            async def get_open_orders(self, symbol=None):
                return []

            async def get_exchange_info(self, symbol=None):
                return {}

            async def get_ticker_price(self, symbol):
                return 0

        # Register new adapter
        ExchangeAdapterFactory.register_adapter("mock", MockExchange)

        # Test that it's now supported
        assert ExchangeAdapterFactory.is_supported("mock") is True

        # Test creating the adapter
        adapter = ExchangeAdapterFactory.create_adapter(
            "mock", "test_key", "test_secret"
        )

        assert isinstance(adapter, MockExchange)
        assert adapter.name == "mock"

        # Clean up - remove the registered adapter
        del ExchangeAdapterFactory._adapters["mock"]
