"""Redis connection and service management"""

import redis.asyncio as redis
import structlog
from typing import Optional

from ..config.settings import get_settings


logger = structlog.get_logger()


class RedisManager:
    """Redis connection manager"""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    async def connect(self):
        """Initialize Redis connection"""
        settings = get_settings()

        try:
            # Create Redis connection
            self._redis = redis.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
            )

            # Test connection
            await self._redis.ping()

            logger.info("Redis connection established")

        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise

    async def disconnect(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")

    def get_client(self) -> redis.Redis:
        """Get Redis client"""
        if not self._redis:
            raise RuntimeError("Redis not initialized. Call connect() first.")
        return self._redis


# Global Redis manager
redis_manager = RedisManager()


async def get_redis_client() -> redis.Redis:
    """Dependency to get Redis client"""
    return redis_manager.get_client()
