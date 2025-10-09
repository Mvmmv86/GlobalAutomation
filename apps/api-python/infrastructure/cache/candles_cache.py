"""
Candles Cache Module
High-performance cache for market candles data with intelligent TTL
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class CandlesCache:
    """
    Cache específico para dados de candles com TTL inteligente baseado no intervalo.

    Intervalos menores (1m-5m) = TTL curto (30s)
    Intervalos médios (15m-1h) = TTL médio (2min)
    Intervalos maiores (4h-1d) = TTL longo (5min)
    """

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
            "cached_bytes": 0
        }

    def _get_cache_key(self, symbol: str, interval: str, limit: int) -> str:
        """Generate unique cache key"""
        return f"candles:{symbol}:{interval}:{limit}"

    def _get_ttl_seconds(self, interval: str) -> int:
        """
        Get TTL based on interval - shorter intervals need fresher data
        Historical data doesn't change, so we can cache longer!
        """
        short_intervals = ['1m', '3m', '5m']
        medium_intervals = ['15m', '30m', '1h']
        long_intervals = ['2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']

        if interval in short_intervals:
            return 60  # 1 minute for scalping (was 30s)
        elif interval in medium_intervals:
            return 300  # 5 minutes for day trading (was 2min)
        elif interval in long_intervals:
            return 600  # 10 minutes for swing trading (was 5min)
        else:
            return 180  # Default 3 minutes (was 1min)

    async def get(self, symbol: str, interval: str, limit: int) -> Optional[Dict[str, Any]]:
        """Get cached candles data"""
        async with self._lock:
            self._stats["total_requests"] += 1

            cache_key = self._get_cache_key(symbol, interval, limit)

            if cache_key not in self._cache:
                self._stats["misses"] += 1
                logger.info(f"❌ CACHE MISS: {cache_key}")
                return None

            entry = self._cache[cache_key]

            # Check if expired
            if datetime.utcnow() > entry["expires_at"]:
                del self._cache[cache_key]
                self._stats["misses"] += 1
                logger.info(f"⏰ CACHE EXPIRED: {cache_key}")
                return None

            self._stats["hits"] += 1
            hit_rate = (self._stats["hits"] / self._stats["total_requests"]) * 100
            logger.info(f"✅ CACHE HIT: {cache_key} (Hit Rate: {hit_rate:.1f}%)")

            return entry["data"]

    async def set(self, symbol: str, interval: str, limit: int, data: Dict[str, Any]):
        """Cache candles data with intelligent TTL"""
        async with self._lock:
            cache_key = self._get_cache_key(symbol, interval, limit)
            ttl_seconds = self._get_ttl_seconds(interval)
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

            # Calculate approximate size
            data_size = len(json.dumps(data))

            self._cache[cache_key] = {
                "data": data,
                "expires_at": expires_at,
                "cached_at": datetime.utcnow(),
                "size_bytes": data_size
            }

            self._stats["cached_bytes"] = sum(
                entry.get("size_bytes", 0)
                for entry in self._cache.values()
            )

            logger.info(
                f"💾 CACHE SET: {cache_key} "
                f"(TTL: {ttl_seconds}s, Size: {data_size/1024:.1f}KB, "
                f"Total Cache: {self._stats['cached_bytes']/1024:.1f}KB)"
            )

    async def invalidate(self, symbol: Optional[str] = None):
        """Invalidate cache for specific symbol or all"""
        async with self._lock:
            if symbol:
                # Invalidate specific symbol
                keys_to_delete = [
                    key for key in self._cache.keys()
                    if key.startswith(f"candles:{symbol}:")
                ]
                for key in keys_to_delete:
                    del self._cache[key]
                    logger.info(f"🗑️ CACHE INVALIDATED: {key}")
                return len(keys_to_delete)
            else:
                # Invalidate all
                count = len(self._cache)
                self._cache.clear()
                self._stats["cached_bytes"] = 0
                logger.info(f"🗑️ CACHE CLEARED: {count} entries")
                return count

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        total = self._stats["total_requests"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": round(hit_rate, 2),
            "total_requests": total,
            "cached_entries": len(self._cache),
            "cached_kb": round(self._stats["cached_bytes"] / 1024, 2)
        }

    async def cleanup_expired(self):
        """Remove expired entries"""
        async with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry["expires_at"]
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")


# Global singleton instance
candles_cache = CandlesCache()


async def start_candles_cache_cleanup():
    """Background task to cleanup expired entries every 60 seconds"""
    while True:
        try:
            await asyncio.sleep(60)
            await candles_cache.cleanup_expired()
        except Exception as e:
            logger.error(f"Error in candles cache cleanup: {e}")
            await asyncio.sleep(60)