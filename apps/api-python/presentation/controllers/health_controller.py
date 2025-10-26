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

    @router.get("/whitelist-ips")
    async def get_whitelist_ips():
        """
        Get FIXED list of IPs for exchange API key whitelisting

        Similar to Insilico Terminal, this provides a fixed list of IPs
        that clients should add to their Binance/Bybit API key whitelist.

        These IPs represent all possible server IPs (current + backups).
        """
        # Fixed list of IPs from our infrastructure
        # Includes current + historical IPs to prevent breaking if IP changes
        fixed_ips = [
            "178.128.19.69",    # Digital Ocean production (current)
            "159.223.46.195",   # Singapore primary
            "143.198.80.231",   # Singapore backup
            "134.199.194.84",   # USA backup 1
            "129.212.187.46",   # USA backup 2
            "134.199.195.235",  # USA backup 3
        ]

        return {
            "success": True,
            "ips": fixed_ips,
            "count": len(fixed_ips),
            "message": "Add ALL these IPs to your exchange API key whitelist (separated by commas or spaces)",
            "instructions": {
                "binance": "Go to Binance → API Management → Edit Key → Restrict access to trusted IPs only → Paste all IPs separated by spaces",
                "bybit": "Go to Bybit → API Management → Edit Key → IP restriction → Paste all IPs separated by commas",
                "tip": "Whitelisting ALL IPs ensures your connection works even if our server IP changes"
            }
        }

    return router
