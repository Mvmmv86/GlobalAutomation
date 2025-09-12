"""Tests for UserService"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from application.services.user_service import UserService
from infrastructure.database.models.user import User, APIKey


class TestUserService:
    """Test cases for UserService"""

    @pytest.fixture
    def mock_user_repo(self):
        """Mock UserRepository"""
        return AsyncMock()

    @pytest.fixture
    def mock_api_key_repo(self):
        """Mock APIKeyRepository"""
        return AsyncMock()

    @pytest.fixture
    def user_service(self, mock_user_repo, mock_api_key_repo):
        """UserService instance with mocked repositories"""
        return UserService(mock_user_repo, mock_api_key_repo)

    @pytest.fixture
    def sample_user(self):
        """Sample user for testing"""
        return User(
            id=str(uuid4()),
            email="test@example.com",
            password_hash="hashed123",
            is_active=True,
            is_verified=True,
        )

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_service, mock_user_repo, sample_user):
        """Test getting user by ID"""
        user_id = uuid4()
        mock_user_repo.get.return_value = sample_user

        result = await user_service.get_user_by_id(user_id)

        assert result == sample_user
        mock_user_repo.get.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_service, mock_user_repo, sample_user):
        """Test getting user by email"""
        email = "test@example.com"
        mock_user_repo.get_by_email.return_value = sample_user

        result = await user_service.get_user_by_email(email)

        assert result == sample_user
        mock_user_repo.get_by_email.assert_called_once_with(email)

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_user_repo, sample_user):
        """Test successful user creation"""
        user_data = {
            "email": "NEW@EXAMPLE.COM",
            "password_hash": "hashed123",
            "name": "Test User",
        }

        mock_user_repo.get_by_email.return_value = None  # Email not exists
        mock_user_repo.create.return_value = sample_user

        result = await user_service.create_user(user_data)

        assert result == sample_user
        # Should check for existing email
        mock_user_repo.get_by_email.assert_called_once_with("NEW@EXAMPLE.COM")
        # Should create with lowercase email
        expected_data = user_data.copy()
        expected_data["email"] = "new@example.com"
        mock_user_repo.create.assert_called_once_with(expected_data)

    @pytest.mark.asyncio
    async def test_create_user_email_exists(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test user creation with existing email"""
        user_data = {"email": "test@example.com", "password_hash": "hashed123"}

        mock_user_repo.get_by_email.return_value = sample_user  # Email exists

        with pytest.raises(ValueError, match="Email already registered"):
            await user_service.create_user(user_data)

        mock_user_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_filters_sensitive_fields(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test user update filters sensitive fields"""
        user_id = uuid4()
        update_data = {
            "name": "Updated Name",
            "password_hash": "should_be_filtered",  # Sensitive
            "totp_secret": "should_be_filtered",  # Sensitive
            "failed_login_attempts": 5,  # Sensitive
            "locked_until": datetime.now(),  # Sensitive
            "email": "new@email.com",  # Should be kept
        }

        mock_user_repo.update.return_value = sample_user

        result = await user_service.update_user(user_id, update_data)

        assert result == sample_user

        # Check that sensitive fields were filtered out
        call_args = mock_user_repo.update.call_args[0]
        assert call_args[0] == user_id
        filtered_data = call_args[1]

        assert "name" in filtered_data
        assert "email" in filtered_data
        assert "password_hash" not in filtered_data
        assert "totp_secret" not in filtered_data
        assert "failed_login_attempts" not in filtered_data
        assert "locked_until" not in filtered_data

    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test successful user authentication"""
        email = "test@example.com"
        password = "correct_password"

        # Mock user with successful password verification
        sample_user.is_locked = MagicMock(return_value=False)
        sample_user.verify_password = MagicMock(return_value=True)

        mock_user_repo.get_by_email.return_value = sample_user
        mock_user_repo.update_last_login.return_value = None

        result = await user_service.authenticate_user(email, password)

        assert result == sample_user
        mock_user_repo.get_by_email.assert_called_once_with(email)
        sample_user.verify_password.assert_called_once_with(password)
        mock_user_repo.update_last_login.assert_called_once_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, user_service, mock_user_repo):
        """Test authentication with non-existent user"""
        email = "nonexistent@example.com"
        password = "password"

        mock_user_repo.get_by_email.return_value = None

        result = await user_service.authenticate_user(email, password)

        assert result is None
        mock_user_repo.get_by_email.assert_called_once_with(email)

    @pytest.mark.asyncio
    async def test_authenticate_user_locked(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test authentication with locked user"""
        email = "test@example.com"
        password = "password"

        sample_user.is_locked = MagicMock(return_value=True)
        mock_user_repo.get_by_email.return_value = sample_user

        result = await user_service.authenticate_user(email, password)

        assert result is None
        sample_user.is_locked.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test authentication with wrong password"""
        email = "test@example.com"
        password = "wrong_password"

        sample_user.is_locked = MagicMock(return_value=False)
        sample_user.verify_password = MagicMock(return_value=False)

        mock_user_repo.get_by_email.return_value = sample_user
        mock_user_repo.increment_failed_login.return_value = None

        result = await user_service.authenticate_user(email, password)

        assert result is None
        sample_user.verify_password.assert_called_once_with(password)
        mock_user_repo.increment_failed_login.assert_called_once_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_change_password_success(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test successful password change"""
        user_id = uuid4()
        old_password = "old_password"
        new_password = "new_password"

        sample_user.verify_password = MagicMock(return_value=True)
        sample_user.hash_password = MagicMock(return_value="hashed_new_password")

        mock_user_repo.get.return_value = sample_user
        mock_user_repo.update.return_value = None

        result = await user_service.change_password(user_id, old_password, new_password)

        assert result is True
        mock_user_repo.get.assert_called_once_with(user_id)
        sample_user.verify_password.assert_called_once_with(old_password)
        sample_user.hash_password.assert_called_once_with(new_password)
        mock_user_repo.update.assert_called_once_with(
            user_id, {"password_hash": "hashed_new_password"}
        )

    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(
        self, user_service, mock_user_repo, sample_user
    ):
        """Test password change with wrong old password"""
        user_id = uuid4()
        old_password = "wrong_old_password"
        new_password = "new_password"

        sample_user.verify_password = MagicMock(return_value=False)
        mock_user_repo.get.return_value = sample_user

        result = await user_service.change_password(user_id, old_password, new_password)

        assert result is False
        mock_user_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_api_keys(self, user_service, mock_api_key_repo):
        """Test getting user API keys"""
        user_id = uuid4()
        expected_keys = [
            APIKey(id=str(uuid4()), user_id=str(user_id), name="Key 1"),
            APIKey(id=str(uuid4()), user_id=str(user_id), name="Key 2"),
        ]

        mock_api_key_repo.get_user_api_keys.return_value = expected_keys

        result = await user_service.get_user_api_keys(user_id)

        assert result == expected_keys
        mock_api_key_repo.get_user_api_keys.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_create_api_key(self, user_service, mock_api_key_repo):
        """Test API key creation"""
        user_id = uuid4()
        name = "Test API Key"
        expires_days = 30

        mock_api_key = AsyncMock(spec=APIKey)
        mock_api_key.id = str(uuid4())
        mock_api_key.key_hash = "generated_hash"
        mock_api_key.generate_key_hash = MagicMock()

        mock_api_key_repo.create.return_value = mock_api_key
        mock_api_key_repo.update.return_value = None

        result = await user_service.create_api_key(user_id, name, expires_days)

        assert result == mock_api_key

        # Verify create was called with correct data
        create_call_args = mock_api_key_repo.create.call_args[0][0]
        assert create_call_args["user_id"] == str(user_id)
        assert create_call_args["name"] == name
        assert create_call_args["is_active"] is True
        assert "expires_at" in create_call_args

        # Verify key hash generation and update
        mock_api_key.generate_key_hash.assert_called_once()
        mock_api_key_repo.update.assert_called_once_with(
            mock_api_key.id, {"key_hash": mock_api_key.key_hash}
        )

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, user_service, mock_api_key_repo):
        """Test successful API key revocation"""
        user_id = uuid4()
        key_id = uuid4()

        mock_api_key = AsyncMock(spec=APIKey)
        mock_api_key.user_id = str(user_id)

        mock_api_key_repo.get.return_value = mock_api_key
        mock_api_key_repo.soft_delete.return_value = True

        result = await user_service.revoke_api_key(user_id, key_id)

        assert result is True
        mock_api_key_repo.get.assert_called_once_with(key_id)
        mock_api_key_repo.soft_delete.assert_called_once_with(key_id)

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_owned(self, user_service, mock_api_key_repo):
        """Test API key revocation for key not owned by user"""
        user_id = uuid4()
        key_id = uuid4()
        other_user_id = uuid4()

        mock_api_key = AsyncMock(spec=APIKey)
        mock_api_key.user_id = str(other_user_id)  # Different user

        mock_api_key_repo.get.return_value = mock_api_key

        result = await user_service.revoke_api_key(user_id, key_id)

        assert result is False
        mock_api_key_repo.soft_delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_api_key_success(
        self, user_service, mock_api_key_repo, mock_user_repo, sample_user
    ):
        """Test successful API key authentication"""
        key_hash = "valid_key_hash"

        mock_api_key = AsyncMock(spec=APIKey)
        mock_api_key.id = str(uuid4())
        mock_api_key.user_id = str(uuid4())
        mock_api_key.is_active = True
        mock_api_key.is_expired = MagicMock(return_value=False)

        mock_api_key_repo.get_by_key_hash.return_value = mock_api_key
        mock_api_key_repo.record_usage.return_value = None
        mock_user_repo.get.return_value = sample_user

        result = await user_service.authenticate_api_key(key_hash)

        assert result == sample_user
        mock_api_key_repo.get_by_key_hash.assert_called_once_with(key_hash)
        mock_api_key.is_expired.assert_called_once()
        mock_api_key_repo.record_usage.assert_called_once_with(mock_api_key.id)
        mock_user_repo.get.assert_called_once_with(mock_api_key.user_id)

    @pytest.mark.asyncio
    async def test_authenticate_api_key_expired(self, user_service, mock_api_key_repo):
        """Test API key authentication with expired key"""
        key_hash = "expired_key_hash"

        mock_api_key = AsyncMock(spec=APIKey)
        mock_api_key.is_active = True
        mock_api_key.is_expired = MagicMock(return_value=True)

        mock_api_key_repo.get_by_key_hash.return_value = mock_api_key

        result = await user_service.authenticate_api_key(key_hash)

        assert result is None
        mock_api_key_repo.record_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_stats(self, user_service, mock_user_repo):
        """Test getting user statistics"""
        expected_stats = {
            "total": 100,
            "active": 85,
            "verified": 70,
            "totp_enabled": 30,
        }

        mock_user_repo.get_stats.return_value = expected_stats

        result = await user_service.get_user_stats()

        assert result == expected_stats
        mock_user_repo.get_stats.assert_called_once()
