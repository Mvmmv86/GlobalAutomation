"""Distributed Lock using Redis for preventing race conditions"""

import time
import uuid
from typing import Optional
from contextlib import asynccontextmanager

import redis
import structlog

logger = structlog.get_logger(__name__)


class DistributedLock:
    """
    Distributed lock implementation using Redis.

    Prevents race conditions in distributed systems by ensuring
    only one process can execute a critical section at a time.

    Uses Redis SET with NX (Not eXists) and EX (EXpire) options.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "lock"
    ):
        """
        Initialize distributed lock.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for lock keys in Redis
        """
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.redis_client.ping()
            logger.info("Distributed lock initialized", redis_url=redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis for distributed lock", error=str(e))
            raise

        self.key_prefix = key_prefix

    def _get_lock_key(self, resource: str) -> str:
        """Generate Redis key for lock"""
        return f"{self.key_prefix}:{resource}"

    async def acquire(
        self,
        resource: str,
        ttl: int = 30,
        timeout: Optional[int] = None,
        retry_interval: float = 0.1
    ) -> Optional[str]:
        """
        Acquire a distributed lock.

        Args:
            resource: Resource identifier to lock (e.g., "order:BTCUSDT", "user:123")
            ttl: Time to live for the lock in seconds (prevents deadlocks)
            timeout: Maximum time to wait for lock acquisition (None = wait forever)
            retry_interval: Time to wait between retry attempts in seconds

        Returns:
            Lock token (UUID) if acquired, None if failed
        """
        lock_key = self._get_lock_key(resource)
        lock_token = str(uuid.uuid4())  # Unique token to identify this lock holder
        start_time = time.time()

        while True:
            try:
                # Try to acquire lock using SET NX (Not eXists) with expiration
                acquired = self.redis_client.set(
                    lock_key,
                    lock_token,
                    nx=True,  # Only set if key doesn't exist
                    ex=ttl     # Set expiration time
                )

                if acquired:
                    logger.debug(
                        "Lock acquired",
                        resource=resource,
                        token=lock_token[:8],
                        ttl=ttl
                    )
                    return lock_token

                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        logger.warning(
                            "Lock acquisition timeout",
                            resource=resource,
                            timeout=timeout,
                            elapsed=elapsed
                        )
                        return None

                # Wait before retrying
                await self._async_sleep(retry_interval)

            except redis.RedisError as e:
                logger.error(
                    "Redis error while acquiring lock",
                    error=str(e),
                    resource=resource
                )
                return None
            except Exception as e:
                logger.error(
                    "Unexpected error while acquiring lock",
                    error=str(e),
                    resource=resource
                )
                return None

    async def release(self, resource: str, lock_token: str) -> bool:
        """
        Release a distributed lock.

        Args:
            resource: Resource identifier
            lock_token: Token returned by acquire()

        Returns:
            True if lock was released, False otherwise
        """
        lock_key = self._get_lock_key(resource)

        try:
            # Lua script to ensure we only delete our own lock
            # This prevents accidentally releasing another process's lock
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """

            result = self.redis_client.eval(lua_script, 1, lock_key, lock_token)

            if result:
                logger.debug(
                    "Lock released",
                    resource=resource,
                    token=lock_token[:8]
                )
                return True
            else:
                logger.warning(
                    "Failed to release lock (token mismatch or already released)",
                    resource=resource,
                    token=lock_token[:8]
                )
                return False

        except redis.RedisError as e:
            logger.error(
                "Redis error while releasing lock",
                error=str(e),
                resource=resource
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error while releasing lock",
                error=str(e),
                resource=resource
            )
            return False

    async def extend(
        self,
        resource: str,
        lock_token: str,
        additional_ttl: int = 30
    ) -> bool:
        """
        Extend the TTL of an existing lock.

        Args:
            resource: Resource identifier
            lock_token: Token returned by acquire()
            additional_ttl: Additional time in seconds

        Returns:
            True if lock was extended, False otherwise
        """
        lock_key = self._get_lock_key(resource)

        try:
            # Lua script to extend TTL only if we own the lock
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """

            result = self.redis_client.eval(
                lua_script,
                1,
                lock_key,
                lock_token,
                additional_ttl
            )

            if result:
                logger.debug(
                    "Lock extended",
                    resource=resource,
                    token=lock_token[:8],
                    additional_ttl=additional_ttl
                )
                return True
            else:
                logger.warning(
                    "Failed to extend lock (token mismatch)",
                    resource=resource,
                    token=lock_token[:8]
                )
                return False

        except Exception as e:
            logger.error(
                "Error extending lock",
                error=str(e),
                resource=resource
            )
            return False

    @asynccontextmanager
    async def lock_context(
        self,
        resource: str,
        ttl: int = 30,
        timeout: Optional[int] = 10
    ):
        """
        Context manager for distributed lock.

        Usage:
            async with lock.lock_context("order:BTCUSDT"):
                # Critical section
                await place_order()

        Args:
            resource: Resource identifier to lock
            ttl: Time to live for the lock
            timeout: Maximum time to wait for lock

        Raises:
            RuntimeError: If lock cannot be acquired
        """
        lock_token = await self.acquire(resource, ttl=ttl, timeout=timeout)

        if lock_token is None:
            raise RuntimeError(f"Failed to acquire lock for resource: {resource}")

        try:
            yield lock_token
        finally:
            await self.release(resource, lock_token)

    async def is_locked(self, resource: str) -> bool:
        """
        Check if a resource is currently locked.

        Args:
            resource: Resource identifier

        Returns:
            True if locked, False otherwise
        """
        try:
            lock_key = self._get_lock_key(resource)
            return self.redis_client.exists(lock_key) > 0
        except Exception as e:
            logger.error("Error checking lock status", error=str(e))
            return False

    async def get_lock_ttl(self, resource: str) -> Optional[int]:
        """
        Get remaining TTL for a lock.

        Args:
            resource: Resource identifier

        Returns:
            Remaining TTL in seconds, or None if not locked
        """
        try:
            lock_key = self._get_lock_key(resource)
            ttl = self.redis_client.ttl(lock_key)

            # -2 means key doesn't exist, -1 means no expiration
            if ttl < 0:
                return None

            return ttl
        except Exception as e:
            logger.error("Error getting lock TTL", error=str(e))
            return None

    async def force_release(self, resource: str):
        """
        Force release a lock (use with caution!).

        This should only be used in emergency situations or cleanup.

        Args:
            resource: Resource identifier
        """
        try:
            lock_key = self._get_lock_key(resource)
            result = self.redis_client.delete(lock_key)

            if result:
                logger.warning(
                    "Lock force released",
                    resource=resource
                )
            else:
                logger.debug(
                    "Lock already released",
                    resource=resource
                )

        except Exception as e:
            logger.error("Error force releasing lock", error=str(e))

    async def _async_sleep(self, seconds: float):
        """Async sleep helper"""
        import asyncio
        await asyncio.sleep(seconds)

    def close(self):
        """Close Redis connection"""
        try:
            self.redis_client.close()
            logger.info("Distributed lock connection closed")
        except Exception as e:
            logger.error("Error closing Redis connection", error=str(e))
