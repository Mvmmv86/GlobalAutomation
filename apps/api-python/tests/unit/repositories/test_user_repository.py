"""Unit tests for UserRepository and APIKeyRepository"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from infrastructure.database.repositories.user import UserRepository, APIKeyRepository
from infrastructure.database.models.user import User, APIKey


class TestUserRepository:
    """Test UserRepository operations"""

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create UserRepository instance"""
        return UserRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_email(self, repository, mock_session):
        """Test getting user by email"""
        # Setup
        email = "test@example.com"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = User(
            email=email, password_hash="hashed123"
        )
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_email(email)

        # Verify
        assert result is not None
        assert result.email == email
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_email_case_insensitive(self, repository, mock_session):
        """Test getting user by email (case insensitive)"""
        # Setup
        email = "TEST@EXAMPLE.COM"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = User(
            email="test@example.com", password_hash="hashed123"
        )
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_email(email)

        # Verify
        assert result is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_relationships(self, repository, mock_session):
        """Test getting user with relationships loaded"""
        # Setup
        user_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = User(
            id=user_id, email="test@example.com", password_hash="hashed123"
        )
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_with_relationships(user_id)

        # Verify
        assert result is not None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_users(self, repository, mock_session):
        """Test getting active users"""
        # Setup
        repository.get_multi = AsyncMock(
            return_value=[
                User(email="user1@test.com", is_active=True, password_hash="hash1"),
                User(email="user2@test.com", is_active=True, password_hash="hash2"),
            ]
        )

        # Execute
        result = await repository.get_active_users(skip=0, limit=10)

        # Verify
        assert len(result) == 2
        repository.get_multi.assert_called_once_with(
            skip=0, limit=10, filters={"is_active": True}, order_by="-created_at"
        )

    @pytest.mark.asyncio
    async def test_search_users(self, repository, mock_session):
        """Test searching users"""
        # Setup
        search_term = "john"
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            User(email="john@test.com", name="John Doe", password_hash="hash1")
        ]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.search_users(search_term, skip=0, limit=10)

        # Verify
        assert len(result) == 1
        assert result[0].name == "John Doe"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_login(self, repository, mock_session):
        """Test updating last login timestamp"""
        # Setup
        user_id = str(uuid4())
        repository.update = AsyncMock(return_value=User(id=user_id))

        # Execute
        result = await repository.update_last_login(user_id)

        # Verify
        assert result is True
        repository.update.assert_called_once()
        # Check that the update call includes the expected fields
        call_args = repository.update.call_args[0]
        assert call_args[0] == user_id
        update_data = call_args[1]
        assert "failed_login_attempts" in update_data
        assert update_data["failed_login_attempts"] == 0

    @pytest.mark.asyncio
    async def test_increment_failed_login(self, repository, mock_session):
        """Test incrementing failed login attempts"""
        # Setup
        user_id = str(uuid4())
        user = User(
            id=user_id,
            email="test@example.com",
            password_hash="hashed123",
            failed_login_attempts=2,
        )
        repository.get = AsyncMock(return_value=user)

        # Execute
        result = await repository.increment_failed_login(user_id)

        # Verify
        assert result is not None
        assert result.failed_login_attempts == 3
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_failed_login_user_not_found(
        self, repository, mock_session
    ):
        """Test incrementing failed login for non-existent user"""
        # Setup
        user_id = str(uuid4())
        repository.get = AsyncMock(return_value=None)

        # Execute
        result = await repository.increment_failed_login(user_id)

        # Verify
        assert result is None
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_stats(self, repository, mock_session):
        """Test getting user statistics"""
        # Setup
        mock_results = [
            MagicMock(scalar=lambda: 100),  # total
            MagicMock(scalar=lambda: 85),  # active
            MagicMock(scalar=lambda: 75),  # verified
            MagicMock(scalar=lambda: 30),  # totp_enabled
        ]
        mock_session.execute.side_effect = mock_results

        # Execute
        result = await repository.get_stats()

        # Verify
        assert result["total"] == 100
        assert result["active"] == 85
        assert result["verified"] == 75
        assert result["totp_enabled"] == 30
        assert mock_session.execute.call_count == 4


