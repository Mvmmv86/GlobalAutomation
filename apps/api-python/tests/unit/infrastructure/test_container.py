"""Tests for dependency injection container"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.di.container import Container


class TestContainer:
    """Test cases for DI Container"""

    def test_container_initialization(self):
        """Test container initialization"""
        container = Container()
        assert container._services == {}
        assert container._factories == {}
        assert container._singletons == {}

    def test_register_singleton(self):
        """Test singleton registration"""
        container = Container()
        instance = "test_instance"

        container.register_singleton("test", instance)

        assert "test" in container._singletons
        assert container._singletons["test"] == instance

    def test_register_factory(self):
        """Test factory registration"""
        container = Container()

        def test_factory():
            return "factory_result"

        container.register_factory("test", test_factory)

        assert "test" in container._factories
        assert container._factories["test"] == test_factory

    def test_register_service(self):
        """Test service registration"""
        container = Container()

        class TestService:
            def __init__(self, param1, param2):
                self.param1 = param1
                self.param2 = param2

        container.register_service(
            "test", TestService, param1="value1", param2="value2"
        )

        assert "test" in container._services
        assert container._services["test"]["class"] == TestService
        assert container._services["test"]["kwargs"] == {
            "param1": "value1",
            "param2": "value2",
        }

    def test_get_singleton(self):
        """Test getting singleton instance"""
        container = Container()
        instance = "test_instance"

        container.register_singleton("test", instance)
        result = container.get("test")

        assert result == instance

    def test_get_factory(self):
        """Test getting factory result"""
        container = Container()

        def test_factory():
            return "factory_result"

        container.register_factory("test", test_factory)
        result = container.get("test")

        assert result == "factory_result"

    def test_get_service(self):
        """Test getting service instance"""
        container = Container()

        class TestService:
            def __init__(self, param1, param2):
                self.param1 = param1
                self.param2 = param2

        container.register_service(
            "test", TestService, param1="value1", param2="value2"
        )
        result = container.get("test")

        assert isinstance(result, TestService)
        assert result.param1 == "value1"
        assert result.param2 == "value2"

    def test_get_service_with_dependency_injection(self):
        """Test service with dependency injection"""
        container = Container()

        # Register dependency
        container.register_singleton("dependency", "dep_value")

        class TestService:
            def __init__(self, param1, dependency):
                self.param1 = param1
                self.dependency = dependency

        # Register service with dependency reference
        container.register_service(
            "test", TestService, param1="value1", dependency="@dependency"
        )
        result = container.get("test")

        assert isinstance(result, TestService)
        assert result.param1 == "value1"
        assert result.dependency == "dep_value"

    def test_get_nonexistent_service(self):
        """Test getting nonexistent service raises KeyError"""
        container = Container()

        with pytest.raises(KeyError):
            container.get("nonexistent")

    @pytest.mark.asyncio
    @patch("infrastructure.di.container.create_async_engine")
    @patch("infrastructure.di.container.async_sessionmaker")
    @patch("infrastructure.di.container.get_settings")
    async def test_initialize_database(
        self, mock_get_settings, mock_sessionmaker, mock_create_engine
    ):
        """Test database initialization"""
        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql+asyncpg://test"
        mock_settings.database_echo = False
        mock_get_settings.return_value = mock_settings

        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine

        mock_session_factory = MagicMock()
        mock_sessionmaker.return_value = mock_session_factory

        container = Container()
        await container.initialize_database()

        # Verify engine creation
        mock_create_engine.assert_called_once_with(
            "postgresql+asyncpg://test",
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        # Verify sessionmaker creation
        mock_sessionmaker.assert_called_once_with(
            mock_engine, class_=AsyncSession, expire_on_commit=False
        )

        # Verify registrations
        assert "database_engine" in container._singletons
        assert "database_session" in container._factories

    @pytest.mark.asyncio
    async def test_setup_repositories(self):
        """Test repository setup"""
        container = Container()

        # Mock session factory
        mock_session = AsyncMock(spec=AsyncSession)
        container.register_factory("database_session", lambda: mock_session)

        await container.setup_repositories()

        # Verify all repositories are registered
        expected_repos = [
            "user_repository",
            "api_key_repository",
            "exchange_account_repository",
            "webhook_repository",
            "webhook_delivery_repository",
            "order_repository",
            "position_repository",
        ]

        for repo_name in expected_repos:
            assert repo_name in container._factories

    @pytest.mark.asyncio
    async def test_session_scope_success(self):
        """Test successful session scope"""
        container = Container()

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        container.register_factory("database_session", lambda: mock_session)

        async with container.session_scope() as session:
            assert session == mock_session

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_scope_with_exception(self):
        """Test session scope with exception"""
        container = Container()

        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        container.register_factory("database_session", lambda: mock_session)

        with pytest.raises(ValueError):
            async with container.session_scope() as session:
                assert session == mock_session
                raise ValueError("Test error")

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self):
        """Test container cleanup"""
        container = Container()

        # Mock engine
        mock_engine = AsyncMock()
        container._engine = mock_engine

        await container.close()

        mock_engine.dispose.assert_called_once()
