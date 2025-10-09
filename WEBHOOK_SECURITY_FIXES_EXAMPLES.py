"""
WEBHOOK SECURITY FIXES - CODIGO PRONTO PARA IMPLEMENTACAO
=========================================================

Este arquivo contem implementacoes prontas para corrigir as 7 vulnerabilidades CRITICAS
identificadas na auditoria de seguranca do sistema de webhooks.

Autor: Claude Code (Anthropic Security Specialist)
Data: 09/10/2025
"""

import asyncio
import hashlib
import json
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

import redis.asyncio as redis
import structlog
from circuitbreaker import CircuitBreaker, CircuitBreakerError
from pydantic import BaseModel, Field, validator, ValidationError

logger = structlog.get_logger()


# ============================================================================
# FIX CRITICA-01: RATE LIMITING REAL COM REDIS
# ============================================================================

class RedisRateLimiter:
    """Rate limiter using Redis for distributed systems"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url

    async def check_rate_limit(
        self,
        webhook_id: UUID,
        rate_limit_per_minute: int = 60,
        rate_limit_per_hour: int = 1000,
    ) -> bool:
        """
        Check if webhook is within rate limits

        Args:
            webhook_id: Webhook UUID
            rate_limit_per_minute: Max requests per minute
            rate_limit_per_hour: Max requests per hour

        Returns:
            True if within limits, False if exceeded
        """
        try:
            redis_client = await redis.from_url(self.redis_url)

            # Check per-minute rate limit
            minute_key = f"webhook:{webhook_id}:minute:{datetime.now().strftime('%Y%m%d%H%M')}"
            minute_count = await redis_client.incr(minute_key)

            if minute_count == 1:
                await redis_client.expire(minute_key, 60)

            if minute_count > rate_limit_per_minute:
                logger.warning(
                    "Rate limit exceeded (per minute)",
                    webhook_id=str(webhook_id),
                    count=minute_count,
                    limit=rate_limit_per_minute,
                )
                await redis_client.close()
                return False

            # Check per-hour rate limit
            hour_key = f"webhook:{webhook_id}:hour:{datetime.now().strftime('%Y%m%d%H')}"
            hour_count = await redis_client.incr(hour_key)

            if hour_count == 1:
                await redis_client.expire(hour_key, 3600)

            if hour_count > rate_limit_per_hour:
                logger.warning(
                    "Rate limit exceeded (per hour)",
                    webhook_id=str(webhook_id),
                    count=hour_count,
                    limit=rate_limit_per_hour,
                )
                await redis_client.close()
                return False

            await redis_client.close()
            return True

        except Exception as e:
            logger.error(f"Rate limiting check failed: {e}")
            # FAIL SECURE: If Redis fails, reject request
            return False


# ============================================================================
# FIX CRITICA-02: REPLAY ATTACK PREVENTION
# ============================================================================

class ReplayAttackPrevention:
    """Prevent replay attacks using nonce tracking with Redis"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.nonce_ttl = 360  # 6 minutes (signature_tolerance + buffer)

    async def check_replay_attack(
        self,
        webhook_id: UUID,
        payload: Dict[str, Any],
        timestamp: str,
    ) -> bool:
        """
        Check if request is a replay attack

        Args:
            webhook_id: Webhook UUID
            payload: Request payload
            timestamp: Request timestamp

        Returns:
            True if legitimate request, False if replay attack detected
        """
        try:
            # Generate unique nonce from payload + timestamp
            payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            nonce = hashlib.sha256(
                f"{webhook_id}:{payload_str}:{timestamp}".encode()
            ).hexdigest()

            redis_client = await redis.from_url(self.redis_url)
            nonce_key = f"webhook:nonce:{nonce}"

            # Check if nonce already used
            exists = await redis_client.exists(nonce_key)

            if exists:
                logger.warning(
                    "Replay attack detected - nonce already used",
                    webhook_id=str(webhook_id),
                    nonce=nonce[:16],
                )
                await redis_client.close()
                return False

            # Store nonce with expiry
            await redis_client.setex(nonce_key, self.nonce_ttl, "1")

            await redis_client.close()
            return True

        except Exception as e:
            logger.error(f"Replay attack check failed: {e}")
            return False


# ============================================================================
# FIX CRITICA-03: VALIDACAO DE PAYLOAD COM PYDANTIC
# ============================================================================

