"""Unit tests for User and APIKey models"""

from datetime import datetime, timedelta
from infrastructure.database.models.user import User, APIKey


class TestUser:
    """Test User model business logic"""

    def test_user_creation(self):
        """Test user creation with basic fields"""
        user = User(
            email="test@example.com",
            name="Test User",
            password_hash="hashed_pass_123",
        )

        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.totp_enabled is False
        assert user.failed_login_attempts == 0

    def test_activate_user(self):
        """Test user activation"""
        user = User(
            email="test@example.com", password_hash="hashed_pass_123", is_active=False
        )

        user.activate()
        assert user.is_active is True

    def test_deactivate_user(self):
        """Test user deactivation"""
        user = User(email="test@example.com", password_hash="hashed_pass_123")

        user.deactivate()
        assert user.is_active is False

    def test_verify_email(self):
        """Test email verification"""
        user = User(
            email="test@example.com",
            password_hash="hashed_pass_123",
            verification_token="token123",
        )

        user.verify_email()
        assert user.is_verified is True
        assert user.verification_token is None

    def test_enable_totp(self):
        """Test TOTP enabling"""
        user = User(email="test@example.com", password_hash="hashed_pass_123")

        secret = "ABCDEFGHIJKLMNOP"
        user.enable_totp(secret)

        assert user.totp_enabled is True
        assert user.totp_secret == secret

    def test_disable_totp(self):
        """Test TOTP disabling"""
        user = User(
            email="test@example.com",
            password_hash="hashed_pass_123",
            totp_secret="ABCDEFGHIJKLMNOP",
            totp_enabled=True,
        )

        user.disable_totp()

        assert user.totp_enabled is False
        assert user.totp_secret is None

    def test_failed_login_management(self):
        """Test failed login attempts management"""
        user = User(email="test@example.com", password_hash="hashed_pass_123")

        # Test increment
        user.increment_failed_login()
        assert user.failed_login_attempts == 1

        user.increment_failed_login()
        assert user.failed_login_attempts == 2

        # Test reset
        user.reset_failed_login()
        assert user.failed_login_attempts == 0

    def test_account_locking(self):
        """Test account locking and unlocking"""
        user = User(email="test@example.com", password_hash="hashed_pass_123")

        # Initially not locked
        assert user.is_locked() is False

        # Lock account
        lock_time = datetime.now() + timedelta(hours=1)
        user.lock_account(lock_time)

        assert user.locked_until == lock_time
        assert user.is_locked() is True

        # Unlock account
        user.unlock_account()

        assert user.locked_until is None
        assert user.failed_login_attempts == 0
        assert user.is_locked() is False

    def test_expired_lock(self):
        """Test that expired locks are considered unlocked"""
        user = User(email="test@example.com", password_hash="hashed_pass_123")

        # Set lock time in the past
        past_time = datetime.now() - timedelta(hours=1)
        user.lock_account(past_time)

        # Should not be locked since time has passed
        assert user.is_locked() is False


class TestAPIKey:
    """Test APIKey model business logic"""

    def test_api_key_creation(self):
        """Test API key creation with basic fields"""
        api_key = APIKey(
            name="Test API Key", key_hash="hashed_key_123", user_id="user-123"
        )

        assert api_key.name == "Test API Key"
        assert api_key.key_hash == "hashed_key_123"
        assert api_key.is_active is True
        assert api_key.usage_count == 0
        assert api_key.last_used_at is None

    def test_activate_api_key(self):
        """Test API key activation"""
        api_key = APIKey(
            name="Test API Key",
            key_hash="hashed_key_123",
            user_id="user-123",
            is_active=False,
        )

        api_key.activate()
        assert api_key.is_active is True

    def test_deactivate_api_key(self):
        """Test API key deactivation"""
        api_key = APIKey(
            name="Test API Key", key_hash="hashed_key_123", user_id="user-123"
        )

        api_key.deactivate()
        assert api_key.is_active is False

    def test_record_usage(self):
        """Test usage recording"""
        api_key = APIKey(
            name="Test API Key", key_hash="hashed_key_123", user_id="user-123"
        )

        # Record first usage
        api_key.record_usage()

        assert api_key.usage_count == 1
        assert api_key.last_used_at is not None

        first_usage_time = api_key.last_used_at

        # Record second usage
        api_key.record_usage()

        assert api_key.usage_count == 2
        assert api_key.last_used_at >= first_usage_time

    def test_is_expired(self):
        """Test expiration checking"""
        api_key = APIKey(
            name="Test API Key", key_hash="hashed_key_123", user_id="user-123"
        )

        # No expiration set
        assert api_key.is_expired() is False

        # Set future expiration
        future_time = datetime.now() + timedelta(days=1)
        api_key.expires_at = future_time
        assert api_key.is_expired() is False

        # Set past expiration
        past_time = datetime.now() - timedelta(days=1)
        api_key.expires_at = past_time
        assert api_key.is_expired() is True

    def test_is_valid(self):
        """Test validity checking"""
        api_key = APIKey(
            name="Test API Key", key_hash="hashed_key_123", user_id="user-123"
        )

        # Active and not expired
        assert api_key.is_valid() is True

        # Deactivated
        api_key.deactivate()
        assert api_key.is_valid() is False

        # Reactivate but set expiration in past
        api_key.activate()
        api_key.expires_at = datetime.now() - timedelta(days=1)
        assert api_key.is_valid() is False

        # Remove expiration
        api_key.expires_at = None
        assert api_key.is_valid() is True
