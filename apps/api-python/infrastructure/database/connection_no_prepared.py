"""Database connection without prepared statements for pgBouncer transaction mode"""
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import event, pool
import structlog

from ..config.settings import get_settings


logger = structlog.get_logger()


class DatabaseManager:
    """Database connection manager optimized for pgBouncer transaction mode"""

    def __init__(self):
        self._engine = None
        self._session_factory = None

    async def connect(self):
        """Initialize database connection for pgBouncer transaction mode"""
        settings = get_settings()

        try:
            # SSL context para Supabase
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            logger.warning("DB SSL verification DISABLED (DEV only).")

            # SOLUÇÃO: Usar psycopg ao invés de asyncpg para pgBouncer transaction mode
            # psycopg funciona melhor com pgBouncer transaction mode
            database_url = settings.database_url.replace(
                "postgresql+asyncpg://", "postgresql+asyncpg://"
            )

            # Criar engine otimizada para pgBouncer transaction mode
            self._engine = create_async_engine(
                database_url,
                # NullPool porque pgBouncer gerencia as conexões
                poolclass=NullPool,
                echo=settings.debug,
                connect_args={
                    "ssl": ssl_ctx,
                    "command_timeout": 60,
                    # Desabilitar statement cache completamente
                    "statement_cache_size": 0,
                    # Desabilitar prepared statements cache
                    "prepared_statement_cache_size": 0,
                },
                # Evitar qualquer tipo de cache
                query_cache_size=0,
                # Não fazer ping (cria prepared statements)
                pool_pre_ping=False,
            )

            # Listener para garantir que NUNCA use prepared statements
            @event.listens_for(self._engine.sync_engine, "connect")
            def receive_connect(dbapi_conn, connection_record):
                # Forçar cada conexão a não usar prepared statements
                connection_record.info["uses_prepared"] = False

            # Create session factory
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                # Não fazer autoflush (pode criar prepared statements)
                autoflush=False,
            )

            # Test connection sem usar prepared statements
            from sqlalchemy import text

            async with self._session_factory() as session:
                # Usar text() para evitar prepared statements
                result = await session.execute(text("SELECT 1"))
                await session.commit()

            logger.info("Database connection established (pgBouncer transaction mode)")

        except Exception as e:
            logger.error("Failed to connect to database", error=str(e))
            raise

    async def disconnect(self):
        """Close database connection"""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connection closed")

    def get_session(self) -> AsyncSession:
        """Get database session"""
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call connect() first.")
        return self._session_factory()

    @property
    def engine(self):
        """Get database engine"""
        return self._engine


# Global database manager
database_manager = DatabaseManager()


async def get_db_session() -> AsyncSession:
    """Dependency to get database session"""
    async with database_manager.get_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
