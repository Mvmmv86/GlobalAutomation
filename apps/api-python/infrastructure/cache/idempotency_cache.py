"""
Idempotency Cache - In-memory cache for preventing duplicate requests

This module provides a simple in-memory cache with TTL for idempotency.
Can be easily replaced with Redis for production scaling.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger(__name__)


class IdempotencyCache:
    """
    Thread-safe in-memory cache with TTL for idempotency keys

    Features:
    - Automatic expiration (TTL)
    - Thread-safe operations
    - JSON serialization
    - Easy migration to Redis
    """

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = None  # Será inicializado quando event loop estiver disponível
        self._cleanup_task = None

    def _ensure_initialized(self):
        """Ensure lock is initialized (called lazily when event loop is available)"""
        if self._lock is None:
            self._lock = asyncio.Lock()
            # Start cleanup task only once
            if self._cleanup_task is None:
                self._cleanup_task = asyncio.create_task(self._cleanup_expired())

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached value by key

        Args:
            key: Idempotency key

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        self._ensure_initialized()
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]

            # Check expiration
            if datetime.utcnow() > entry['expires_at']:
                del self._cache[key]
                logger.debug(f"Cache entry expired: {key}")
                return None

            logger.info(f"✅ Cache HIT: {key}")
            return entry['value']

    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 60):
        """
        Set cached value with TTL

        Args:
            key: Idempotency key
            value: Value to cache (must be JSON-serializable)
            ttl_seconds: Time to live in seconds (default: 60)
        """
        self._ensure_initialized()
        async with self._lock:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': datetime.utcnow()
            }

            logger.info(f"✅ Cache SET: {key} (TTL: {ttl_seconds}s)")

    async def delete(self, key: str):
        """Delete cached entry"""
        self._ensure_initialized()
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.info(f"🗑️ Cache DELETE: {key}")

    async def clear(self):
        """Clear all cache entries"""
        self._ensure_initialized()
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"🗑️ Cache CLEARED: {count} entries removed")

    async def _cleanup_expired(self):
        """Background task to remove expired entries"""
        while True:
            try:
                await asyncio.sleep(30)  # Run every 30 seconds

                if self._lock is None:
                    continue

                async with self._lock:
                    now = datetime.utcnow()
                    expired_keys = [
                        key for key, entry in self._cache.items()
                        if now > entry['expires_at']
                    ]

                    for key in expired_keys:
                        del self._cache[key]

                    if expired_keys:
                        logger.info(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")

            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'total_entries': len(self._cache),
            'entries': [
                {
                    'key': key[:20] + '...' if len(key) > 20 else key,
                    'created_at': entry['created_at'].isoformat(),
                    'expires_at': entry['expires_at'].isoformat(),
                    'ttl_remaining': (entry['expires_at'] - datetime.utcnow()).total_seconds()
                }
                for key, entry in self._cache.items()
            ]
        }


# Global singleton instance
idempotency_cache = IdempotencyCache()


# ==================== Helper Functions ====================

async def check_idempotency(key: str) -> Optional[Dict[str, Any]]:
    """
    Check if request with this idempotency key was already processed

    Args:
        key: Idempotency key (usually from X-Idempotency-Key header)

    Returns:
        Cached response if exists, None otherwise
    """
    if not key:
        return None

    return await idempotency_cache.get(f"idempotency:{key}")


async def cache_response(key: str, response: Dict[str, Any], ttl: int = 60):
    """
    Cache response for idempotency

    Args:
        key: Idempotency key
        response: Response to cache
        ttl: Time to live in seconds
    """
    if not key:
        return

    await idempotency_cache.set(f"idempotency:{key}", response, ttl)
