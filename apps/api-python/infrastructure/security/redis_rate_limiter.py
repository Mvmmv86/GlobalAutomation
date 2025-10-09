"""Redis-based Rate Limiter for distributed systems"""

import time
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

import redis
import structlog
from fastapi import Request

logger = structlog.get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    max_requests: int
    window_seconds: int
    block_duration: int = 300  # 5 minutes default


class RedisRateLimiter:
    """
    Distributed rate limiter using Redis.
    Uses sliding window algorithm for accurate rate limiting.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "ratelimit"
    ):
        """
        Initialize Redis rate limiter.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for Redis keys
        """
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis rate limiter initialized", redis_url=redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise

        self.key_prefix = key_prefix

    def _get_key(self, identifier: str, scope: str = "global") -> str:
        """Generate Redis key for rate limiting"""
        return f"{self.key_prefix}:{scope}:{identifier}"

    def _get_block_key(self, identifier: str, scope: str = "global") -> str:
        """Generate Redis key for blocking"""
        return f"{self.key_prefix}:block:{scope}:{identifier}"

    async def check_rate_limit(
        self,
        identifier: str,
        config: RateLimitConfig,
        scope: str = "global"
    ) -> Tuple[bool, Dict]:
        """
        Check if request should be rate limited.

        Args:
            identifier: Unique identifier (IP, user_id, webhook_id, etc.)
            config: Rate limit configuration
            scope: Scope for rate limiting (e.g., "webhook", "api", "login")

        Returns:
            Tuple of (allowed, info_dict)
        """
        try:
            now = time.time()
            key = self._get_key(identifier, scope)
            block_key = self._get_block_key(identifier, scope)

            # Check if client is blocked
            blocked_until = self.redis_client.get(block_key)
            if blocked_until and float(blocked_until) > now:
                retry_after = int(float(blocked_until) - now)
                return False, {
                    "error": "Rate limit exceeded - temporarily blocked",
                    "retry_after": retry_after,
                    "blocked_until": float(blocked_until)
                }

            # Use sorted set for sliding window
            window_start = now - config.window_seconds

            # Remove old entries outside the window
            self.redis_client.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            current_count = self.redis_client.zcard(key)

            # Check if limit exceeded
            if current_count >= config.max_requests:
                # Block the client
                block_until = now + config.block_duration
                self.redis_client.setex(
                    block_key,
                    config.block_duration,
                    str(block_until)
                )

                logger.warning(
                    "Rate limit exceeded",
                    identifier=identifier,
                    scope=scope,
                    requests=current_count,
                    limit=config.max_requests,
                    window=config.window_seconds
                )

                return False, {
                    "error": "Rate limit exceeded",
                    "requests": current_count,
                    "limit": config.max_requests,
                    "window": config.window_seconds,
                    "retry_after": config.block_duration
                }

            # Add current request
            self.redis_client.zadd(key, {str(now): now})

            # Set expiry on the key to prevent memory leaks
            self.redis_client.expire(key, config.window_seconds + 60)

            # Calculate remaining requests
            remaining = config.max_requests - current_count - 1
            reset_time = int(now + config.window_seconds)

            return True, {
                "requests_remaining": remaining,
                "reset_time": reset_time,
                "limit": config.max_requests,
                "window": config.window_seconds
            }

        except redis.RedisError as e:
            logger.error(
                "Redis error in rate limiter",
                error=str(e),
                identifier=identifier,
                scope=scope
            )
            # Fail open - allow request if Redis is unavailable
            return True, {"error": "Rate limiter unavailable"}
        except Exception as e:
            logger.error(
                "Unexpected error in rate limiter",
                error=str(e),
                identifier=identifier,
                scope=scope
            )
            # Fail open
            return True, {"error": "Rate limiter error"}

    async def reset_rate_limit(self, identifier: str, scope: str = "global"):
        """Reset rate limit for an identifier"""
        try:
            key = self._get_key(identifier, scope)
            block_key = self._get_block_key(identifier, scope)

            self.redis_client.delete(key)
            self.redis_client.delete(block_key)

            logger.info("Rate limit reset", identifier=identifier, scope=scope)
        except Exception as e:
            logger.error("Error resetting rate limit", error=str(e))

    async def get_rate_limit_info(
        self,
        identifier: str,
        config: RateLimitConfig,
        scope: str = "global"
    ) -> Dict:
        """Get current rate limit info for an identifier"""
        try:
            now = time.time()
            key = self._get_key(identifier, scope)
            block_key = self._get_block_key(identifier, scope)

            # Check if blocked
            blocked_until = self.redis_client.get(block_key)
            is_blocked = blocked_until and float(blocked_until) > now

            # Count requests in window
            window_start = now - config.window_seconds
            self.redis_client.zremrangebyscore(key, 0, window_start)
            current_count = self.redis_client.zcard(key)

            return {
                "identifier": identifier,
                "scope": scope,
                "requests_used": current_count,
                "requests_limit": config.max_requests,
                "requests_remaining": max(0, config.max_requests - current_count),
                "window_seconds": config.window_seconds,
                "is_blocked": is_blocked,
                "blocked_until": float(blocked_until) if blocked_until else None,
                "reset_time": int(now + config.window_seconds)
            }
        except Exception as e:
            logger.error("Error getting rate limit info", error=str(e))
            return {"error": str(e)}

    def close(self):
        """Close Redis connection"""
        try:
            self.redis_client.close()
            logger.info("Redis rate limiter connection closed")
        except Exception as e:
            logger.error("Error closing Redis connection", error=str(e))


def get_client_identifier(request: Request) -> str:
    """
    Extract unique identifier from request.
    Priority: user_id > api_key > IP address
    """
    # Try to get user_id from request state (if authenticated)
    user_id = getattr(request.state, 'user_id', None)
    if user_id:
        return f"user:{user_id}"

    # Try to get API key from headers
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # Use hash of API key to avoid storing sensitive data
        import hashlib
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        return f"apikey:{key_hash}"

    # Fall back to IP address
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip() or
        request.headers.get("x-real-ip") or
        request.client.host if request.client else "unknown"
    )

    return f"ip:{client_ip}"
