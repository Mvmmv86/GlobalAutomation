"""Circuit Breaker pattern for Exchange API calls"""

import time
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass, field

import redis
import structlog

logger = structlog.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures exceeded threshold, reject all requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5           # Number of failures before opening circuit
    success_threshold: int = 2           # Number of successes needed to close circuit
    timeout: int = 60                    # Time to wait before trying again (seconds)
    half_open_max_calls: int = 3         # Max calls allowed in half-open state
    monitored_exceptions: tuple = (Exception,)  # Exceptions to monitor


@dataclass
class CircuitMetrics:
    """Circuit breaker metrics"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    opened_at: float = 0.0
    last_state_change: float = field(default_factory=time.time)
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class ExchangeCircuitBreaker:
    """
    Circuit Breaker for protecting against cascading failures in exchange APIs.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject all requests
    - HALF_OPEN: Test if service recovered, allow limited requests

    When circuit opens, it prevents further requests for a timeout period,
    giving the failing service time to recover.
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        redis_url: str = "redis://localhost:6379/0"
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker name (e.g., "binance", "bybit")
            config: Circuit breaker configuration
            redis_url: Redis connection URL for distributed state
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # Try to use Redis for distributed state
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.redis_client.ping()
            self.use_redis = True
            logger.info(
                "Circuit breaker initialized with Redis",
                name=name,
                redis_url=redis_url
            )
        except Exception as e:
            logger.warning(
                "Redis unavailable, using in-memory state",
                name=name,
                error=str(e)
            )
            self.redis_client = None
            self.use_redis = False

        # In-memory metrics (fallback or local cache)
        self.metrics = CircuitMetrics()

        self.key_prefix = f"circuit_breaker:{name}"

    def _get_redis_key(self, metric: str) -> str:
        """Generate Redis key for metric"""
        return f"{self.key_prefix}:{metric}"

    def _get_state(self) -> CircuitState:
        """Get current circuit state (from Redis or memory)"""
        if self.use_redis:
            try:
                state_str = self.redis_client.get(self._get_redis_key("state"))
                if state_str:
                    return CircuitState(state_str)
            except Exception as e:
                logger.error("Error reading state from Redis", error=str(e))

        return self.metrics.state

    def _set_state(self, state: CircuitState):
        """Set circuit state (to Redis and memory)"""
        self.metrics.state = state
        self.metrics.last_state_change = time.time()

        if self.use_redis:
            try:
                self.redis_client.setex(
                    self._get_redis_key("state"),
                    3600,  # 1 hour TTL
                    state.value
                )
            except Exception as e:
                logger.error("Error writing state to Redis", error=str(e))

    def _increment_metric(self, metric: str) -> int:
        """Increment a metric (in Redis and memory)"""
        # Update memory
        current_value = getattr(self.metrics, metric, 0)
        new_value = current_value + 1
        setattr(self.metrics, metric, new_value)

        # Update Redis
        if self.use_redis:
            try:
                redis_key = self._get_redis_key(metric)
                self.redis_client.incr(redis_key)
                self.redis_client.expire(redis_key, 3600)  # 1 hour TTL
            except Exception as e:
                logger.error(f"Error incrementing {metric} in Redis", error=str(e))

        return new_value

    def _get_metric(self, metric: str) -> int:
        """Get metric value (from Redis or memory)"""
        if self.use_redis:
            try:
                value = self.redis_client.get(self._get_redis_key(metric))
                if value:
                    return int(value)
            except Exception as e:
                logger.error(f"Error reading {metric} from Redis", error=str(e))

        return getattr(self.metrics, metric, 0)

    def _reset_counts(self):
        """Reset failure and success counts"""
        self.metrics.failure_count = 0
        self.metrics.success_count = 0

        if self.use_redis:
            try:
                self.redis_client.delete(
                    self._get_redis_key("failure_count"),
                    self._get_redis_key("success_count")
                )
            except Exception as e:
                logger.error("Error resetting counts in Redis", error=str(e))

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception from func if circuit allows
        """
        state = self._get_state()

        # Check if circuit is open
        if state == CircuitState.OPEN:
            # Check if timeout has passed
            now = time.time()
            if now - self.metrics.opened_at >= self.config.timeout:
                # Transition to half-open
                logger.info(
                    "Circuit transitioning to HALF_OPEN",
                    name=self.name,
                    timeout=self.config.timeout
                )
                self._set_state(CircuitState.HALF_OPEN)
                self._reset_counts()
            else:
                # Still open, reject request
                time_remaining = int(self.config.timeout - (now - self.metrics.opened_at))
                logger.warning(
                    "Circuit is OPEN, rejecting request",
                    name=self.name,
                    retry_in=time_remaining
                )
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Retry in {time_remaining} seconds."
                )

        # Half-open: limit number of test calls
        if state == CircuitState.HALF_OPEN:
            total_half_open_calls = (
                self._get_metric("failure_count") +
                self._get_metric("success_count")
            )
            if total_half_open_calls >= self.config.half_open_max_calls:
                logger.warning(
                    "Too many calls in HALF_OPEN state",
                    name=self.name,
                    calls=total_half_open_calls
                )
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is in HALF_OPEN state. "
                    "Please wait before retrying."
                )

        # Execute the function
        self._increment_metric("total_calls")

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) \
                     else func(*args, **kwargs)

            # Success
            self._on_success()
            return result

        except self.config.monitored_exceptions as e:
            # Failure
            self._on_failure(e)
            raise

    def _on_success(self):
        """Handle successful call"""
        state = self._get_state()

        self._increment_metric("total_successes")
        success_count = self._increment_metric("success_count")

        if state == CircuitState.HALF_OPEN:
            # Check if enough successes to close circuit
            if success_count >= self.config.success_threshold:
                logger.info(
                    "Circuit transitioning to CLOSED (recovered)",
                    name=self.name,
                    successes=success_count
                )
                self._set_state(CircuitState.CLOSED)
                self._reset_counts()

    def _on_failure(self, exception: Exception):
        """Handle failed call"""
        state = self._get_state()

        self.metrics.last_failure_time = time.time()
        self._increment_metric("total_failures")
        failure_count = self._increment_metric("failure_count")

        logger.warning(
            "Circuit breaker recorded failure",
            name=self.name,
            state=state.value,
            failure_count=failure_count,
            threshold=self.config.failure_threshold,
            exception=str(exception)[:100]
        )

        # Check if should open circuit
        if state == CircuitState.HALF_OPEN:
            # Any failure in half-open reopens circuit
            logger.warning(
                "Circuit transitioning to OPEN (failure in HALF_OPEN)",
                name=self.name
            )
            self.metrics.opened_at = time.time()
            self._set_state(CircuitState.OPEN)
            self._reset_counts()

        elif state == CircuitState.CLOSED:
            # Check if threshold exceeded
            if failure_count >= self.config.failure_threshold:
                logger.error(
                    "Circuit transitioning to OPEN (threshold exceeded)",
                    name=self.name,
                    failures=failure_count,
                    threshold=self.config.failure_threshold
                )
                self.metrics.opened_at = time.time()
                self._set_state(CircuitState.OPEN)
                self._reset_counts()

    def get_metrics(self) -> dict:
        """Get circuit breaker metrics"""
        return {
            "name": self.name,
            "state": self._get_state().value,
            "failure_count": self._get_metric("failure_count"),
            "success_count": self._get_metric("success_count"),
            "total_calls": self._get_metric("total_calls"),
            "total_failures": self._get_metric("total_failures"),
            "total_successes": self._get_metric("total_successes"),
            "last_failure_time": self.metrics.last_failure_time,
            "last_state_change": self.metrics.last_state_change,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout
            }
        }

    def reset(self):
        """Reset circuit breaker to initial state"""
        logger.info("Circuit breaker reset", name=self.name)
        self._set_state(CircuitState.CLOSED)
        self._reset_counts()
        self.metrics = CircuitMetrics()

        if self.use_redis:
            try:
                # Clear all Redis keys for this circuit
                keys = self.redis_client.keys(f"{self.key_prefix}:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.error("Error clearing Redis keys", error=str(e))


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


# Import asyncio for coroutine check
import asyncio
