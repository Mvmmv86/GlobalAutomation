"""Application settings using Pydantic Settings"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # App config
    app_name: str = "TradingView Gateway API"
    version: str = "1.0.0"
    environment: str = Field(default="development", env="ENV")
    debug: bool = Field(default=True, env="DEBUG")
    port: int = Field(default=8000, env="PORT")

    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # TradingView
    tv_webhook_secret: str = Field(..., env="TV_WEBHOOK_SECRET")

    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_max_connections: int = Field(default=10, env="REDIS_MAX_CONNECTIONS")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"], env="CORS_ORIGINS"
    )

    # Security
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS"
    )

    # Rate limiting
    rate_limit_per_minute: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    webhook_rate_limit_per_minute: int = Field(
        default=200, env="WEBHOOK_RATE_LIMIT_PER_MINUTE"
    )
    authenticated_rate_limit_per_minute: int = Field(
        default=500, env="AUTH_RATE_LIMIT_PER_MINUTE"
    )

    # Encryption
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")

    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")

    # Queue
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1", env="CELERY_RESULT_BACKEND"
    )

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",  # Ignorar campos extras do .env
    }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
