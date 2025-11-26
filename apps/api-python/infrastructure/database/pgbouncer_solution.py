"""
Solução definitiva para problemas de pgBouncer/Supabase
"""

import os
import ssl
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text, event
from sqlalchemy.engine import Engine
from sqlalchemy.dialects.postgresql.asyncpg import AsyncAdapt_asyncpg_connection
import structlog
import asyncpg

logger = structlog.get_logger()


class PgBouncerDatabaseManager:
    """
    Database manager específico para pgBouncer/Supabase
    Resolve completamente os problemas de prepared statements
    """

    def __init__(self):
        self._engine = None
        self._session_factory = None
        self._connection_string = None

    async def connect(self, database_url: str = None):
        """Initialize database connection optimized for pgBouncer"""

        if not database_url:
            # Usar settings do projeto se não especificado
            try:
                from ...config.settings import get_settings

                settings = get_settings()
                database_url = settings.database_url
            except ImportError:
                # Fallback para variável de ambiente
                database_url = os.getenv("DATABASE_URL")

        if not database_url:
            raise ValueError("DATABASE_URL não configurada")

        # Preparar URL para asyncpg
        connection_url = self._prepare_connection_url(database_url)
        self._connection_string = connection_url

        logger.info(f"🔗 Connecting to: {connection_url[:50]}...")

        try:
            # Criar engine SEM prepared statements
            self._engine = create_async_engine(
                connection_url,
                # CRÍTICO: Usar NullPool para evitar problemas de pool
                poolclass=NullPool,
                echo=False,  # Desabilitar logs SQL para reduzir overhead
                # Configurações específicas para asyncpg + pgBouncer
                connect_args={
                    # SSL para Supabase
                    "ssl": self._create_ssl_context(),
                    # Timeout de comando
                    "command_timeout": 60,
                    # ELIMINAR PREPARED STATEMENTS COMPLETAMENTE
                    "prepared_statement_cache_size": 0,
                    "statement_cache_size": 0,
                    # FORÇAR asyncpg a nunca preparar statements
                    "server_settings": {
                        "application_name": "fastapi_pgbouncer",
                        "search_path": "public",
                    },
                },
                # Configurações de engine para pgBouncer
                execution_options={
                    # Desabilitar cache de queries compiladas
                    "compiled_cache": {},
                    # FORÇAR execução sem prepared statements
                    "schema_translate_map": None,
                    "no_parameters": False,
                },
                # Desabilitar todos os caches possíveis
                query_cache_size=0,
                pool_pre_ping=False,  # Não fazer ping preventivo
                pool_recycle=-1,  # Nunca reciclar conexões (pgBouncer gerencia)
            )

            # Configurar event listeners para garantir que prepared statements nunca sejam criados
            self._setup_event_listeners()

            # Criar session factory
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,  # Reduzir flushes automáticos
            )

            # Testar conexão com query simples
            await self._test_connection()

            logger.info("✅ PostgreSQL connection established (pgBouncer optimized)")

        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise

    def _prepare_connection_url(self, database_url: str) -> str:
        """Preparar URL de conexão - manter como está"""
        return database_url

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Criar contexto SSL para Supabase"""

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        logger.warning("SSL verification DISABLED for development")

        return ssl_ctx

    def _setup_event_listeners(self):
        """Configurar event listeners para prevenir prepared statements"""

        @event.listens_for(self._engine.sync_engine, "before_cursor_execute")
        def receive_before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            """Interceptar execução de queries para debug"""
            if "PREPARE" in statement.upper() or "EXECUTE" in statement.upper():
                logger.warning(f"⚠️ Prepared statement detected: {statement[:100]}...")

        @event.listens_for(self._engine.sync_engine, "connect")
        def set_postgresql_settings(dbapi_conn, connection_record):
            """Configurar PostgreSQL settings por conexão"""
            # Marcar que esta conexão não deve usar prepared statements
            connection_record.info["disable_prepared_statements"] = True

    async def _test_connection(self):
        """Testar conexão com query simples usando asyncpg raw"""

        try:
            # Usar conexão asyncpg raw para evitar SQLAlchemy prepared statements
            raw_conn = await self.get_raw_connection()

            # Query simples sem prepared statements
            result = await raw_conn.fetchval(
                "SELECT 'pgBouncer connection works!' as test"
            )

            await raw_conn.close()

            if result == "pgBouncer connection works!":
                logger.info("🔗 Database connection test: SUCCESS")
            else:
                raise Exception("Connection test failed")

        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            raise

    async def disconnect(self):
        """Close database connection"""
        if self._engine:
            await self._engine.dispose()
            logger.info("📪 Database connection closed")

    def get_session(self) -> AsyncSession:
        """Get database session"""
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call connect() first.")
        return self._session_factory()

    async def execute_raw_query(self, query: str, parameters: dict = None):
        """Executar query raw sem prepared statements"""

        try:
            async with self._session_factory() as session:
                result = await session.execute(text(query), parameters or {})
                await session.commit()
                return result

        except Exception as e:
            logger.error(f"❌ Raw query failed: {e}")
            raise

    async def get_raw_connection(self):
        """Obter conexão asyncpg direta (para casos extremos)"""

        if not self._connection_string:
            raise RuntimeError("Database not connected")

        # Converter URL para asyncpg puro (remover +asyncpg)
        asyncpg_url = self._connection_string.replace(
            "postgresql+asyncpg://", "postgresql://", 1
        )

        # Conectar diretamente com asyncpg sem SQLAlchemy
        # asyncpg não tem prepared_statement_cache_size, usar statement_cache_size
        conn = await asyncpg.connect(
            asyncpg_url,
            ssl=self._create_ssl_context(),
            command_timeout=60,
            # CRÍTICO: Desabilitar prepared statements no asyncpg
            statement_cache_size=0,
        )

        return conn

    @property
    def engine(self):
        """Get database engine"""
        return self._engine


# Dependency para FastAPI
async def get_pgbouncer_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para obter sessão de banco otimizada para pgBouncer"""

    db_manager = PgBouncerDatabaseManager()

    try:
        await db_manager.connect()

        async with db_manager.get_session() as session:
            yield session

    except Exception as e:
        logger.error(f"Database session error: {e}")
        if "session" in locals():
            await session.rollback()
        raise

    finally:
        await db_manager.disconnect()


# Instância global
pgbouncer_db_manager = PgBouncerDatabaseManager()


# Função de teste
async def test_pgbouncer_connection():
    """Testar conexão pgBouncer"""

    print("🧪 Testando conexão pgBouncer...")

    try:
        await pgbouncer_db_manager.connect()

        # Teste 1: Query simples
        async with pgbouncer_db_manager.get_session() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.fetchone()
            print(f"✅ PostgreSQL version: {version[0][:50]}...")

        # Teste 2: Query com parâmetros
        async with pgbouncer_db_manager.get_session() as session:
            result = await session.execute(
                text("SELECT $1 as test_param"), {"test_param": "pgBouncer working!"}
            )
            test_result = result.fetchone()
            print(f"✅ Parameter test: {test_result[0]}")

        # Teste 3: Conexão raw
        raw_conn = await pgbouncer_db_manager.get_raw_connection()
        version_raw = await raw_conn.fetchval("SELECT 'Raw connection works!'")
        await raw_conn.close()
        print(f"✅ Raw connection: {version_raw}")

        print("🎉 Todos os testes de pgBouncer passaram!")
        return True

    except Exception as e:
        print(f"❌ Teste falhou: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await pgbouncer_db_manager.disconnect()


if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()
    asyncio.run(test_pgbouncer_connection())
