"""Alembic environment configuration for async SQLAlchemy"""

import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config


# Load .env file manually for Alembic
def load_env_file():
    """Load .env file manually since Alembic doesn't use pydantic-settings"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value


# Load environment variables
load_env_file()

# Import all models to ensure they are registered with SQLAlchemy
from infrastructure.database.models.base import Base

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def get_database_url() -> str:
    """Get database URL from environment or config"""
    # For migrations, use DIRECT_URL (Supabase direct connection)
    # This bypasses pooling and uses direct PostgreSQL connection
    direct_url = os.getenv("DIRECT_URL")
    if direct_url:
        return direct_url

    # Fallback to DATABASE_URL but convert async to sync for Alembic
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Convert async URL to sync for Alembic
        if database_url.startswith("postgresql+asyncpg://"):
            return database_url.replace("postgresql+asyncpg://", "postgresql://")
        return database_url

    # Try environment-specific config
    env = os.getenv("ENV", "dev")
    if env == "test":
        try:
            return config.get_section_option("test", "sqlalchemy.url")
        except:
            pass
    elif env == "prod":
        return os.getenv("DATABASE_URL", "")

    # Default to main config
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with database connection"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode"""
    import ssl
    import os

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    # Configure SSL for Supabase (same as main app)
    no_verify = os.getenv("DB_SSL_NO_VERIFY", "false").lower() == "true"

    connect_args = {}
    if no_verify:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_ctx

    # For pgBouncer compatibility
    connect_args["statement_cache_size"] = 0
    connect_args["server_settings"] = {"application_name": "alembic_migrations"}

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    asyncio.run(run_async_migrations())


# Determine if we're running in offline or online mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
