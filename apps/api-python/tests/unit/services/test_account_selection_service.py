"""Tests for AccountSelectionService"""

import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal
from uuid import uuid4

from application.services.account_selection_service import (
    AccountSelectionService,
    SelectionCriteria,
    TradingRequest,
    AccountScore,
)
from infrastructure.database.models.exchange_account import (
    ExchangeAccount,
    ExchangeType,
    ExchangeEnvironment,
)
from infrastructure.external.exchange_adapters import Balance, ExchangeError


class TestAccountSelectionService:
    """Test cases for AccountSelectionService"""

    @pytest.fixture
    def mock_exchange_account_repo(self):
        """Mock ExchangeAccountRepository"""
        return AsyncMock()

    @pytest.fixture
    def account_selection_service(self, mock_exchange_account_repo):
        """AccountSelectionService instance for testing"""
        return AccountSelectionService(mock_exchange_account_repo)

    @pytest.fixture
    def sample_accounts(self):
        """Sample exchange accounts for testing"""
        return [
            ExchangeAccount(
                id=str(uuid4()),
                user_id=str(uuid4()),
                name="Binance Main",
                exchange_type=ExchangeType.BINANCE,
                environment=ExchangeEnvironment.TESTNET,
                api_key_encrypted="encrypted_binance_key",
                api_secret_encrypted="encrypted_binance_secret",
                is_active=True,
            ),
            ExchangeAccount(
                id=str(uuid4()),
                user_id=str(uuid4()),
                name="Bybit Pro",
                exchange_type=ExchangeType.BYBIT,
                environment=ExchangeEnvironment.TESTNET,
                api_key_encrypted="encrypted_bybit_key",
                api_secret_encrypted="encrypted_bybit_secret",
                is_active=True,
            ),
        ]

    @pytest.fixture
    def trading_request(self):
        """Sample trading request"""
        return TradingRequest(
            symbol="BTCUSDT", side="buy", quantity=Decimal("0.1"), order_type="market"
        )

    @pytest.fixture
    def mock_adapter(self):
        """Mock exchange adapter"""
        adapter = AsyncMock()
        adapter.name = "binance"
        adapter.test_connection.return_value = True
        adapter.get_balances.return_value = [
            Balance(
                asset="USDT",
                free=Decimal("5000.0"),
                locked=Decimal("0.0"),
                total=Decimal("5000.0"),
            )
        ]
        adapter.get_ticker_price.return_value = Decimal("50000.0")
        adapter.validate_order_params.return_value = True
        return adapter

    def test_selection_criteria_weights(self, account_selection_service):
        """Test that selection criteria have proper weights"""
        weights = account_selection_service._score_weights

        # Test that all criteria exist
        for criteria in SelectionCriteria:
            assert criteria in weights

        # Test that weights sum to 1.0 for each criteria
        for criteria, weight_dict in weights.items():
            total_weight = sum(weight_dict.values())
            assert (
                abs(total_weight - 1.0) < 0.01
            )  # Allow small floating point differences

    @pytest.mark.asyncio
    async def test_select_best_account_no_accounts(
        self, account_selection_service, mock_exchange_account_repo, trading_request
    ):
        """Test selection when no accounts available"""
        mock_exchange_account_repo.get_user_active_accounts.return_value = []

        result = await account_selection_service.select_best_account(
            "user123", trading_request
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_filter_accounts(self, account_selection_service, sample_accounts):
        """Test account filtering"""
        # Test normal filtering
        trading_request = TradingRequest(
            symbol="BTCUSDT", side="buy", quantity=Decimal("0.1")
        )

        filtered = account_selection_service._filter_accounts(
            sample_accounts, trading_request
        )
        assert len(filtered) == 2  # Both accounts should pass

        # Test with excluded exchanges
        trading_request.exclude_exchanges = ["binance"]
        filtered = account_selection_service._filter_accounts(
            sample_accounts, trading_request
        )
        assert len(filtered) == 1
        assert filtered[0].exchange_type == ExchangeType.BYBIT

        # Test with inactive account
        sample_accounts[0].is_active = False
        filtered = account_selection_service._filter_accounts(
            sample_accounts, trading_request
        )
        assert len(filtered) == 1
        assert filtered[0].exchange_type == ExchangeType.BYBIT

    @pytest.mark.asyncio
    async def test_get_adapter_caching(
        self, account_selection_service, sample_accounts
    ):
        """Test adapter caching"""
        account = sample_accounts[0]

        with patch(
            "application.services.account_selection_service.ExchangeAdapterFactory.create_adapter"
        ) as mock_factory:
            mock_adapter = AsyncMock()
            mock_factory.return_value = mock_adapter

            # First call should create adapter
            adapter1 = await account_selection_service._get_adapter(account)
            assert adapter1 == mock_adapter
            mock_factory.assert_called_once()

            # Second call should use cached adapter
            adapter2 = await account_selection_service._get_adapter(account)
            assert adapter2 == mock_adapter
            assert adapter1 is adapter2
            # Factory should still be called only once
            assert mock_factory.call_count == 1

    def test_extract_quote_asset(self, account_selection_service):
        """Test quote asset extraction from symbols"""
        assert account_selection_service._extract_quote_asset("BTCUSDT") == "USDT"
        assert account_selection_service._extract_quote_asset("ETHUSDC") == "USDC"
        assert account_selection_service._extract_quote_asset("BNBBTC") == "BTC"
        assert account_selection_service._extract_quote_asset("DOGEETH") == "ETH"
        assert (
            account_selection_service._extract_quote_asset("UNKNOWNPAIR") == "USDT"
        )  # Default

    @pytest.mark.asyncio
    async def test_estimate_trade_value_buy(
        self, account_selection_service, mock_adapter
    ):
        """Test trade value estimation for buy orders"""
        trading_request = TradingRequest(
            symbol="BTCUSDT", side="buy", quantity=Decimal("0.1")
        )

        mock_adapter.get_ticker_price.return_value = Decimal("50000.0")

        value = await account_selection_service._estimate_trade_value(
            mock_adapter, trading_request
        )

        assert value == Decimal("5000.0")  # 0.1 * 50000
        mock_adapter.get_ticker_price.assert_called_once_with("BTCUSDT")

    @pytest.mark.asyncio
    async def test_estimate_trade_value_sell(
        self, account_selection_service, mock_adapter
    ):
        """Test trade value estimation for sell orders"""
        trading_request = TradingRequest(
            symbol="BTCUSDT", side="sell", quantity=Decimal("0.1")
        )

        value = await account_selection_service._estimate_trade_value(
            mock_adapter, trading_request
        )

        assert value == Decimal("0.1")  # For sell, we need the base asset quantity
        mock_adapter.get_ticker_price.assert_not_called()

    @pytest.mark.asyncio
    async def test_estimate_fees(self, account_selection_service, trading_request):
        """Test fee estimation for different exchanges"""
        mock_binance = AsyncMock()
        mock_binance.name = "binance"

        mock_bybit = AsyncMock()
        mock_bybit.name = "bybit"

        mock_unknown = AsyncMock()
        mock_unknown.name = "kraken"

        # Test Binance fees
        fee = await account_selection_service._estimate_fees(
            mock_binance, trading_request
        )
        assert fee == Decimal("0.001")

        # Test Bybit fees
        fee = await account_selection_service._estimate_fees(
            mock_bybit, trading_request
        )
        assert fee == Decimal("0.001")

        # Test unknown exchange fees
        fee = await account_selection_service._estimate_fees(
            mock_unknown, trading_request
        )
        assert fee == Decimal("0.002")

    @pytest.mark.asyncio
    async def test_score_liquidity(
        self, account_selection_service, mock_adapter, trading_request
    ):
        """Test liquidity scoring"""
        # Test successful price fetch (good liquidity)
        mock_adapter.get_ticker_price.return_value = Decimal("50000.0")
        score = await account_selection_service._score_liquidity(
            mock_adapter, trading_request
        )
        assert score == 0.8

        # Test failed price fetch (poor liquidity)
        mock_adapter.get_ticker_price.side_effect = ExchangeError("Price not available")
        score = await account_selection_service._score_liquidity(
            mock_adapter, trading_request
        )
        assert score == 0.2

    @pytest.mark.asyncio
    async def test_validate_account_for_trade_success(
        self, account_selection_service, sample_accounts, trading_request, mock_adapter
    ):
        """Test successful account validation"""
        account = sample_accounts[0]

        with (
            patch.object(
                account_selection_service, "_get_adapter", return_value=mock_adapter
            ),
            patch.object(
                account_selection_service,
                "_estimate_trade_value",
                return_value=Decimal("5000.0"),
            ),
            patch.object(
                account_selection_service, "_extract_quote_asset", return_value="USDT"
            ),
        ):
            (
                is_valid,
                error,
            ) = await account_selection_service.validate_account_for_trade(
                account, trading_request
            )

            assert is_valid is True
            assert error is None

    @pytest.mark.asyncio
    async def test_validate_account_for_trade_connection_failed(
        self, account_selection_service, sample_accounts, trading_request
    ):
        """Test account validation with connection failure"""
        account = sample_accounts[0]
        mock_adapter = AsyncMock()
        mock_adapter.test_connection.return_value = False

        with patch.object(
            account_selection_service, "_get_adapter", return_value=mock_adapter
        ):
            (
                is_valid,
                error,
            ) = await account_selection_service.validate_account_for_trade(
                account, trading_request
            )

            assert is_valid is False
            assert error == "Connection failed"

    @pytest.mark.asyncio
    async def test_validate_account_for_trade_insufficient_balance(
        self, account_selection_service, sample_accounts, trading_request
    ):
        """Test account validation with insufficient balance"""
        account = sample_accounts[0]
        mock_adapter = AsyncMock()
        mock_adapter.test_connection.return_value = True
        mock_adapter.get_balances.return_value = [
            Balance(
                asset="USDT",
                free=Decimal("100.0"),  # Insufficient for 5000 USDT trade
                locked=Decimal("0.0"),
                total=Decimal("100.0"),
            )
        ]
        mock_adapter.validate_order_params.return_value = True

        with (
            patch.object(
                account_selection_service, "_get_adapter", return_value=mock_adapter
            ),
            patch.object(
                account_selection_service,
                "_estimate_trade_value",
                return_value=Decimal("5000.0"),
            ),
            patch.object(
                account_selection_service, "_extract_quote_asset", return_value="USDT"
            ),
        ):
            (
                is_valid,
                error,
            ) = await account_selection_service.validate_account_for_trade(
                account, trading_request
            )

            assert is_valid is False
            assert "Insufficient balance" in error
            assert "Required: 5000" in error
            assert "Available: 100" in error

    @pytest.mark.asyncio
    async def test_validate_account_for_trade_exchange_error(
        self, account_selection_service, sample_accounts, trading_request
    ):
        """Test account validation with exchange error"""
        account = sample_accounts[0]
        mock_adapter = AsyncMock()
        mock_adapter.test_connection.return_value = True
        mock_adapter.get_balances.side_effect = ExchangeError("API rate limit exceeded")

        with patch.object(
            account_selection_service, "_get_adapter", return_value=mock_adapter
        ):
            (
                is_valid,
                error,
            ) = await account_selection_service.validate_account_for_trade(
                account, trading_request
            )

            assert is_valid is False
            assert "Exchange error: API rate limit exceeded" in error

    @pytest.mark.asyncio
    async def test_score_single_account_success(
        self, account_selection_service, sample_accounts, trading_request, mock_adapter
    ):
        """Test scoring a single account successfully"""
        account = sample_accounts[0]
        weights = {
            "balance": 0.3,
            "fee": 0.3,
            "liquidity": 0.2,
            "speed": 0.1,
            "health": 0.1,
        }

        with (
            patch.object(
                account_selection_service, "_get_adapter", return_value=mock_adapter
            ),
            patch.object(
                account_selection_service,
                "_estimate_trade_value",
                return_value=Decimal("5000.0"),
            ),
            patch.object(
                account_selection_service, "_extract_quote_asset", return_value="USDT"
            ),
            patch.object(
                account_selection_service,
                "_estimate_fees",
                return_value=Decimal("0.001"),
            ),
            patch.object(
                account_selection_service, "_score_liquidity", return_value=0.8
            ),
        ):
            score = await account_selection_service._score_single_account(
                account, trading_request, weights
            )

            assert isinstance(score, AccountScore)
            assert score.account == account
            assert score.adapter == mock_adapter
            assert score.health_score == 1.0  # Connection successful
            assert score.balance_score > 0  # Should have good balance score
            assert score.fee_score > 0  # Should have fee score
            assert score.liquidity_score == 0.8
            assert score.speed_score > 0  # Should have speed score
            assert score.total_score > 0  # Should have positive total score
            assert score.available_balance == Decimal("5000.0")
            assert score.estimated_fee == Decimal("0.001")
            assert score.connection_latency is not None
            assert score.error_message is None

    @pytest.mark.asyncio
    async def test_score_single_account_connection_failed(
        self, account_selection_service, sample_accounts, trading_request
    ):
        """Test scoring account with connection failure"""
        account = sample_accounts[0]
        weights = {
            "balance": 0.3,
            "fee": 0.3,
            "liquidity": 0.2,
            "speed": 0.1,
            "health": 0.1,
        }

        mock_adapter = AsyncMock()
        mock_adapter.test_connection.return_value = False

        with patch.object(
            account_selection_service, "_get_adapter", return_value=mock_adapter
        ):
            score = await account_selection_service._score_single_account(
                account, trading_request, weights
            )

            assert score.health_score == 0.0
            assert score.error_message == "Connection failed"

    @pytest.mark.asyncio
    async def test_score_single_account_exception(
        self, account_selection_service, sample_accounts, trading_request
    ):
        """Test scoring account with exception"""
        account = sample_accounts[0]
        weights = {
            "balance": 0.3,
            "fee": 0.3,
            "liquidity": 0.2,
            "speed": 0.1,
            "health": 0.1,
        }

        with patch.object(
            account_selection_service,
            "_get_adapter",
            side_effect=Exception("Adapter creation failed"),
        ):
            score = await account_selection_service._score_single_account(
                account, trading_request, weights
            )

            assert score.health_score == 0.0
            assert "Adapter creation failed" in score.error_message

    @pytest.mark.asyncio
    async def test_select_best_account_success(
        self,
        account_selection_service,
        mock_exchange_account_repo,
        sample_accounts,
        trading_request,
        mock_adapter,
    ):
        """Test successful best account selection"""
        mock_exchange_account_repo.get_user_active_accounts.return_value = (
            sample_accounts
        )

        with (
            patch.object(
                account_selection_service, "_get_adapter", return_value=mock_adapter
            ),
            patch.object(
                account_selection_service,
                "_estimate_trade_value",
                return_value=Decimal("5000.0"),
            ),
            patch.object(
                account_selection_service, "_extract_quote_asset", return_value="USDT"
            ),
            patch.object(
                account_selection_service,
                "_estimate_fees",
                return_value=Decimal("0.001"),
            ),
            patch.object(
                account_selection_service, "_score_liquidity", return_value=0.8
            ),
        ):
            best_account = await account_selection_service.select_best_account(
                "user123", trading_request, SelectionCriteria.BALANCED
            )

            assert best_account is not None
            assert isinstance(best_account, AccountScore)
            assert best_account.total_score > 0
            assert best_account.account in sample_accounts

    @pytest.mark.asyncio
    async def test_get_ranked_accounts(
        self,
        account_selection_service,
        mock_exchange_account_repo,
        sample_accounts,
        trading_request,
        mock_adapter,
    ):
        """Test getting ranked accounts"""
        mock_exchange_account_repo.get_user_active_accounts.return_value = (
            sample_accounts
        )

        with (
            patch.object(
                account_selection_service, "_get_adapter", return_value=mock_adapter
            ),
            patch.object(
                account_selection_service,
                "_estimate_trade_value",
                return_value=Decimal("5000.0"),
            ),
            patch.object(
                account_selection_service, "_extract_quote_asset", return_value="USDT"
            ),
            patch.object(
                account_selection_service,
                "_estimate_fees",
                return_value=Decimal("0.001"),
            ),
            patch.object(
                account_selection_service, "_score_liquidity", return_value=0.8
            ),
        ):
            ranked_accounts = await account_selection_service.get_ranked_accounts(
                "user123", trading_request, SelectionCriteria.BEST_BALANCE, limit=5
            )

            assert len(ranked_accounts) <= 5
            assert len(ranked_accounts) <= len(sample_accounts)

            # Check that accounts are sorted by score (descending)
            for i in range(1, len(ranked_accounts)):
                assert (
                    ranked_accounts[i - 1].total_score >= ranked_accounts[i].total_score
                )

    @pytest.mark.asyncio
    async def test_close_adapters(self, account_selection_service):
        """Test closing all adapters"""
        # Add some mock adapters to cache
        mock_adapter1 = AsyncMock()
        mock_adapter2 = AsyncMock()

        account_selection_service._adapter_cache = {
            "adapter1": mock_adapter1,
            "adapter2": mock_adapter2,
        }

        await account_selection_service.close_adapters()

        # Check that close was called on all adapters
        mock_adapter1.close.assert_called_once()
        mock_adapter2.close.assert_called_once()

        # Check that cache is cleared
        assert len(account_selection_service._adapter_cache) == 0
