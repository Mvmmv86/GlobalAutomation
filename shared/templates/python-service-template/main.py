"""FastAPI Service Template - Base for new services"""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting service", service_name="{SERVICE_NAME}")
    
    try:
        # Initialize database connections
        # await database.connect()
        logger.info("Database connected successfully")
        
        # Initialize Redis
        # await redis.connect()
        logger.info("Redis connected successfully")
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down service", service_name="{SERVICE_NAME}")
        
        # Close connections
        # await database.disconnect()
        # await redis.disconnect()
        
        logger.info("Shutdown completed")


def create_app() -> FastAPI:
    """Create FastAPI application with all configurations"""
    
    app = FastAPI(
        title="{SERVICE_TITLE}",
        description="{SERVICE_DESCRIPTION}",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # Add rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests"""
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_ip=get_remote_address(request),
        )
        
        try:
            response = await call_next(request)
            
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                client_ip=get_remote_address(request),
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                client_ip=get_remote_address(request),
                error=str(e),
            )
            raise
    
    # Error handlers
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle ValueError exceptions"""
        logger.warning("ValueError occurred", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=400, 
            content={"error": "Bad Request", "detail": str(exc)}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions"""
        logger.error(
            "Unhandled exception occurred",
            error=str(exc),
            path=request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred"
            },
        )
    
    return app


# Create app instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "{SERVICE_NAME}",
        "version": "1.0.0",
        "status": "healthy",
        "description": "{SERVICE_DESCRIPTION}"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "{SERVICE_NAME}",
        "timestamp": "2025-01-15T10:00:00Z"
    }


# Add your service-specific routes here
@app.get("/api/v1/{service_path}")
async def service_endpoint():
    """Service-specific endpoint"""
    return {
        "message": "Service endpoint working",
        "service": "{SERVICE_NAME}"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