class TestAPIKeyRepository:
    """Test APIKeyRepository operations"""

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create APIKeyRepository instance"""
        return APIKeyRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_key_hash(self, repository, mock_session):
        """Test getting API key by hash"""
        # Setup
        key_hash = "hashed_key_123"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = APIKey(
            name="Test Key", key_hash=key_hash, user_id=str(uuid4())
        )
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_key_hash(key_hash)

        # Verify
        assert result is not None
        assert result.key_hash == key_hash
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_api_keys(self, repository, mock_session):
        """Test getting API keys for a user"""
        # Setup
        user_id = str(uuid4())
        repository.get_multi = AsyncMock(
            return_value=[
                APIKey(name="Key 1", key_hash="hash1", user_id=user_id),
                APIKey(name="Key 2", key_hash="hash2", user_id=user_id),
            ]
        )

        # Execute
        result = await repository.get_user_api_keys(user_id, active_only=True)

        # Verify
        assert len(result) == 2
        repository.get_multi.assert_called_once_with(
            filters={"user_id": user_id, "is_active": True}, order_by="-created_at"
        )

    @pytest.mark.asyncio
    async def test_get_user_api_keys_all(self, repository, mock_session):
        """Test getting all API keys for a user (including inactive)"""
        # Setup
        user_id = str(uuid4())
        repository.get_multi = AsyncMock(return_value=[])

        # Execute
        await repository.get_user_api_keys(user_id, active_only=False)

        # Verify
        repository.get_multi.assert_called_once_with(
            filters={"user_id": user_id}, order_by="-created_at"
        )

    @pytest.mark.asyncio
    async def test_record_usage(self, repository, mock_session):
        """Test recording API key usage"""
        # Setup
        api_key_id = str(uuid4())
        api_key = APIKey(
            id=api_key_id,
            name="Test Key",
            key_hash="hash123",
            user_id=str(uuid4()),
            usage_count=5,
        )
        repository.get = AsyncMock(return_value=api_key)

        # Execute
        result = await repository.record_usage(api_key_id)

        # Verify
        assert result is True
        assert api_key.usage_count == 6
        assert api_key.last_used_at is not None
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_usage_key_not_found(self, repository, mock_session):
        """Test recording usage for non-existent key"""
        # Setup
        api_key_id = str(uuid4())
        repository.get = AsyncMock(return_value=None)

        # Execute
        result = await repository.record_usage(api_key_id)

        # Verify
        assert result is False
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_usage_stats(self, repository, mock_session):
        """Test getting usage statistics"""
        # Setup
        mock_results = [
            MagicMock(scalar=lambda: 10),  # total keys
            MagicMock(scalar=lambda: 8),  # active keys
            MagicMock(
                first=lambda: MagicMock(total_usage=500, avg_usage=50.0, max_usage=200)
            ),
        ]
        mock_session.execute.side_effect = mock_results

        # Execute
        result = await repository.get_usage_stats()

        # Verify
        assert result["total_keys"] == 10
        assert result["active_keys"] == 8
        assert result["total_usage"] == 500
        assert result["average_usage"] == 50.0
        assert result["max_usage"] == 200

    @pytest.mark.asyncio
    async def test_cleanup_expired_keys(self, repository, mock_session):
        """Test cleaning up expired keys"""
        # Setup
        expired_key1 = APIKey(
            id=str(uuid4()),
            name="Expired Key 1",
            key_hash="hash1",
            user_id=str(uuid4()),
            expires_at=datetime.now(),
        )
        expired_key2 = APIKey(
            id=str(uuid4()),
            name="Expired Key 2",
            key_hash="hash2",
            user_id=str(uuid4()),
            expires_at=datetime.now(),
        )

        repository.get_expired_keys = AsyncMock(
            return_value=[expired_key1, expired_key2]
        )
        repository.soft_delete = AsyncMock(return_value=True)

        # Execute
        result = await repository.cleanup_expired_keys()

        # Verify
        assert result == 2
        assert repository.soft_delete.call_count == 2
