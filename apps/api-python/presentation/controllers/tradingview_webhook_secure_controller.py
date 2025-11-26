"""Secure TradingView Webhook Controller with all security layers"""

import json
import time
from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog

from infrastructure.di.container import get_container
from infrastructure.config.settings import get_settings
from application.services.tradingview_webhook_service import TradingViewWebhookService

# Security components
from infrastructure.security.redis_rate_limiter import (
    RedisRateLimiter,
    RateLimitConfig,
    get_client_identifier
)
from infrastructure.security.replay_attack_prevention import ReplayAttackPrevention
from infrastructure.security.tradingview_webhook_schema import (
    TradingViewWebhookPayload,
    WebhookResponse
)
from infrastructure.security.distributed_lock import DistributedLock
from infrastructure.security.circuit_breaker import (
    ExchangeCircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError
)
from infrastructure.security.error_sanitizer import get_error_sanitizer

logger = structlog.get_logger(__name__)


def create_secure_tradingview_webhook_router() -> APIRouter:
    """Create secure TradingView webhook router with all security layers"""
    router = APIRouter(tags=["TradingView Webhooks (Secure)"])

    # Get settings
    settings = get_settings()

    # Initialize security components
    try:
        rate_limiter = RedisRateLimiter(redis_url=settings.redis_url)
        replay_prevention = ReplayAttackPrevention(redis_url=settings.redis_url)
        distributed_lock = DistributedLock(redis_url=settings.redis_url)
        error_sanitizer = get_error_sanitizer(environment="production")

        # Circuit breakers for different exchanges
        circuit_breakers = {
            "binance": ExchangeCircuitBreaker(
                name="binance",
                config=CircuitBreakerConfig(
                    failure_threshold=5,
                    success_threshold=2,
                    timeout=60
                ),
                redis_url=settings.redis_url
            ),
            "bybit": ExchangeCircuitBreaker(name="bybit", redis_url=settings.redis_url),
            "bingx": ExchangeCircuitBreaker(name="bingx", redis_url=settings.redis_url),
            "bitget": ExchangeCircuitBreaker(name="bitget", redis_url=settings.redis_url),
        }

        logger.info("Security components initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize security components", error=str(e))
        # Continue without Redis-based features (fallback mode)
        rate_limiter = None
        replay_prevention = None
        distributed_lock = None
        circuit_breakers = {}
        error_sanitizer = get_error_sanitizer()

    async def get_tradingview_service() -> TradingViewWebhookService:
        """Dependency to get TradingView webhook service"""
        container = await get_container()
        return container.get("tradingview_webhook_service")

    @router.post("/webhooks/tradingview/secure/{webhook_id}")
    async def process_secure_webhook(
        webhook_id: str,
        request: Request,
        background_tasks: BackgroundTasks,
        tradingview_service: TradingViewWebhookService = Depends(get_tradingview_service),
    ) -> JSONResponse:
        """
        Process TradingView webhook with comprehensive security.

        Security layers:
        1. Rate limiting (per webhook_id)
        2. Replay attack prevention (timestamp + nonce validation)
        3. Payload validation (Pydantic schema)
        4. Distributed locking (prevent duplicate processing)
        5. Circuit breaker (protect against exchange failures)
        6. Error sanitization (no sensitive data leakage)
        """
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"

        try:
            # ==========================================
            # SECURITY LAYER 1: RATE LIMITING
            # ==========================================
            if rate_limiter:
                rate_limit_config = RateLimitConfig(
                    max_requests=60,  # 60 requests per minute per webhook
                    window_seconds=60,
                    block_duration=300  # 5 minutes block
                )

                allowed, rate_info = await rate_limiter.check_rate_limit(
                    identifier=f"webhook:{webhook_id}",
                    config=rate_limit_config,
                    scope="tradingview_webhook"
                )

                if not allowed:
                    logger.warning(
                        "Rate limit exceeded",
                        webhook_id=webhook_id,
                        client_ip=client_ip,
                        rate_info=rate_info
                    )
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "rate_limit_exceeded",
                            "message": "Too many requests. Please try again later.",
                            "retry_after": rate_info.get("retry_after", 60)
                        },
                        headers={
                            "Retry-After": str(rate_info.get("retry_after", 60))
                        }
                    )

            # ==========================================
            # VALIDATE WEBHOOK ID FORMAT
            # ==========================================
            try:
                webhook_uuid = UUID(webhook_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid webhook ID format")

            # ==========================================
            # PARSE REQUEST BODY
            # ==========================================
            try:
                body = await request.body()
                if not body:
                    raise HTTPException(status_code=400, detail="Empty request body")

                payload_dict = json.loads(body.decode("utf-8"))

            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON in webhook payload", error=str(e))
                raise HTTPException(status_code=400, detail="Invalid JSON payload")

            # ==========================================
            # SECURITY LAYER 2: REPLAY ATTACK PREVENTION
            # ==========================================
            if replay_prevention:
                timestamp = payload_dict.get("timestamp", int(time.time()))
                nonce = payload_dict.get("nonce")
                signature = request.headers.get("X-Webhook-Signature")

                if not nonce:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing 'nonce' field in payload (required for security)"
                    )

                # Validate request against replay attacks
                is_valid, error_msg = await replay_prevention.validate_request(
                    webhook_id=webhook_id,
                    timestamp=timestamp,
                    nonce=nonce,
                    payload=json.dumps(payload_dict, sort_keys=True),
                    signature=signature
                )

                if not is_valid:
                    logger.warning(
                        "Replay attack detected",
                        webhook_id=webhook_id,
                        error=error_msg
                    )
                    raise HTTPException(status_code=403, detail=error_msg)

            # ==========================================
            # SECURITY LAYER 3: PAYLOAD VALIDATION
            # ==========================================
            try:
                validated_payload = TradingViewWebhookPayload(**payload_dict)
                logger.info(
                    "Payload validated successfully",
                    webhook_id=webhook_id,
                    action=validated_payload.action,
                    symbol=validated_payload.symbol
                )
            except Exception as e:
                logger.warning(
                    "Payload validation failed",
                    webhook_id=webhook_id,
                    error=str(e)
                )
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid payload format: {str(e)}"
                )

            # ==========================================
            # SECURITY LAYER 4: DISTRIBUTED LOCKING
            # ==========================================
            lock_resource = f"webhook_process:{webhook_id}:{validated_payload.nonce}"

            if distributed_lock:
                try:
                    async with distributed_lock.lock_context(
                        resource=lock_resource,
                        ttl=30,  # 30 seconds max processing time
                        timeout=5  # Wait max 5 seconds for lock
                    ):
                        # Process inside lock to prevent duplicate processing
                        result = await _process_webhook_with_circuit_breaker(
                            tradingview_service=tradingview_service,
                            webhook_uuid=webhook_uuid,
                            validated_payload=validated_payload,
                            headers=dict(request.headers),
                            client_ip=client_ip,
                            circuit_breakers=circuit_breakers
                        )
                except RuntimeError as e:
                    # Lock acquisition failed - possible duplicate request
                    logger.warning(
                        "Failed to acquire lock (duplicate request?)",
                        webhook_id=webhook_id,
                        nonce=validated_payload.nonce
                    )
                    return JSONResponse(
                        status_code=409,  # Conflict
                        content={
                            "error": "duplicate_request",
                            "message": "This request is already being processed"
                        }
                    )
            else:
                # No distributed lock available - process directly
                result = await _process_webhook_with_circuit_breaker(
                    tradingview_service=tradingview_service,
                    webhook_uuid=webhook_uuid,
                    validated_payload=validated_payload,
                    headers=dict(request.headers),
                    client_ip=client_ip,
                    circuit_breakers=circuit_breakers
                )

            # ==========================================
            # BUILD RESPONSE
            # ==========================================
            processing_time = (time.time() - start_time) * 1000  # Convert to ms

            if result.get("success"):
                response = WebhookResponse(
                    success=True,
                    message="Webhook processed successfully",
                    order_id=result.get("order_id"),
                    execution_time=processing_time
                )
                return JSONResponse(
                    status_code=200,
                    content=response.dict()
                )
            else:
                # Error occurred
                error = result.get("error", "Unknown error")
                sanitized_error = error_sanitizer.sanitize_error(
                    Exception(error),
                    error_type="webhook_processing"
                )

                response = WebhookResponse(
                    success=False,
                    message=sanitized_error["message"],
                    execution_time=processing_time
                )
                return JSONResponse(
                    status_code=422,
                    content=response.dict()
                )

        except HTTPException:
            raise
        except CircuitBreakerError as e:
            # Circuit breaker is open
            logger.error(
                "Circuit breaker open",
                webhook_id=webhook_id,
                error=str(e)
            )
            return JSONResponse(
                status_code=503,  # Service Unavailable
                content={
                    "error": "service_unavailable",
                    "message": "Exchange service temporarily unavailable. Please try again later."
                }
            )
        except Exception as e:
            # Unhandled error - sanitize before returning
            logger.error(
                "Unhandled error in secure webhook",
                webhook_id=webhook_id,
                error=str(e),
                exc_info=True
            )

            sanitized = error_sanitizer.create_safe_error_response(
                error=e,
                status_code=500,
                error_type="internal",
                additional_context={"webhook_id": webhook_id}
            )

            return JSONResponse(
                status_code=500,
                content=sanitized
            )

    async def _process_webhook_with_circuit_breaker(
        tradingview_service: TradingViewWebhookService,
        webhook_uuid: UUID,
        validated_payload: TradingViewWebhookPayload,
        headers: Dict[str, Any],
        client_ip: str,
        circuit_breakers: Dict[str, ExchangeCircuitBreaker]
    ) -> Dict[str, Any]:
        """Process webhook with circuit breaker protection"""

        # Convert validated payload to dict
        payload_dict = validated_payload.dict()

        # Determine which exchange will be used (simplified - would need webhook config)
        exchange_name = payload_dict.get("exchange", "binance").lower()

        # Get circuit breaker for this exchange
        circuit_breaker = circuit_breakers.get(exchange_name)

        if circuit_breaker:
            # Call with circuit breaker protection
            return await circuit_breaker.call(
                tradingview_service.process_tradingview_webhook,
                webhook_id=webhook_uuid,
                payload=payload_dict,
                headers=headers,
                user_ip=client_ip
            )
        else:
            # No circuit breaker - call directly
            return await tradingview_service.process_tradingview_webhook(
                webhook_id=webhook_uuid,
                payload=payload_dict,
                headers=headers,
                user_ip=client_ip
            )

    @router.get("/webhooks/tradingview/secure/{webhook_id}/health")
    async def get_webhook_health(webhook_id: str) -> JSONResponse:
        """Get health status of webhook including circuit breaker states"""

        health_status = {
            "webhook_id": webhook_id,
            "timestamp": int(time.time()),
            "circuit_breakers": {}
        }

        # Add circuit breaker metrics
        for exchange_name, cb in circuit_breakers.items():
            health_status["circuit_breakers"][exchange_name] = cb.get_metrics()

        return JSONResponse(status_code=200, content=health_status)

    return router
