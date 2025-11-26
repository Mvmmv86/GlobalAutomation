"""Security Headers Middleware for FastAPI"""

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""
    
    def __init__(self, app, config=None):
        super().__init__(app)
        self.config = config or {}
        self.is_production = self.config.get("environment") == "production"
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response, request)
        
        return response
    
    def _add_security_headers(self, response: Response, request: Request):
        """Add comprehensive security headers"""
        
        # Content Security Policy (CSP)
        if self.is_production:
            # Strict CSP for production
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https: wss:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        else:
            # More permissive CSP for development
            csp = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval' *; "
                "frame-ancestors 'none'; "
                "base-uri 'self'"
            )
        
        response.headers["Content-Security-Policy"] = csp
        
        # Strict Transport Security (HSTS) - only in production with HTTPS
        if self.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # X-Content-Type-Options - prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options - prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection - XSS protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy - control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (formerly Feature Policy)
        permissions_policy = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "accelerometer=(), "
            "gyroscope=()"
        )
        response.headers["Permissions-Policy"] = permissions_policy
        
        # Cross-Origin Embedder Policy
        if self.is_production:
            response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        
        # Cross-Origin Opener Policy  
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        
        # Cross-Origin Resource Policy
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        
        # Server header - remove sensitive information
        response.headers["Server"] = "TradingView Gateway"
        
        # X-Powered-By - remove if exists
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]
        
        # Cache Control for sensitive endpoints
        if self._is_sensitive_endpoint(request.url.path):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Add custom security headers for API responses
        if request.url.path.startswith("/api/"):
            response.headers["X-API-Version"] = "1.0"
            response.headers["X-Rate-Limit-Policy"] = "enforced"
        
        # HPKP (HTTP Public Key Pinning) - only in production with proper certificates
        # This is commented out as it requires careful certificate management
        # if self.is_production:
        #     response.headers["Public-Key-Pins"] = 'pin-sha256="base64+primary+key"; pin-sha256="base64+backup+key"; max-age=5184000'
    
    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Check if endpoint handles sensitive data"""
        sensitive_patterns = [
            "/api/v1/auth/",
            "/api/v1/users/",
            "/api/v1/exchange-accounts/",
            "/api/v1/orders/",
            "/api/v1/positions/"
        ]
        
        return any(path.startswith(pattern) for pattern in sensitive_patterns)


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced CORS middleware with security considerations"""
    
    def __init__(self, app, allowed_origins=None, is_production=False):
        super().__init__(app)
        self.allowed_origins = allowed_origins or []
        self.is_production = is_production
    
    async def dispatch(self, request: Request, call_next):
        # Handle preflight requests
        if request.method == "OPTIONS":
            return self._handle_preflight(request)
        
        response = await call_next(request)
        
        # Add CORS headers to actual requests
        self._add_cors_headers(request, response)
        
        return response
    
    def _handle_preflight(self, request: Request) -> Response:
        """Handle CORS preflight requests"""
        origin = request.headers.get("origin")
        
        if not self._is_origin_allowed(origin):
            # Return 403 for disallowed origins in production
            if self.is_production:
                return Response(status_code=403, content="Origin not allowed")
        
        headers = {
            "Access-Control-Allow-Origin": origin if self._is_origin_allowed(origin) else "null",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": (
                "Authorization, Content-Type, X-Requested-With, "
                "X-API-Key, X-Client-Version, X-Request-ID"
            ),
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "86400",  # 24 hours
            "Vary": "Origin"
        }
        
        return Response(status_code=200, headers=headers)
    
    def _add_cors_headers(self, request: Request, response: Response):
        """Add CORS headers to response"""
        origin = request.headers.get("origin")
        
        if self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        elif not self.is_production:
            # Allow all origins in development
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Vary"] = "Origin"
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is in allowed list"""
        if not origin:
            return False
        
        # Allow localhost in development
        if not self.is_production and ("localhost" in origin or "127.0.0.1" in origin):
            return True
        
        return origin in self.allowed_origins


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for request validation and sanitization"""
    
    def __init__(self, app):
        super().__init__(app)
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        self.suspicious_patterns = [
            # SQL Injection patterns
            r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into)",
            # XSS patterns
            r"(?i)(<script|javascript:|onerror=|onload=)",
            # Path traversal
            r"(\.\.\/|\.\.\\|%2e%2e%2f)",
            # Command injection
            r"(;|\||&|`|\$\(|\$\{)"
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Validate request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            logger.warning(
                "Request too large",
                client_ip=request.client.host if request.client else "unknown",
                content_length=content_length,
                path=request.url.path
            )
            return Response(
                status_code=413,
                content="Request entity too large",
                headers={"Content-Type": "text/plain"}
            )
        
        # Validate request headers for suspicious content
        if self._contains_suspicious_content(request):
            logger.warning(
                "Suspicious request detected",
                client_ip=request.client.host if request.client else "unknown",
                path=request.url.path,
                user_agent=request.headers.get("user-agent", "")
            )
            return Response(
                status_code=400,
                content="Bad request",
                headers={"Content-Type": "text/plain"}
            )
        
        response = await call_next(request)
        return response
    
    def _contains_suspicious_content(self, request: Request) -> bool:
        """Check if request contains suspicious patterns"""
        import re
        
        # Check URL path
        path = str(request.url.path).lower()
        for pattern in self.suspicious_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        
        # Check query parameters
        query = str(request.url.query).lower()
        for pattern in self.suspicious_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        
        # Check user agent for known malicious patterns
        user_agent = request.headers.get("user-agent", "").lower()
        malicious_ua_patterns = [
            "sqlmap", "nmap", "nikto", "dirb", "masscan", 
            "zap", "burp", "havij", "sqlninja"
        ]
        
        for pattern in malicious_ua_patterns:
            if pattern in user_agent:
                return True
        
        return False