class TradingViewWebhookPayload(BaseModel):
    """Validated webhook payload schema with strict validation"""

    ticker: str = Field(
        ..., min_length=6, max_length=20, description="Trading symbol (e.g., BTCUSDT)"
    )
    action: str = Field(
        ..., pattern="^(buy|sell|close)$", description="Order action"
    )
    quantity: Decimal = Field(
        ..., gt=0, description="Order quantity (must be positive)"
    )
    price: Optional[Decimal] = Field(
        None, gt=0, description="Order price (optional for market orders)"
    )
    order_type: str = Field(
        "market", pattern="^(market|limit)$", description="Order type"
    )
    stop_loss: Optional[Decimal] = Field(None, gt=0)
    take_profit: Optional[Decimal] = Field(None, gt=0)
    leverage: Optional[int] = Field(
        1, ge=1, le=125, description="Leverage 1-125x"
    )
    timestamp: Optional[str] = Field(None, description="Request timestamp")

    @validator("ticker")
    def validate_ticker(cls, v):
        """Validate ticker format and prevent injection"""
        import re

        # Sanitize input
        v = v.upper().strip()

        # Check format (alphanumeric + USDT only)
        if not re.match(r"^[A-Z0-9]+USDT$", v):
            raise ValueError(
                f"Invalid ticker format: {v}. Must be alphanumeric ending with USDT"
            )

        # Check length (prevent DoS)
        if len(v) < 6 or len(v) > 15:
            raise ValueError(f"Invalid ticker length: {v}")

        # Optional: Whitelist known symbols
        ALLOWED_SYMBOLS = [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "ADAUSDT",
            "SOLUSDT",
            "XRPUSDT",
            "DOTUSDT",
            "DOGEUSDT",
            "AVAXUSDT",
            "MATICUSDT",
        ]

        # Uncomment to enforce whitelist
        # if v not in ALLOWED_SYMBOLS:
        #     raise ValueError(f"Symbol {v} not in whitelist")

        return v

    @validator("quantity")
    def validate_quantity(cls, v):
        """Validate quantity ranges"""
        if v <= 0:
            raise ValueError("Quantity must be positive")

        if v > Decimal("1000000"):
            raise ValueError("Quantity exceeds maximum allowed (1M)")

        # Check precision (max 8 decimals)
        if v.as_tuple().exponent < -8:
            raise ValueError("Quantity has too many decimal places (max 8)")

        return v

    @validator("price", "stop_loss", "take_profit")
    def validate_prices(cls, v):
        """Validate price values"""
        if v is not None:
            if v <= 0:
                raise ValueError("Price must be positive")

            if v > Decimal("10000000"):
                raise ValueError("Price exceeds maximum allowed (10M)")

        return v

    class Config:
        # Prevent extra fields (security)
        extra = "forbid"


# ============================================================================
# FIX CRITICA-04: DISTRIBUTED LOCKING PARA RACE CONDITIONS
# ============================================================================

@asynccontextmanager
async def distributed_lock(
    lock_key: str,
    redis_url: str = "redis://localhost:6379",
    timeout: int = 10,
):
    """
    Distributed lock using Redis to prevent race conditions

    Args:
        lock_key: Unique key for the lock
        redis_url: Redis connection URL
        timeout: Lock timeout in seconds

    Usage:
        async with distributed_lock("order:BTCUSDT:123"):
            # Critical section
            await create_order(...)
    """
    redis_client = await redis.from_url(redis_url)
    lock = redis_client.lock(lock_key, timeout=timeout)

    try:
        # Acquire lock with timeout
        acquired = await lock.acquire(blocking=True, blocking_timeout=timeout)

        if not acquired:
            raise Exception(f"Failed to acquire lock: {lock_key}")

        logger.debug(f"Lock acquired: {lock_key}")
        yield lock

    finally:
        try:
            await lock.release()
            logger.debug(f"Lock released: {lock_key}")
        except Exception as e:
            logger.warning(f"Failed to release lock: {e}")

        await redis_client.close()


# ============================================================================
# FIX CRITICA-05: CIRCUIT BREAKER PARA EXCHANGE API
# ============================================================================

