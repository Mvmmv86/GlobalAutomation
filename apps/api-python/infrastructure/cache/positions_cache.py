"""
Cache Layer for Positions Data

Implements TTL-based caching for positions data with automatic invalidation
on order creation/modification. This reduces redundant API calls while ensuring
data freshness for critical trading operations.

Security: Cache only structural data (positions metadata), never prices.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with TTL and metadata."""
    data: Any
    created_at: datetime
    ttl_seconds: int
    hit_count: int = 0

    def is_valid(self) -> bool:
        """Check if cache entry is still valid based on TTL."""
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age < self.ttl_seconds

    def increment_hit(self) -> None:
        """Increment cache hit counter for metrics."""
        self.hit_count += 1


class PositionsCache:
    """
    Thread-safe cache for positions data with automatic TTL expiration.

    Design decisions:
    - TTL of 3s: Balance between freshness and performance
    - User-scoped keys: Prevent data leakage between users
    - Automatic cleanup: Remove stale entries every 60s
    - Metrics: Track hits/misses for monitoring
    """

    def __init__(self, default_ttl: int = 3):
        """
        Initialize cache with default TTL.

        Args:
            default_ttl: Default time-to-live in seconds (default: 3s)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._default_ttl = default_ttl

        # Metrics
        self._hits = 0
        self._misses = 0
        self._invalidations = 0

        logger.info(f"PositionsCache initialized with TTL={default_ttl}s")

    def _make_key(self, user_id: int, key_type: str) -> str:
        """
        Generate cache key scoped to user and data type.

        Args:
            user_id: User identifier
            key_type: Type of cached data (e.g., 'positions', 'positions_metrics')

        Returns:
            Scoped cache key
        """
        return f"user:{user_id}:{key_type}"

    async def get(self, user_id: int, key_type: str) -> Optional[Any]:
        """
        Retrieve cached data if valid.

        Args:
            user_id: User identifier
            key_type: Type of cached data

        Returns:
            Cached data if valid, None otherwise
        """
        async with self._lock:
            key = self._make_key(user_id, key_type)
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                logger.debug(f"Cache MISS: {key}")
                return None

            if not entry.is_valid():
                # Remove expired entry
                del self._cache[key]
                self._misses += 1
                logger.debug(f"Cache EXPIRED: {key}")
                return None

            # Cache hit
            entry.increment_hit()
            self._hits += 1
            logger.debug(f"Cache HIT: {key} (hits={entry.hit_count})")
            return entry.data

    async def set(self, user_id: int, key_type: str, data: Any, ttl: Optional[int] = None) -> None:
        """
        Store data in cache with TTL.

        Args:
            user_id: User identifier
            key_type: Type of cached data
            data: Data to cache
            ttl: Custom TTL in seconds (uses default if not provided)
        """
        async with self._lock:
            key = self._make_key(user_id, key_type)
            ttl = ttl or self._default_ttl

            entry = CacheEntry(
                data=data,
                created_at=datetime.utcnow(),
                ttl_seconds=ttl
            )

            self._cache[key] = entry
            logger.debug(f"Cache SET: {key} (TTL={ttl}s)")

    async def invalidate(self, user_id: int, key_type: Optional[str] = None) -> int:
        """
        Invalidate cache entries for a user.

        Args:
            user_id: User identifier
            key_type: Specific key type to invalidate (invalidates all user keys if None)

        Returns:
            Number of entries invalidated
        """
        async with self._lock:
            if key_type:
                # Invalidate specific key
                key = self._make_key(user_id, key_type)
                if key in self._cache:
                    del self._cache[key]
                    self._invalidations += 1
                    logger.info(f"Cache INVALIDATED: {key}")
                    return 1
                return 0
            else:
                # Invalidate all keys for user
                prefix = f"user:{user_id}:"
                keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]

                for k in keys_to_remove:
                    del self._cache[k]

                count = len(keys_to_remove)
                self._invalidations += count
                logger.info(f"Cache INVALIDATED: {count} entries for user {user_id}")
                return count

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.warning(f"Cache CLEARED: {count} entries removed")

    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if not entry.is_valid()
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info(f"Cache CLEANUP: {len(expired_keys)} expired entries removed")

            return len(expired_keys)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get cache performance metrics.

        Returns:
            Dictionary with hits, misses, hit_rate, size, invalidations
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "size": len(self._cache),
            "invalidations": self._invalidations,
            "total_requests": total_requests
        }

    def reset_metrics(self) -> None:
        """Reset all metrics counters."""
        self._hits = 0
        self._misses = 0
        self._invalidations = 0
        logger.info("Cache metrics reset")


# Global singleton instance
_positions_cache: Optional[PositionsCache] = None


def get_positions_cache() -> PositionsCache:
    """
    Get or create global positions cache instance.

    Returns:
        Singleton PositionsCache instance
    """
    global _positions_cache
    if _positions_cache is None:
        _positions_cache = PositionsCache(default_ttl=3)
    return _positions_cache


async def start_cache_cleanup_task():
    """
    Background task to cleanup expired cache entries every 60s.
    Should be started on application startup.
    """
    cache = get_positions_cache()

    while True:
        try:
            await asyncio.sleep(60)  # Cleanup every 60 seconds
            removed = await cache.cleanup_expired()

            # Log metrics periodically
            metrics = cache.get_metrics()
            logger.info(f"Cache metrics: {metrics}")

        except Exception as e:
            logger.error(f"Error in cache cleanup task: {e}", exc_info=True)
