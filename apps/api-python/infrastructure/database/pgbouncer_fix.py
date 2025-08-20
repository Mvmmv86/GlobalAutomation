"""
Configuração específica para pgBouncer/Supabase pooler
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool
import structlog

logger = structlog.get_logger()


def create_pgbouncer_engine(database_url: str, debug: bool = False):
    """
    Cria engine otimizada para pgBouncer/Supabase pooler
    que não suporta prepared statements
    """

    # Remover prepared statements completamente
    connect_args = {
        "server_settings": {"jit": "off"},  # Desabilitar JIT que pode causar problemas
        "command_timeout": 60,
    }

    # Se estiver usando SSL (Supabase)
    if "sslmode" in database_url:
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context

    # Criar engine sem prepared statements
    engine = create_async_engine(
        database_url,
        # Não usar pool, deixar pgBouncer gerenciar
        poolclass=NullPool,
        echo=debug,
        connect_args=connect_args,
        # Desabilitar cache de queries compiladas
        query_cache_size=0,
        # Configurações para evitar prepared statements
        pool_pre_ping=False,  # Não fazer ping (pode criar prepared statement)
        # Evitar prepared statements no asyncpg
        execution_options={
            "no_autoflush": False,
            "synchronize_session": False,
        },
    )

    # Configurar evento para desabilitar prepared statements por conexão
    @engine.dialect.get_asyncio_connection_from_pool_slot.connect
    def receive_do_connect(asyncio_connection, cargs, cparams):
        """Desabilitar prepared statements em cada conexão"""
        # Definir statement_cache_size=0 diretamente no asyncpg
        if "prepared_statement_cache_size" not in cparams:
            cparams["prepared_statement_cache_size"] = 0
        if "statement_cache_size" not in cparams:
            cparams["statement_cache_size"] = 0

    return engine