class ExchangeCircuitBreaker:
    """Circuit breaker for exchange API calls"""

    def __init__(self):
        self.breakers = {}  # exchange_type -> CircuitBreaker
        self.failure_threshold = 5  # Open after 5 failures
        self.recovery_timeout = 60  # Try again after 60 seconds

    def get_breaker(self, exchange_type: str) -> CircuitBreaker:
        """Get or create circuit breaker for exchange"""
        if exchange_type not in self.breakers:
            self.breakers[exchange_type] = CircuitBreaker(
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
                expected_exception=Exception,
            )

        return self.breakers[exchange_type]

    async def call_with_breaker(
        self,
        exchange_type: str,
        func,
        *args,
        **kwargs,
    ):
        """
        Execute function with circuit breaker protection

        Args:
            exchange_type: Exchange name (binance, bybit, etc)
            func: Async function to execute
            *args, **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            Exception if circuit breaker is open
        """
        breaker = self.get_breaker(exchange_type)

        try:
            return await breaker.call_async(func, *args, **kwargs)

        except CircuitBreakerError as e:
            logger.error(
                "Circuit breaker OPEN - Exchange API unavailable",
                exchange_type=exchange_type,
                failures=breaker.failure_count,
                state=breaker.current_state,
            )
            raise Exception(
                f"Exchange {exchange_type} temporarily unavailable (circuit breaker open)"
            )


# Initialize global circuit breaker
exchange_circuit_breaker = ExchangeCircuitBreaker()


# ============================================================================
# FIX CRITICA-06: SECRETS MANAGER (AWS EXAMPLE)
# ============================================================================

class SecretsManager:
    """Secure secrets management with AWS Secrets Manager"""

    def __init__(self, region_name: str = "us-east-1"):
        try:
            import boto3
            from botocore.exceptions import ClientError

            self.client = boto3.client("secretsmanager", region_name=region_name)
            self.ClientError = ClientError
        except ImportError:
            logger.warning("boto3 not installed - secrets manager disabled")
            self.client = None

        self.cache = {}
        self.cache_ttl = 300  # 5 minutes

    async def get_secret(self, secret_name: str) -> dict:
        """
        Get secret from AWS Secrets Manager with caching

        Args:
            secret_name: Secret identifier (e.g., 'binance/api/production')

        Returns:
            Secret dictionary with api_key, api_secret, etc
        """
        if not self.client:
            raise Exception("Secrets Manager not available - boto3 not installed")

        # Check cache
        if secret_name in self.cache:
            cached = self.cache[secret_name]
            if datetime.now() < cached["expiry"]:
                return cached["value"]

        try:
            response = self.client.get_secret_value(SecretId=secret_name)

            if "SecretString" in response:
                import json

                secret = json.loads(response["SecretString"])

                # Cache result
                self.cache[secret_name] = {
                    "value": secret,
                    "expiry": datetime.now() + timedelta(seconds=self.cache_ttl),
                }

                return secret

        except self.ClientError as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise Exception("Failed to load API credentials")

    async def rotate_secret(
        self, secret_name: str, new_key: str, new_secret: str
    ):
        """
        Rotate API credentials

        Args:
            secret_name: Secret identifier
            new_key: New API key
            new_secret: New API secret
        """
        if not self.client:
            raise Exception("Secrets Manager not available")

        try:
            import json

            self.client.put_secret_value(
                SecretId=secret_name,
                SecretString=json.dumps(
                    {
                        "api_key": new_key,
                        "api_secret": new_secret,
                        "rotated_at": datetime.now().isoformat(),
                    }
                ),
            )

            # Clear cache
            if secret_name in self.cache:
                del self.cache[secret_name]

            logger.info(f"Secret rotated successfully: {secret_name}")

        except self.ClientError as e:
            logger.error(f"Failed to rotate secret: {e}")
            raise


# ============================================================================
# FIX CRITICA-07: ERROR SANITIZATION
# ============================================================================

ERROR_MESSAGES = {
    # Generic errors
    "default": "Processing error occurred - please contact support",
    # Specific safe messages
    "hmac_validation_failed": "Invalid webhook signature",
    "rate_limit_exceeded": "Rate limit exceeded - please try again later",
    "replay_attack": "Duplicate request detected",
    "invalid_payload": "Invalid request format",
    "webhook_disabled": "Webhook is currently disabled",
    "exchange_unavailable": "Exchange temporarily unavailable",
}


