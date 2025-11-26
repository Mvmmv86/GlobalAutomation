"""Replay Attack Prevention using Redis"""

import time
import hashlib
from typing import Optional, Tuple

import redis
import structlog

logger = structlog.get_logger(__name__)


class ReplayAttackPrevention:
    """
    Prevent replay attacks by tracking request nonces and timestamps.

    Uses Redis to store:
    1. Nonces (unique request IDs) with expiration
    2. Request signatures with timestamps

    Protection mechanisms:
    - Timestamp validation (reject old requests)
    - Nonce validation (reject duplicate requests)
    - Signature validation (ensure request hasn't been modified)
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        key_prefix: str = "replay_prevention",
        max_timestamp_drift: int = 300,  # 5 minutes
        nonce_ttl: int = 3600  # 1 hour
    ):
        """
        Initialize replay attack prevention.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for Redis keys
            max_timestamp_drift: Maximum allowed time drift in seconds
            nonce_ttl: Time to live for nonces in seconds
        """
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.redis_client.ping()
            logger.info("Replay attack prevention initialized", redis_url=redis_url)
        except Exception as e:
            logger.error("Failed to connect to Redis for replay prevention", error=str(e))
            raise

        self.key_prefix = key_prefix
        self.max_timestamp_drift = max_timestamp_drift
        self.nonce_ttl = nonce_ttl

    def _get_nonce_key(self, nonce: str) -> str:
        """Generate Redis key for nonce"""
        return f"{self.key_prefix}:nonce:{nonce}"

    def _get_signature_key(self, signature: str) -> str:
        """Generate Redis key for signature"""
        return f"{self.key_prefix}:signature:{signature}"

    def _validate_timestamp(self, timestamp: int) -> Tuple[bool, Optional[str]]:
        """
        Validate request timestamp.

        Args:
            timestamp: Unix timestamp from request

        Returns:
            Tuple of (is_valid, error_message)
        """
        now = int(time.time())
        time_diff = abs(now - timestamp)

        if time_diff > self.max_timestamp_drift:
            error_msg = (
                f"Request timestamp too old or in future. "
                f"Drift: {time_diff}s, Max allowed: {self.max_timestamp_drift}s"
            )
            logger.warning(
                "Invalid timestamp",
                timestamp=timestamp,
                current_time=now,
                drift=time_diff,
                max_drift=self.max_timestamp_drift
            )
            return False, error_msg

        return True, None

    def _validate_nonce(self, nonce: str) -> Tuple[bool, Optional[str]]:
        """
        Validate nonce (ensure it hasn't been used before).

        Args:
            nonce: Unique request identifier

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not nonce or len(nonce) < 16:
            return False, "Nonce must be at least 16 characters"

        nonce_key = self._get_nonce_key(nonce)

        # Check if nonce exists
        if self.redis_client.exists(nonce_key):
            logger.warning("Duplicate nonce detected", nonce=nonce)
            return False, "Duplicate request detected (nonce already used)"

        # Store nonce with TTL
        self.redis_client.setex(nonce_key, self.nonce_ttl, "1")

        return True, None

    def _compute_signature(
        self,
        webhook_id: str,
        timestamp: int,
        nonce: str,
        payload: str
    ) -> str:
        """
        Compute request signature for validation.

        Args:
            webhook_id: Webhook identifier
            timestamp: Unix timestamp
            nonce: Unique request ID
            payload: Request payload (JSON string)

        Returns:
            Hex digest of signature
        """
        # Combine all elements
        message = f"{webhook_id}:{timestamp}:{nonce}:{payload}"

        # Compute SHA256 hash
        signature = hashlib.sha256(message.encode()).hexdigest()

        return signature

    def _validate_signature(
        self,
        signature: str,
        webhook_id: str,
        timestamp: int,
        nonce: str,
        payload: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate request signature.

        Args:
            signature: Provided signature
            webhook_id: Webhook identifier
            timestamp: Unix timestamp
            nonce: Unique request ID
            payload: Request payload

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Compute expected signature
        expected_signature = self._compute_signature(
            webhook_id, timestamp, nonce, payload
        )

        # Compare signatures (constant-time comparison to prevent timing attacks)
        import hmac
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning(
                "Invalid signature",
                provided=signature[:16],  # Log only first 16 chars
                expected=expected_signature[:16]
            )
            return False, "Invalid request signature"

        # Check if signature was used before
        signature_key = self._get_signature_key(signature)
        if self.redis_client.exists(signature_key):
            logger.warning("Duplicate signature detected", signature=signature[:16])
            return False, "Duplicate request detected (signature already used)"

        # Store signature with TTL
        self.redis_client.setex(signature_key, self.nonce_ttl, "1")

        return True, None

    async def validate_request(
        self,
        webhook_id: str,
        timestamp: int,
        nonce: str,
        payload: str,
        signature: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate request against replay attacks.

        Args:
            webhook_id: Webhook identifier
            timestamp: Unix timestamp from request
            nonce: Unique request identifier
            payload: Request payload (JSON string)
            signature: Optional request signature

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # 1. Validate timestamp
            timestamp_valid, error = self._validate_timestamp(timestamp)
            if not timestamp_valid:
                return False, error

            # 2. Validate nonce
            nonce_valid, error = self._validate_nonce(nonce)
            if not nonce_valid:
                return False, error

            # 3. Validate signature (if provided)
            if signature:
                signature_valid, error = self._validate_signature(
                    signature, webhook_id, timestamp, nonce, payload
                )
                if not signature_valid:
                    return False, error

            logger.info(
                "Request validated successfully",
                webhook_id=webhook_id,
                timestamp=timestamp,
                nonce=nonce[:16]  # Log only first 16 chars
            )

            return True, None

        except redis.RedisError as e:
            logger.error("Redis error in replay prevention", error=str(e))
            # Fail open - allow request if Redis is unavailable
            # In production, you might want to fail closed instead
            return True, None
        except Exception as e:
            logger.error("Unexpected error in replay prevention", error=str(e))
            # Fail open
            return True, None

    async def cleanup_expired(self):
        """
        Cleanup expired nonces and signatures.
        Redis automatically handles TTL, but this can be used for manual cleanup.
        """
        try:
            # Redis automatically removes expired keys
            # This method can be extended for additional cleanup logic
            logger.info("Replay prevention cleanup completed")
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

    def close(self):
        """Close Redis connection"""
        try:
            self.redis_client.close()
            logger.info("Replay prevention connection closed")
        except Exception as e:
            logger.error("Error closing Redis connection", error=str(e))
