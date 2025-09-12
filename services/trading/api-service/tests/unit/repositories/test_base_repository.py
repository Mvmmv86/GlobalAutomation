"""Unit tests for BaseRepository"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from infrastructure.database.repositories.base import BaseRepository
from infrastructure.database.models.user import User


class TestBaseRepository:
    """Test BaseRepository CRUD operations"""

    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create repository instance"""
        return BaseRepository(User, mock_session)

    @pytest.mark.asyncio
    async def test_create(self, repository, mock_session):
        """Test creating a new instance"""
        # Setup
        user_data = {"email": "test@example.com", "password_hash": "hashed123"}

        # Execute
        result = await repository.create(user_data)

        # Verify
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()
        assert isinstance(result, User)
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get(self, repository, mock_session):
        """Test getting instance by ID"""
        # Setup
        user_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = User(
            id=user_id, email="test@example.com", password_hash="hashed123"
        )
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get(user_id)

        # Verify
        mock_session.execute.assert_called_once()
        assert result is not None
        assert result.id == user_id

    @pytest.mark.asyncio
    async def test_get_not_found(self, repository, mock_session):
        """Test getting non-existent instance"""
        # Setup
        user_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get(user_id)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_get_multi_with_filters(self, repository, mock_session):
        """Test getting multiple instances with filters"""
        # Setup
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            User(email="user1@test.com", password_hash="hash1"),
            User(email="user2@test.com", password_hash="hash2"),
        ]
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_multi(
            skip=0, limit=10, filters={"is_active": True}
        )

        # Verify
        assert len(result) == 2
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(self, repository, mock_session):
        """Test updating instance"""
        # Setup
        user_id = str(uuid4())
        update_data = {"name": "Updated Name"}

        mock_result = MagicMock()
        updated_user = User(
            id=user_id,
            email="test@example.com",
            name="Updated Name",
            password_hash="hashed123",
        )
        mock_result.scalar_one_or_none.return_value = updated_user
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.update(user_id, update_data)

        # Verify
        mock_session.execute.assert_called_once()
        mock_session.refresh.assert_called_once()
        assert result is not None
        assert result.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_with_none_values(self, repository, mock_session):
        """Test updating with None values (should be filtered out)"""
        # Setup
        user_id = str(uuid4())
        update_data = {"name": "Updated Name", "description": None}

        # Mock get method to return existing user
        existing_user = User(
            id=user_id, email="test@example.com", password_hash="hashed123"
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            existing_user
        )

        # Execute
        result = await repository.update(user_id, update_data)

        # Verify - should still execute query even after filtering None values
        mock_session.execute.assert_called()
        assert result is not None

    @pytest.mark.asyncio
    async def test_delete(self, repository, mock_session):
        """Test deleting instance"""
        # Setup
        user_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.delete(user_id)

        # Verify
        assert result is True
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        """Test deleting non-existent instance"""
        # Setup
        user_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.delete(user_id)

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_count(self, repository, mock_session):
        """Test counting instances"""
        # Setup
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.count()

        # Verify
        assert result == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_with_filters(self, repository, mock_session):
        """Test counting with filters"""
        # Setup
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.count(filters={"is_active": True})

        # Verify
        assert result == 3

    @pytest.mark.asyncio
    async def test_exists(self, repository, mock_session):
        """Test checking if instance exists"""
        # Setup
        user_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.exists(user_id)

        # Verify
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_not_found(self, repository, mock_session):
        """Test checking non-existent instance"""
        # Setup
        user_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.exists(user_id)

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_get_by_field(self, repository, mock_session):
        """Test getting instance by field"""
        # Setup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = User(
            email="test@example.com", password_hash="hashed123"
        )
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_field("email", "test@example.com")

        # Verify
        assert result is not None
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_by_field_invalid_field(self, repository, mock_session):
        """Test getting by non-existent field"""
        # Execute
        result = await repository.get_by_field("invalid_field", "value")

        # Verify
        assert result is None
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_create(self, repository, mock_session):
        """Test bulk creating instances"""
        # Setup
        users_data = [
            {"email": "user1@test.com", "password_hash": "hash1"},
            {"email": "user2@test.com", "password_hash": "hash2"},
        ]

        # Execute
        result = await repository.bulk_create(users_data)

        # Verify
        mock_session.add_all.assert_called_once()
        mock_session.flush.assert_called_once()
        assert len(result) == 2
        assert all(isinstance(user, User) for user in result)

    @pytest.mark.asyncio
    async def test_bulk_update(self, repository, mock_session):
        """Test bulk updating instances"""
        # Setup
        updates = [
            {"id": str(uuid4()), "name": "User 1"},
            {"id": str(uuid4()), "name": "User 2"},
        ]

        # Execute
        result = await repository.bulk_update(updates)

        # Verify
        assert result == 2
        # Should be called once per update
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_bulk_update_empty(self, repository, mock_session):
        """Test bulk update with empty list"""
        # Execute
        result = await repository.bulk_update([])

        # Verify
        assert result == 0
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_soft_delete_supported(self, repository, mock_session):
        """Test soft delete when model supports it"""
        # Setup - User model doesn't have is_deleted, so it will fall back to hard delete
        user_id = str(uuid4())
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.soft_delete(user_id)

        # Verify
        assert result is True
        mock_session.execute.assert_called_once()

    def test_build_query_with_filters(self, repository):
        """Test query building with filters"""
        # Setup
        filters = {"is_active": True, "created_at": {"gte": datetime.now()}}

        # Execute
        query = repository._build_query(filters=filters)

        # Verify - query should be built without errors
        assert query is not None

    def test_build_query_with_search(self, repository):
        """Test query building with search"""
        # Execute
        query = repository._build_query(search="test", search_fields=["email", "name"])

        # Verify - query should be built without errors
        assert query is not None

    def test_build_query_with_list_filter(self, repository):
        """Test query building with list filter"""
        # Setup
        filters = {"status": ["active", "pending"]}

        # Execute
        query = repository._build_query(filters=filters)

        # Verify - query should be built without errors
        assert query is not None
