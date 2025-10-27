"""Dependency Injection Container"""

from typing import Dict, Any, Callable, TypeVar, Optional
from contextlib import asynccontextmanager
import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from infrastructure.config.settings import get_settings
from infrastructure.database.repositories import (
    UserRepository,
    APIKeyRepository,
    ExchangeAccountRepository,
    WebhookRepository,
    WebhookDeliveryRepository,
    OrderRepository,
    PositionRepository,
)
from infrastructure.security.encryption_service import EncryptionService
from infrastructure.security.key_manager import KeyManager
from application.services.exchange_credentials_service import ExchangeCredentialsService
from application.services.secure_exchange_service import SecureExchangeService
from application.services.tradingview_webhook_service import TradingViewWebhookService

T = TypeVar("T")
logger = logging.getLogger(__name__)


class Container:
    """Simple Dependency Injection Container"""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._engine = None
        self._sessionmaker = None

    def register_singleton(self, name: str, instance: Any) -> None:
        """Register a singleton instance"""
        self._singletons[name] = instance
        logger.debug(f"Registered singleton: {name}")

    def register_factory(self, name: str, factory: Callable[[], T]) -> None:
        """Register a factory function"""
        self._factories[name] = factory
        logger.debug(f"Registered factory: {name}")

    def register_service(self, name: str, service_class: type, **kwargs) -> None:
        """Register a service class with dependencies"""
        self._services[name] = {"class": service_class, "kwargs": kwargs}
        logger.debug(f"Registered service: {name}")

    def get(self, name: str) -> Any:
        """Get a service by name"""
        # Check singletons first
        if name in self._singletons:
            return self._singletons[name]

        # Check factories
        if name in self._factories:
            return self._factories[name]()

        # Check services
        if name in self._services:
            service_config = self._services[name]
            service_class = service_config["class"]
            kwargs = service_config.get("kwargs", {})

            # Resolve dependencies in kwargs
            resolved_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str) and value.startswith("@"):
                    # Dependency reference
                    dep_name = value[1:]  # Remove @
                    resolved_kwargs[key] = self.get(dep_name)
                else:
                    resolved_kwargs[key] = value

            return service_class(**resolved_kwargs)

        raise KeyError(f"Service '{name}' not found in container")

    async def initialize_database(self) -> None:
        """Initialize database engine and session maker"""
        settings = get_settings()

        # FIX: Usar NullPool para compatibilidade com PgBouncer (Supabase)
        # PgBouncer em session mode não suporta pool grande de conexões
        # Deixar o PgBouncer gerenciar o pool ao invés do SQLAlchemy
        from sqlalchemy.pool import NullPool
        import ssl

        # SSL context para Supabase
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        self._engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,

            # ✅ FIX PGBOUNCER: Usar NullPool ao invés de pool fixo
            # Evita "MaxClientsInSessionMode: max clients reached"
            poolclass=NullPool,  # PgBouncer gerencia conexões

            # ✅ ASYNCPG OPTIMIZATIONS para PgBouncer
            connect_args={
                "ssl": ssl_ctx,
                "statement_cache_size": 0,  # PgBouncer não suporta prepared statements
                "prepared_statement_cache_size": 0,
                "command_timeout": 60,  # Timeout de comandos SQL
                "server_settings": {
                    "application_name": "tradingview_webhook_api",
                    "jit": "off",  # Desabilitar JIT para melhor previsibilidade
                },
            },
            # Desabilitar cache de compilação
            query_cache_size=0,
            pool_pre_ping=False,  # Evitar pings que criam statements
            # Execution options para evitar prepared statements
            execution_options={
                "postgresql_prepared": False,
                "no_autoflush": True,
            },
        )

        self._sessionmaker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False  # ✅ CRÍTICO para operações async
        )

        self.register_singleton("database_engine", self._engine)
        self.register_factory("database_session", self._create_session)
        logger.info("Database initialized")

    def _create_session(self) -> AsyncSession:
        """Create a new database session"""
        if not self._sessionmaker:
            raise RuntimeError(
                "Database not initialized. Call initialize_database() first."
            )
        return self._sessionmaker()

    async def setup_repositories(self) -> None:
        """Setup repository dependencies"""

        # Register repository factories that depend on session
        def create_user_repository():
            session = self.get("database_session")
            return UserRepository(session)

        def create_api_key_repository():
            session = self.get("database_session")
            return APIKeyRepository(session)

        def create_exchange_account_repository():
            session = self.get("database_session")
            return ExchangeAccountRepository(session)

        def create_webhook_repository():
            session = self.get("database_session")
            return WebhookRepository(session)

        def create_webhook_delivery_repository():
            session = self.get("database_session")
            return WebhookDeliveryRepository(session)

        def create_order_repository():
            session = self.get("database_session")
            return OrderRepository(session)

        def create_position_repository():
            session = self.get("database_session")
            return PositionRepository(session)

        self.register_factory("user_repository", create_user_repository)
        self.register_factory("api_key_repository", create_api_key_repository)
        self.register_factory(
            "exchange_account_repository", create_exchange_account_repository
        )
        self.register_factory("webhook_repository", create_webhook_repository)
        self.register_factory(
            "webhook_delivery_repository", create_webhook_delivery_repository
        )
        self.register_factory("order_repository", create_order_repository)
        self.register_factory("position_repository", create_position_repository)

        logger.info("Repositories registered")

    async def setup_security_services(self) -> None:
        """Setup security service dependencies"""

        # Register security services as singletons
        key_manager = KeyManager()
        encryption_service = EncryptionService()

        self.register_singleton("key_manager", key_manager)
        self.register_singleton("encryption_service", encryption_service)

        logger.info("Security services registered")

    async def setup_application_services(self) -> None:
        """Setup application service dependencies"""

        # Register auth service
        from infrastructure.services.auth_service import AuthService

        self.register_singleton("auth_service", AuthService())

        # Register user service
        from application.services.user_service import UserService

        self.register_service(
            "user_service",
            UserService,
            user_repository="@user_repository",
            api_key_repository="@api_key_repository",
        )

        # Register application services
        self.register_service(
            "exchange_credentials_service",
            ExchangeCredentialsService,
            exchange_account_repository="@exchange_account_repository",
            encryption_service="@encryption_service",
            key_manager="@key_manager",
        )

        self.register_service(
            "secure_exchange_service",
            SecureExchangeService,
            exchange_credentials_service="@exchange_credentials_service",
        )

        # Webhook services
        from application.services.webhook_service import WebhookService

        self.register_service(
            "webhook_service",
            WebhookService,
            webhook_repository="@webhook_repository",
            webhook_delivery_repository="@webhook_delivery_repository",
            user_repository="@user_repository",
        )

        self.register_service(
            "tradingview_webhook_service",
            TradingViewWebhookService,
            webhook_service="@webhook_service",
            secure_exchange_service="@secure_exchange_service",
            exchange_account_repository="@exchange_account_repository",
            user_repository="@user_repository",
        )

        logger.info("Application services registered")

    @asynccontextmanager
    async def session_scope(self):
        """Provide a transactional scope around a series of operations"""
        session = self.get("database_session")
        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            # ✅ TRATAMENTO ESPECIAL para task cancellation (hot reload, etc)
            logger.warning("Session cancelled, rolling back")
            try:
                await session.rollback()
            except Exception as e:
                logger.error(f"Error rolling back cancelled session: {e}")
            raise
        except Exception:
            await session.rollback()
            raise
        finally:
            try:
                await session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")

    async def close(self) -> None:
        """Close database connections"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connections closed")


# Global container instance
_container: Optional[Container] = None


async def get_container() -> Container:
    """Get or create the global container instance"""
    global _container

    if _container is None:
        _container = Container()
        # ✅ HABILITADO - Necessário para webhooks do TradingView funcionarem
        await _container.initialize_database()
        await _container.setup_repositories()
        await _container.setup_security_services()
        await _container.setup_application_services()

    return _container


async def cleanup_container() -> None:
    """Cleanup the global container"""
    global _container

    if _container is not None:
        await _container.close()
        _container = None