def sanitize_error_message(error: str, webhook_id: str) -> str:
    """
    Sanitize error message for external response

    Args:
        error: Internal error message
        webhook_id: Webhook ID for logging

    Returns:
        Safe error message for external API
    """
    error_lower = error.lower()

    # Map known error types to safe messages
    if "hmac" in error_lower or "signature" in error_lower:
        return ERROR_MESSAGES["hmac_validation_failed"]

    if "rate limit" in error_lower:
        return ERROR_MESSAGES["rate_limit_exceeded"]

    if "replay" in error_lower or "nonce" in error_lower:
        return ERROR_MESSAGES["replay_attack"]

    if "validation" in error_lower or "invalid" in error_lower:
        return ERROR_MESSAGES["invalid_payload"]

    if "disabled" in error_lower or "inactive" in error_lower:
        return ERROR_MESSAGES["webhook_disabled"]

    if "circuit breaker" in error_lower or "unavailable" in error_lower:
        return ERROR_MESSAGES["exchange_unavailable"]

    # For any other error, return generic message and log details
    logger.error(
        "Unhandled webhook error",
        webhook_id=webhook_id,
        error=error,
        error_hash=hashlib.sha256(error.encode()).hexdigest()[:16],
    )

    return ERROR_MESSAGES["default"]


# ============================================================================
# LOG SANITIZATION (BONUS: GDPR COMPLIANCE)
# ============================================================================

def sanitize_for_logging(
    data: Any,
    fields_to_hash: list = None,
    fields_to_remove: list = None,
) -> Any:
    """
    Sanitize data before logging to comply with GDPR/LGPD

    Args:
        data: Data to sanitize
        fields_to_hash: Fields to hash (PII)
        fields_to_remove: Fields to completely remove (secrets)

    Returns:
        Sanitized data safe for logging
    """
    if fields_to_hash is None:
        fields_to_hash = ["client_ip", "user_ip", "ip", "email", "api_key"]

    if fields_to_remove is None:
        fields_to_remove = ["password", "secret", "token", "api_secret", "signature"]

    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()

            # Remove sensitive fields
            if any(field in key_lower for field in fields_to_remove):
                sanitized[key] = "***REDACTED***"

            # Hash PII fields
            elif any(field in key_lower for field in fields_to_hash):
                if isinstance(value, str):
                    # Hash IP/PII (first 16 chars of SHA256)
                    sanitized[key] = hashlib.sha256(value.encode()).hexdigest()[:16]
                else:
                    sanitized[key] = value

            # Recursively sanitize nested dicts
            elif isinstance(value, dict):
                sanitized[key] = sanitize_for_logging(
                    value, fields_to_hash, fields_to_remove
                )

            # Keep other fields
            else:
                sanitized[key] = value

        return sanitized

    elif isinstance(data, str):
        # Check if string looks like sensitive data
        if len(data) > 32 and any(char in data for char in ["=", "/", "+"]):
            # Looks like base64 or token
            return f"{data[:8]}...{data[-8:]}"
        return data

    else:
        return data


# ============================================================================
# EXEMPLO DE USO INTEGRADO
# ============================================================================

async def process_webhook_with_security(
    webhook_id: UUID,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    user_ip: str,
) -> Dict[str, Any]:
    """
    Example of webhook processing with all security fixes integrated

    This demonstrates how to use all security components together
    """

    # Initialize security components
    rate_limiter = RedisRateLimiter()
    replay_prevention = ReplayAttackPrevention()

    try:
        # 1. Rate Limiting Check
        if not await rate_limiter.check_rate_limit(webhook_id):
            return {
                "success": False,
                "error": sanitize_error_message("Rate limit exceeded", str(webhook_id)),
            }

        # 2. Replay Attack Check
        timestamp = headers.get("X-Timestamp") or payload.get("timestamp")
        if timestamp:
            if not await replay_prevention.check_replay_attack(
                webhook_id, payload, timestamp
            ):
                return {
                    "success": False,
                    "error": sanitize_error_message("Replay attack detected", str(webhook_id)),
                }

        # 3. Payload Validation
        try:
            validated_payload = TradingViewWebhookPayload.parse_obj(payload)
        except ValidationError as e:
            logger.warning(
                "Payload validation failed",
                webhook_id=str(webhook_id),
                errors=e.errors(),
            )
            return {
                "success": False,
                "error": sanitize_error_message("Invalid payload", str(webhook_id)),
            }

        # 4. Execute with Distributed Lock (prevent race conditions)
        lock_key = f"order:lock:{webhook_id}:{validated_payload.ticker}:{validated_payload.action}"

        async with distributed_lock(lock_key):
            # 5. Execute with Circuit Breaker (prevent cascade failures)
            try:
                order_result = await exchange_circuit_breaker.call_with_breaker(
                    "binance",
                    create_order_on_exchange,
                    symbol=validated_payload.ticker,
                    side=validated_payload.action,
                    quantity=validated_payload.quantity,
                    price=validated_payload.price,
                )

                # 6. Sanitize logs (GDPR compliance)
                sanitized_payload = sanitize_for_logging(payload)
                logger.info(
                    "Webhook processed successfully",
                    webhook_id=str(webhook_id),
                    payload=sanitized_payload,
                    order_id=order_result.get("order_id"),
                )

                return {
                    "success": True,
                    "order_id": order_result.get("order_id"),
                    "message": "Order executed successfully",
                }

            except Exception as e:
                logger.error(
                    "Order execution failed",
                    webhook_id=str(webhook_id),
                    error=str(e),
                )
                return {
                    "success": False,
                    "error": sanitize_error_message(str(e), str(webhook_id)),
                }

    except Exception as e:
        logger.error(
            "Webhook processing failed",
            webhook_id=str(webhook_id),
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": sanitize_error_message(str(e), str(webhook_id)),
        }


