"""Database connection management"""
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import event
import structlog

from ..config.settings import get_settings


logger = structlog.get_logger()


class DatabaseManager:
    """Database connection manager"""

    def __init__(self):
        self._engine = None
        self._session_factory = None

    async def connect(self):
        """Initialize database connection"""
        settings = get_settings()

        try:
            # Usar SQLite apenas se explicitamente configurado
            if settings.database_url.startswith("sqlite"):
                self._engine = create_async_engine(
                    settings.database_url,
                    poolclass=NullPool,
                    echo=settings.debug,
                )
            else:
                # ---------- Configuração para pgBouncer/Supabase ----------
                # SSL context para Supabase
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
                logger.warning("DB SSL verification DISABLED (DEV only).")

                # Criar engine SEM prepared statements
                # pgBouncer não suporta prepared statements
                self._engine = create_async_engine(
                    settings.database_url,
                    poolclass=NullPool,  # Sem pool, pgBouncer gerencia
                    echo=settings.debug,
                    connect_args={
                        "ssl": ssl_ctx,
                        "command_timeout": 60,
                        # CRÍTICO: Desabilitar completamente prepared statements
                        "prepared_statement_cache_size": 0,
                        "statement_cache_size": 0,
                        # Adicionar flag para desabilitar preparação
                        "prepared_statement_name_func": lambda *_: None,
                    },
                    # Desabilitar cache de compilação
                    query_cache_size=0,
                    pool_pre_ping=False,  # Evitar pings que criam statements
                    # Adicionar execution options para evitar prepared statements
                    execution_options={
                        "postgresql_prepared": False,
                        "no_autoflush": True,
                    },
                )

                # Adicionar listener para garantir que cada conexão
                # seja configurada sem prepared statements
                @event.listens_for(self._engine.sync_engine, "connect")
                def receive_connect(dbapi_conn, connection_record):
                    # Forçar desabilitação de prepared statements
                    # em cada nova conexão
                    _ = dbapi_conn  # Usar parâmetro para evitar warning
                    connection_record.info["prepared_statements"] = False

            # Create session factory
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Test connection
            from sqlalchemy import text

            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))

            logger.info("Database connection established")

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


def get_async_session():
    """Get async session for background tasks"""
    return database_manager.get_session()


3
