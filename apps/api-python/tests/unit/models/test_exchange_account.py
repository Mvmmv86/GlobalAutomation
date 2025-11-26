"""Unit tests for ExchangeAccount model"""

from infrastructure.database.models.exchange_account import (
    ExchangeAccount,
    ExchangeType,
    ExchangeEnvironment,
)


class TestExchangeAccount:
    """Test ExchangeAccount model business logic"""

    def test_exchange_account_creation(self):
        """Test exchange account creation with basic fields"""
        account = ExchangeAccount(
            name="Test Binance Account",
            exchange_type=ExchangeType.BINANCE,
            environment=ExchangeEnvironment.TESTNET,
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
            user_id="user-123",
        )

        assert account.name == "Test Binance Account"
        assert account.exchange_type == ExchangeType.BINANCE
        assert account.environment == ExchangeEnvironment.TESTNET
        assert account.is_active is True
        assert account.is_default is False
        assert account.health_status == "unknown"
        assert account.total_orders == 0
        assert account.successful_orders == 0
        assert account.failed_orders == 0

    def test_activate_account(self):
        """Test account activation"""
        account = ExchangeAccount(
            name="Test Account",
            exchange_type=ExchangeType.BINANCE,
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
            user_id="user-123",
            is_active=False,
        )

        account.activate()
        assert account.is_active is True

    def test_deactivate_account(self):
        """Test account deactivation"""
        account = ExchangeAccount(
            name="Test Account",
            exchange_type=ExchangeType.BINANCE,
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
            user_id="user-123",
        )

        account.deactivate()
        assert account.is_active is False

    def test_set_as_default(self):
        """Test setting account as default"""
        account = ExchangeAccount(
            name="Test Account",
            exchange_type=ExchangeType.BINANCE,
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
            user_id="user-123",
        )

        account.set_as_default()
        assert account.is_default is True

    def test_unset_as_default(self):
        """Test unsetting account as default"""
        account = ExchangeAccount(
            name="Test Account",
            exchange_type=ExchangeType.BINANCE,
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
            user_id="user-123",
            is_default=True,
        )

        account.unset_as_default()
        assert account.is_default is False

    def test_update_health_status(self):
        """Test health status update"""
        account = ExchangeAccount(
            name="Test Account",
            exchange_type=ExchangeType.BINANCE,
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
            user_id="user-123",
        )

        # Update to healthy status
        account.update_health_status("healthy")

        assert account.health_status == "healthy"
        assert account.last_health_check is not None
        assert account.last_error is None

        # Update with error
        error_msg = "API connection failed"
        account.update_health_status("error", error_msg)

        assert account.health_status == "error"
        assert account.last_error == error_msg

    def test_increment_order_stats(self):
        """Test order statistics increment"""
        account = ExchangeAccount(
            name="Test Account",
            exchange_type=ExchangeType.BINANCE,
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
            user_id="user-123",
        )

        # Successful order
        account.increment_order_stats(success=True)

        assert account.total_orders == 1
        assert account.successful_orders == 1
        assert account.failed_orders == 0
        assert account.last_trade_at is not None

        # Failed order
        account.increment_order_stats(success=False)

        assert account.total_orders == 2
        assert account.successful_orders == 1
        assert account.failed_orders == 1

    def test_get_success_rate(self):
        """Test success rate calculation"""
        account = ExchangeAccount(
            name="Test Account",
            exchange_type=ExchangeType.BINANCE,
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
            user_id="user-123",
        )

        # No orders yet
        assert account.get_success_rate() == 0.0

        # Add some orders
        account.increment_order_stats(success=True)  # 1/1 = 100%
        assert account.get_success_rate() == 100.0

        account.increment_order_stats(success=False)  # 1/2 = 50%
        assert account.get_success_rate() == 50.0

        account.increment_order_stats(success=True)  # 2/3 = 66.67%
        assert round(account.get_success_rate(), 2) == 66.67

    def test_is_healthy(self):
        """Test health checking"""
        account = ExchangeAccount(
            name="Test Account",
            exchange_type=ExchangeType.BINANCE,
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
            user_id="user-123",
        )

        # Unknown status but active
        account.health_status = "unknown"
        assert account.is_healthy() is False

        # Healthy status and active
        account.health_status = "healthy"
        assert account.is_healthy() is True

        # Warning status and active
        account.health_status = "warning"
        assert account.is_healthy() is True

        # Error status
        account.health_status = "error"
        assert account.is_healthy() is False

        # Inactive account
        account.deactivate()
        account.health_status = "healthy"
        assert account.is_healthy() is False

    def test_can_trade(self):
        """Test trade capability checking"""
        account = ExchangeAccount(
            name="Test Account",
            exchange_type=ExchangeType.BINANCE,
            api_key_encrypted="encrypted_key",
            api_secret_encrypted="encrypted_secret",
            user_id="user-123",
        )

        # Unknown status
        account.health_status = "unknown"
        assert account.can_trade() is False

        # Healthy status and active
        account.health_status = "healthy"
        assert account.can_trade() is True

        # Warning status (not tradeable)
        account.health_status = "warning"
        assert account.can_trade() is False

        # Inactive account
        account.deactivate()
        account.health_status = "healthy"
        assert account.can_trade() is False

    def test_exchange_type_enum(self):
        """Test ExchangeType enum values"""
        assert ExchangeType.BINANCE == "binance"
        assert ExchangeType.BYBIT == "bybit"

    def test_exchange_environment_enum(self):
        """Test ExchangeEnvironment enum values"""
        assert ExchangeEnvironment.TESTNET == "testnet"
        assert ExchangeEnvironment.MAINNET == "mainnet"
