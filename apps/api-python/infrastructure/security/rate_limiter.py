"""Advanced Rate Limiting with Redis backend and multiple strategies"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from ..config.settings import get_settings
except ImportError:
    # Para testes diretos
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from infrastructure.config.settings import get_settings

logger = structlog.get_logger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window" 
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RateLimitRule:
    """Rate limit rule configuration"""
    requests: int  # Number of requests allowed
    window: int    # Time window in seconds
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_limit: Optional[int] = None  # Allow short bursts
    block_duration: int = 300  # Block duration in seconds after limit exceeded


@dataclass
class ClientState:
    """Track client request state"""
    requests: List[float] = field(default_factory=list)
    tokens: int = 0
    last_refill: float = 0.0
    blocked_until: float = 0.0


class AdvancedRateLimiter:
    """Advanced rate limiter with multiple strategies and memory backend"""
    
    def __init__(self):
        self.clients: Dict[str, ClientState] = {}
        self.rules: Dict[str, RateLimitRule] = {}
        self.cleanup_interval = 300  # Cleanup every 5 minutes
        self.last_cleanup = time.time()
        self.settings = get_settings()
        
        # Development IP whitelist
        self.dev_whitelist = {
            "127.0.0.1", "::1", "localhost", 
            "0.0.0.0", "192.168.0.1", "10.0.0.1"
        }
        
        # Define default rules for different endpoints
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default rate limiting rules based on environment"""
        
        is_dev = self.settings.environment.lower() in ["development", "dev", "local"]
        
        # Authentication endpoints - adjust limits based on environment
        if is_dev:
            # Development: More permissive for testing
            auth_requests = 100
            auth_window = 60  
            auth_block = 60  # Short block duration for dev
        else:
            # Production: Restrictive security
            auth_requests = 10
            auth_window = 60
            auth_block = 300  # Longer block for prod
        
        self.rules["/api/v1/auth/login"] = RateLimitRule(
            requests=auth_requests, 
            window=auth_window,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            block_duration=auth_block
        )
        
        self.rules["/api/v1/auth/register"] = RateLimitRule(
            requests=auth_requests,
            window=auth_window,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            block_duration=auth_block
        )
        
        # Webhook endpoints - moderate limits
        self.rules["/api/v1/webhooks/*"] = RateLimitRule(
            requests=100,
            window=60,  # 100 requests per minute
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            burst_limit=150
        )
        
        # Trading endpoints - more permissive but protected
        self.rules["/api/v1/orders"] = RateLimitRule(
            requests=50,
            window=60,  # 50 requests per minute
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        
        # General API endpoints
        self.rules["*"] = RateLimitRule(
            requests=1000,
            window=60,  # 1000 requests per minute for general endpoints
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
    
    def _get_client_key(self, request: Request) -> str:
        """Generate unique client key from request"""
        # Try to get real IP from headers (proxy/load balancer)
        client_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip() or
            request.headers.get("x-real-ip") or
            request.client.host if request.client else "unknown"
        )
        
        # Include user ID if authenticated
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}:{client_ip}"
        
        return f"ip:{client_ip}"
    
    def _is_whitelisted(self, client_ip: str) -> bool:
        """Check if client IP is whitelisted for development"""
        is_dev = self.settings.environment.lower() in ["development", "dev", "local"]
        if not is_dev:
            return False
            
        # Check exact IP match
        if client_ip in self.dev_whitelist:
            return True
            
        # Check if it's a local development IP
        if client_ip.startswith(("127.", "192.168.", "10.0.", "172.16.")):
            return True
            
        return False
    
    def _get_rule_for_path(self, path: str) -> RateLimitRule:
        """Get rate limit rule for specific path"""
        # Try exact match first
        if path in self.rules:
            return self.rules[path]
        
        # Try wildcard matches
        for rule_path, rule in self.rules.items():
            if rule_path.endswith("*") and path.startswith(rule_path[:-1]):
                return rule
        
        # Return default rule
        return self.rules["*"]
    
    def _cleanup_old_entries(self):
        """Clean up old entries to prevent memory leaks"""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        expired_clients = []
        for client_key, state in self.clients.items():
            # Remove clients with no recent activity
            if (state.requests and now - state.requests[-1] > 3600) or \
               (not state.requests and now - state.last_refill > 3600):
                expired_clients.append(client_key)
        
        for client_key in expired_clients:
            del self.clients[client_key]
        
        self.last_cleanup = now
        logger.info(f"Cleaned up {len(expired_clients)} expired rate limit entries")
    
    def _check_sliding_window(
        self, 
        client_key: str, 
        rule: RateLimitRule, 
        now: float
    ) -> Tuple[bool, Dict]:
        """Check sliding window rate limit"""
        state = self.clients.get(client_key, ClientState())
        
        # Check if client is currently blocked
        if state.blocked_until > now:
            remaining_block = int(state.blocked_until - now)
            return False, {
                "error": "Rate limit exceeded - blocked",
                "blocked_for": remaining_block,
                "retry_after": remaining_block
            }
        
        # Remove old requests outside the window
        cutoff = now - rule.window
        state.requests = [req_time for req_time in state.requests if req_time > cutoff]
        
        # Check if limit is exceeded
        current_count = len(state.requests)
        if current_count >= rule.requests:
            # Block the client
            state.blocked_until = now + rule.block_duration
            self.clients[client_key] = state
            
            logger.warning(
                "Rate limit exceeded for client",
                client=client_key,
                requests=current_count,
                limit=rule.requests,
                blocked_until=state.blocked_until
            )
            
            return False, {
                "error": "Rate limit exceeded",
                "requests": current_count,
                "limit": rule.requests,
                "window": rule.window,
                "blocked_for": rule.block_duration,
                "retry_after": rule.block_duration
            }
        
        # Allow request - add to tracking
        state.requests.append(now)
        state.blocked_until = 0  # Reset block if it was set
        self.clients[client_key] = state
        
        return True, {
            "requests_remaining": rule.requests - current_count - 1,
            "reset_time": int(now + rule.window)
        }
    
    def _check_token_bucket(
        self, 
        client_key: str, 
        rule: RateLimitRule, 
        now: float
    ) -> Tuple[bool, Dict]:
        """Check token bucket rate limit"""
        state = self.clients.get(client_key, ClientState())
        
        # Initialize token bucket
        if state.last_refill == 0:
            state.tokens = rule.requests
            state.last_refill = now
        
        # Refill tokens based on time elapsed
        time_passed = now - state.last_refill
        tokens_to_add = int(time_passed * rule.requests / rule.window)
        
        if tokens_to_add > 0:
            state.tokens = min(rule.requests, state.tokens + tokens_to_add)
            state.last_refill = now
        
        # Check if client is blocked
        if state.blocked_until > now:
            remaining_block = int(state.blocked_until - now)
            return False, {
                "error": "Rate limit exceeded - blocked",
                "blocked_for": remaining_block,
                "retry_after": remaining_block
            }
        
        # Check if tokens available
        if state.tokens < 1:
            # Block if no tokens and implement exponential backoff
            state.blocked_until = now + rule.block_duration
            self.clients[client_key] = state
            
            return False, {
                "error": "Rate limit exceeded - no tokens",
                "tokens": state.tokens,
                "retry_after": rule.block_duration
            }
        
        # Consume token
        state.tokens -= 1
        state.blocked_until = 0
        self.clients[client_key] = state
        
        return True, {
            "tokens_remaining": int(state.tokens),
            "refill_rate": f"{rule.requests}/{rule.window}s"
        }
    
    async def check_rate_limit(self, request: Request) -> Tuple[bool, Dict]:
        """Check if request should be rate limited"""
        try:
            self._cleanup_old_entries()
            
            client_key = self._get_client_key(request)
            
            # Extract IP from client key for whitelist check
            client_ip = client_key.split(":")[-1]  # Get IP part
            
            # Skip rate limiting for whitelisted IPs in development
            if self._is_whitelisted(client_ip):
                logger.debug(f"Rate limit bypassed for whitelisted IP: {client_ip}")
                return True, {"whitelisted": True, "client_ip": client_ip}
            
            rule = self._get_rule_for_path(request.url.path)
            now = time.time()
            
            logger.debug(
                "Rate limit check",
                client_ip=client_ip,
                path=request.url.path,
                rule_requests=rule.requests,
                rule_window=rule.window,
                environment=self.settings.environment
            )
            
            if rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return self._check_sliding_window(client_key, rule, now)
            elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return self._check_token_bucket(client_key, rule, now)
            else:
                # Default to sliding window
                return self._check_sliding_window(client_key, rule, now)
                
        except Exception as e:
            logger.error("Error in rate limiter", error=str(e), exc_info=True)
            # Fail open - allow request if rate limiter fails
            return True, {"error": "Rate limiter unavailable"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = AdvancedRateLimiter()
    
    async def dispatch(self, request: Request, call_next):
        # Check rate limit
        allowed, info = await self.rate_limiter.check_rate_limit(request)
        
        if not allowed:
            # Add rate limit headers
            headers = {
                "X-RateLimit-Error": info.get("error", "Rate limit exceeded"),
                "Retry-After": str(info.get("retry_after", 60))
            }
            
            if "blocked_for" in info:
                headers["X-RateLimit-Blocked-For"] = str(info["blocked_for"])
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": info.get("error", "Too many requests"),
                    "retry_after": info.get("retry_after", 60)
                },
                headers=headers
            )
        
        # Process the request and add rate limit headers to all responses
        response = await call_next(request)
        
        # Add rate limit info headers to all responses
        if "requests_remaining" in info:
            response.headers["X-RateLimit-Remaining"] = str(info["requests_remaining"])
        
        if "reset_time" in info:
            response.headers["X-RateLimit-Reset"] = str(info["reset_time"])
            
        if "tokens_remaining" in info:
            response.headers["X-RateLimit-Tokens"] = str(info["tokens_remaining"])
        
        return response