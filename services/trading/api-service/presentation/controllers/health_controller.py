"""Health check controller"""

from fastapi import APIRouter

from presentation.schemas.webhook import HealthResponse
from infrastructure.config.settings import get_settings


def create_health_router() -> APIRouter:
    """Create health check router"""

    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("/", response_model=HealthResponse)
    async def health_check():
        """
        Basic health check endpoint

        Returns application status and basic information
        """
        settings = get_settings()

        return HealthResponse(
            status="healthy",
            version=settings.version,
            environment=settings.environment,
            services={
                "api": "healthy",
                "database": "unknown",  # Will be enhanced with actual checks
                "redis": "unknown",  # Will be enhanced with actual checks
            },
        )

    @router.get("/ready", response_model=HealthResponse)
    async def readiness_check():
        """
        Readiness check for Kubernetes

        Checks if application is ready to serve traffic
        """
        settings = get_settings()

        # TODO: Add actual readiness checks for:
        # - Database connectivity
        # - Redis connectivity
        # - External service dependencies

        return HealthResponse(
            status="ready",
            version=settings.version,
            environment=settings.environment,
            services={
                "api": "ready",
                "database": "ready",
                "redis": "ready",
            },
        )

    @router.get("/live", response_model=HealthResponse)
    async def liveness_check():
        """
        Liveness check for Kubernetes

        Simple check to verify application is running
        """
        settings = get_settings()

        return HealthResponse(
            status="alive",
            version=settings.version,
            environment=settings.environment,
            services={
                "api": "alive",
            },
        )

    return router
