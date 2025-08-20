"""
Database connection for Supabase pgBouncer in Transaction Mode
Evita completamente prepared statements
"""
import ssl
import asyncpg
from typing import Optional
import structlog

try:
    from ..config.settings import get_settings
except ImportError:
    # Para testes diretos
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from infrastructure.config.settings import get_settings

logger = structlog.get_logger()


class TransactionModeDatabase:
    """
    Database manager para pgBouncer em transaction mode
    Usa asyncpg diretamente para evitar SQLAlchemy prepared statements
    """

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._database_url = None

    async def connect(self):
        """Initialize connection pool"""
        settings = get_settings()

        # Converter SQLAlchemy URL para asyncpg URL
        database_url = settings.database_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        self._database_url = database_url

        # SSL context para Supabase
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            # Criar pool de conexões asyncpg
            # statement_cache_size=0 é CRÍTICO para pgBouncer transaction mode
            self._pool = await asyncpg.create_pool(
                database_url,
                ssl=ssl_ctx,
                statement_cache_size=0,  # CRÍTICO: Sem cache de statements
                command_timeout=60,
                min_size=1,
                max_size=10,
            )

            # Testar conexão
            async with self._pool.acquire() as conn:
                result = await conn.fetchval("SELECT 'Connected to Supabase'")
                logger.info(f"Database test: {result}")

            logger.info("✅ Database connected (pgBouncer transaction mode compatible)")

        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise

    async def disconnect(self):
        """Close connection pool"""
        if self._pool:
            # Usar timeout para evitar travamento
            import asyncio

            try:
                await asyncio.wait_for(self._pool.close(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Pool close timeout - forcing termination")
            logger.info("Database disconnected")

    async def execute(self, query: str, *args):
        """Execute a query"""
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        """Fetch rows"""
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchval(self, query: str, *args):
        """Fetch single value"""
        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def fetchrow(self, query: str, *args):
        """Fetch single row"""
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    @property
    def pool(self):
        """Get connection pool"""
        return self._pool


# Global instance
transaction_db = TransactionModeDatabase()


# Teste
async def test_transaction_mode():
    """Testar conexão com pgBouncer transaction mode"""
    from dotenv import load_dotenv

    load_dotenv()

    try:
        await transaction_db.connect()

        # Teste 1: Query simples
        result = await transaction_db.fetchval("SELECT version()")
        print(f"✅ PostgreSQL: {result[:50]}...")

        # Teste 2: Query com parâmetros (sem prepared statements)
        result = await transaction_db.fetchval("SELECT $1::text", "Teste pgBouncer")
        print(f"✅ Parâmetro: {result}")

        # Teste 3: Múltiplas queries
        for i in range(3):
            result = await transaction_db.fetchval(f"SELECT 'Query {i+1}'")
            print(f"✅ {result}")

        print("\n🎉 SUCESSO: pgBouncer transaction mode funcionando!")
        return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

    finally:
        await transaction_db.disconnect()


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_transaction_mode())
