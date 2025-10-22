"""Health check controller"""

from fastapi import APIRouter
import httpx
import structlog

from presentation.schemas.webhook import HealthResponse
from infrastructure.config.settings import get_settings

logger = structlog.get_logger()


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

    @router.get("/public-ips")
    async def get_public_ips():
        """
        Get public IPs of the server for API Key configuration

        Returns the public IPs that clients should whitelist in their
        exchange API key settings (Binance, Bybit, etc.)
        """
        ips = []

        try:
            # Try multiple IP detection services
            services = [
                "https://api.ipify.org?format=json",
                "https://api64.ipify.org?format=json",
                "https://icanhazip.com",
                "https://ifconfig.me/ip"
            ]

            async with httpx.AsyncClient(timeout=5.0) as client:
                for service in services:
                    try:
                        response = await client.get(service)
                        if response.status_code == 200:
                            if "ipify" in service:
                                data = response.json()
                                ip = data.get("ip")
                            else:
                                ip = response.text.strip()

                            if ip and ip not in ips:
                                ips.append(ip)
                                logger.info(f"✅ Detected public IP from {service}: {ip}")

                    except Exception as e:
                        logger.warning(f"⚠️ Failed to get IP from {service}: {e}")
                        continue

        except Exception as e:
            logger.error(f"❌ Error detecting public IPs: {e}")

        # Fallback: If we're behind Cloudflare (Digital Ocean often is)
        # Add known Cloudflare IP ranges or detected IPs
        if not ips:
            logger.warning("⚠️ Could not detect IPs, using fallback")
            ips = ["Unable to detect - Please contact support"]

        return {
            "success": True,
            "ips": ips,
            "count": len(ips),
            "message": "Configure these IPs in your exchange API key settings"
        }

    return router
