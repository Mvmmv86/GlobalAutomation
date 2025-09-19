"""Versão simplificada para testar inicialização"""

from fastapi import FastAPI
from infrastructure.config.settings import get_settings

# Create simple FastAPI app for testing
app = FastAPI(title="Test API", version="1.0.0")


@app.get("/")
async def root():
    """Test endpoint"""
    settings = get_settings()
    return {
        "service": "TradingView Gateway API - TEST",
        "version": settings.version,
        "environment": settings.environment,
        "status": "healthy",
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    print(f"🚀 Starting test server on port {settings.port}")
    uvicorn.run(
        "test_main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
        log_level="info",
    )
