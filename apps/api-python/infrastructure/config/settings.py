"""Application settings using Pydantic Settings"""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file() -> str | None:
    """
    Determina qual arquivo .env usar baseado no ambiente.

    IMPORTANTE para DigitalOcean:
    - Se ENV=production está definido no sistema, NÃO carrega nenhum arquivo .env
    - Isso garante que as Environment Variables do App Platform sejam usadas
    - Em desenvolvimento local, carrega .env normalmente
    """
    env = os.getenv("ENV", "development")

    if env == "production":
        # Em produção: NÃO carregar arquivo .env
        # Usar apenas variáveis de ambiente do sistema (DigitalOcean App Platform)
        return None

    # Em desenvolvimento: usar .env local
    return ".env"


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    IMPORTANTE - Pydantic V2:
    - Usar validation_alias para mapear nomes de variáveis de ambiente
    - O env_file tem PRIORIDADE sobre variáveis de ambiente do sistema
    - Por isso em produção definimos env_file=None
    """

    # App config
    app_name: str = "TradingView Gateway API"
    version: str = "1.0.0"
    environment: str = Field(default="development", validation_alias="ENV")
    debug: bool = Field(default=True, validation_alias="DEBUG")
    port: int = Field(default=8000, validation_alias="PORT")

    # Security
    secret_key: str = Field(..., validation_alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # TradingView
    tv_webhook_secret: str = Field(..., validation_alias="TV_WEBHOOK_SECRET")

    # Database
    database_url: str = Field(..., validation_alias="DATABASE_URL")
    database_echo: bool = Field(default=False, validation_alias="DATABASE_ECHO")
    db_pool_size: int = Field(default=10, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, validation_alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, validation_alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=3600, validation_alias="DB_POOL_RECYCLE")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379", validation_alias="REDIS_URL")
    redis_max_connections: int = Field(default=10, validation_alias="REDIS_MAX_CONNECTIONS")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
        validation_alias="CORS_ORIGINS"
    )

    # Security
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        validation_alias="ALLOWED_HOSTS"
    )

    # Rate limiting
    rate_limit_per_minute: int = Field(default=100, validation_alias="RATE_LIMIT_PER_MINUTE")
    webhook_rate_limit_per_minute: int = Field(
        default=200, validation_alias="WEBHOOK_RATE_LIMIT_PER_MINUTE"
    )
    authenticated_rate_limit_per_minute: int = Field(
        default=500, validation_alias="AUTH_RATE_LIMIT_PER_MINUTE"
    )

    # Encryption
    encryption_key: str = Field(..., validation_alias="ENCRYPTION_KEY")

    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, validation_alias="SENTRY_DSN")

    # Queue
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", validation_alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1", validation_alias="CELERY_RESULT_BACKEND"
    )

    model_config = SettingsConfigDict(
        env_file=get_env_file(),  # None em produção, ".env" em desenvolvimento
        case_sensitive=False,
        extra="ignore",  # Ignorar campos extras do .env
    )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