async def create_order_on_exchange(
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
) -> Dict[str, Any]:
    """
    Mock function - replace with actual exchange API call

    In production, this would call:
    - BinanceConnector.create_market_order()
    - Or SecureExchangeService.create_order()
    """
    # Simulate API call
    await asyncio.sleep(0.1)

    return {
        "order_id": "12345678",
        "status": "FILLED",
        "symbol": symbol,
        "side": side,
        "quantity": str(quantity),
    }


# ============================================================================
# TESTE RAPIDO
# ============================================================================

async def test_security_fixes():
    """Quick test of all security components"""

    print("Testing security fixes...")

    # Test 1: Rate Limiting
    rate_limiter = RedisRateLimiter()
    webhook_id = UUID("12345678-1234-1234-1234-123456789012")

    print("\n1. Testing Rate Limiting...")
    for i in range(3):
        result = await rate_limiter.check_rate_limit(webhook_id)
        print(f"   Request {i+1}: {'ALLOWED' if result else 'BLOCKED'}")

    # Test 2: Replay Prevention
    replay_prevention = ReplayAttackPrevention()

    print("\n2. Testing Replay Prevention...")
    payload = {"ticker": "BTCUSDT", "action": "buy", "quantity": 0.001}
    timestamp = str(int(time.time()))

    result1 = await replay_prevention.check_replay_attack(webhook_id, payload, timestamp)
    print(f"   First request: {'ALLOWED' if result1 else 'BLOCKED'}")

    result2 = await replay_prevention.check_replay_attack(webhook_id, payload, timestamp)
    print(f"   Replay attempt: {'ALLOWED' if result2 else 'BLOCKED (GOOD!)'}")

    # Test 3: Payload Validation
    print("\n3. Testing Payload Validation...")

    valid_payload = {
        "ticker": "BTCUSDT",
        "action": "buy",
        "quantity": "0.001",
        "order_type": "market",
    }

    try:
        validated = TradingViewWebhookPayload.parse_obj(valid_payload)
        print(f"   Valid payload: ACCEPTED ({validated.ticker})")
    except ValidationError as e:
        print(f"   Valid payload: REJECTED (ERROR!)")

    invalid_payload = {
        "ticker": "INVALID",
        "action": "invalid_action",
        "quantity": "-1",
    }

    try:
        validated = TradingViewWebhookPayload.parse_obj(invalid_payload)
        print(f"   Invalid payload: ACCEPTED (ERROR!)")
    except ValidationError as e:
        print(f"   Invalid payload: REJECTED (GOOD!)")

    # Test 4: Circuit Breaker
    print("\n4. Testing Circuit Breaker...")

    async def failing_api_call():
        """Simulate failing API"""
        raise Exception("API error")

    for i in range(7):
        try:
            await exchange_circuit_breaker.call_with_breaker(
                "binance", failing_api_call
            )
        except Exception as e:
            status = "OPEN" if "circuit breaker" in str(e).lower() else "CLOSED"
            print(f"   Attempt {i+1}: FAILED (Circuit breaker: {status})")

    # Test 5: Error Sanitization
    print("\n5. Testing Error Sanitization...")

    errors = [
        "HMAC signature validation failed",
        "Binance API error: Insufficient balance",
        "Database connection timeout",
        "User ID 12345 not found in exchange_accounts table",
    ]

    for error in errors:
        sanitized = sanitize_error_message(error, str(webhook_id))
        print(f"   Internal: {error[:50]}...")
        print(f"   External: {sanitized}")
        print()

    print("\nAll tests completed!")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_security_fixes())
