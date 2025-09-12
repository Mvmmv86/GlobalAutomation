#!/usr/bin/env python3
"""Simple FastAPI server without database for frontend testing"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
import jwt
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional


# Simple models
class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


class UserProfile(BaseModel):
    id: str = "demo-user-123"
    email: str = "demo@tradingview.com"
    name: str = "Demo User"
    is_active: bool = True
    is_verified: bool = True
    totp_enabled: bool = False
    created_at: str = "2024-01-01T00:00:00Z"
    last_login_at: str = None


# Simple JWT settings
SECRET_KEY = "demo-secret-key-for-testing-only"
ALGORITHM = "HS256"

# Create app
app = FastAPI(
    title="TradingView Gateway API - Demo Mode",
    description="Simplified API for frontend testing",
    version="1.0.0-demo",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Static files removed - using React frontend only

# Simple demo credentials
DEMO_USERS = {
    "demo@tradingview.com": {"password": "demo123456", "profile": UserProfile()}
}


def create_access_token(user_email: str):
    """Create simple JWT token"""
    expire = datetime.utcnow() + timedelta(minutes=30)
    payload = {
        "sub": "demo-user-123",
        "email": user_email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_email: str):
    """Create refresh token"""
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {
        "sub": "demo-user-123",
        "email": user_email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "TradingView Gateway API - Demo Mode",
        "version": "1.0.0-demo",
        "environment": "development",
        "status": "healthy",
        "note": "Running without database for frontend testing",
    }


# Login redirect - redirect to React frontend
@app.get("/login")
async def login_page():
    return RedirectResponse(url="http://localhost:3000")


# Auth endpoints
@app.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Simple login endpoint"""
    print(f"🔐 Login attempt: {request.email}")

    # Check demo user
    if request.email in DEMO_USERS:
        user_data = DEMO_USERS[request.email]
        if request.password == user_data["password"]:
            access_token = create_access_token(request.email)
            refresh_token = create_refresh_token(request.email)

            print(f"✅ Login successful for: {request.email}")

            return LoginResponse(
                access_token=access_token, refresh_token=refresh_token, expires_in=1800
            )

    print(f"❌ Login failed for: {request.email}")
    raise HTTPException(status_code=401, detail="Incorrect email or password")


@app.get("/api/v1/auth/me", response_model=UserProfile)
async def get_profile():
    """Get user profile (simplified - no auth check for demo)"""
    print("👤 Profile request")
    return DEMO_USERS["demo@tradingview.com"]["profile"]


# Health endpoint
@app.get("/api/v1/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0-demo",
        "database": "disconnected (demo mode)",
        "services": {"api": "running", "auth": "simplified", "webhooks": "mock"},
    }


# Webhook endpoints
@app.post("/api/v1/webhooks/tv/test-simple")
async def test_tradingview_webhook_simple(request: Request):
    """
    Simple TradingView webhook test (no database required)
    """
    try:
        # Get request body
        body = await request.body()

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=400, content={"error": "Invalid JSON payload"}
            )

        # Basic validation
        required_fields = ["ticker", "action"]
        missing_fields = [field for field in required_fields if field not in payload]

        if missing_fields:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Missing required fields",
                    "missing_fields": missing_fields,
                },
            )

        # Mock processing result
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "TradingView webhook received successfully",
                "payload": payload,
                "processing_result": {
                    "orders_created": 1,
                    "orders_executed": 1
                    if payload.get("order_type", "market") == "market"
                    else 0,
                    "orders_failed": 0,
                },
                "test_mode": True,
            },
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)},
        )


@app.post("/api/v1/webhooks/tv/{webhook_path:path}")
async def receive_tradingview_webhook_demo(
    webhook_path: str,
    request: Request,
    x_tradingview_signature: Optional[str] = Header(
        None, alias="x-tradingview-signature"
    ),
):
    """
    Demo TradingView webhook with HMAC validation
    Aceita payload completo baseado no frontend
    """
    try:
        # Get request body as JSON
        body = await request.body()

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=400, content={"error": "Invalid JSON payload"}
            )

        # Demo webhook validation (webhook_path deve ser webhook_demo_123)
        if webhook_path != "webhook_demo_123":
            return JSONResponse(
                status_code=404,
                content={"error": "Webhook not found", "code": "WEBHOOK_NOT_FOUND"},
            )

        # HMAC signature verification (demo)
        demo_secret = "minha_secret_key_super_secreta_123"
        if x_tradingview_signature:
            payload_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)

            # Parse signature
            signature = x_tradingview_signature
            if signature.startswith("sha256="):
                signature = signature[7:]  # Remove 'sha256=' prefix

            # Verify HMAC
            expected_signature = hmac.new(
                demo_secret.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_signature, signature):
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid signature", "code": "INVALID_SIGNATURE"},
                )

        # Payload validation - suporta tanto formato simples quanto completo
        required_fields = ["ticker", "action"]
        missing_fields = [field for field in required_fields if field not in payload]

        if missing_fields:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Missing required fields",
                    "missing_fields": missing_fields,
                    "code": "INVALID_FORMAT",
                },
            )

        # Processar payload completo ou simples
        is_complete_payload = (
            "position" in payload
            and "risk_management" in payload
            and "exchange_config" in payload
        )

        # Extrair configurações se payload completo
        config_summary = {}
        if is_complete_payload:
            position_config = payload.get("position", {})
            risk_config = payload.get("risk_management", {})
            exchange_config = payload.get("exchange_config", {})
            strategy_config = payload.get("strategy", {})

            config_summary = {
                "leverage": position_config.get("leverage", 10),
                "margin_mode": position_config.get("margin_mode", "cross"),
                "position_mode": position_config.get("position_mode", "one-way"),
                "stop_loss_enabled": payload.get("stop_loss", {}).get("enabled", False),
                "take_profit_enabled": payload.get("take_profit", {}).get(
                    "enabled", False
                ),
                "exchange": exchange_config.get("exchange", "unknown"),
                "strategy": strategy_config.get("name", "unknown"),
                "risk_size_type": risk_config.get("position_size_type", "fixed"),
            }

        # Simular processamento baseado na configuração
        orders_created = 1
        orders_executed = 1 if payload.get("order_type", "market") == "market" else 0

        # Simular stop loss / take profit orders
        if config_summary.get("stop_loss_enabled"):
            orders_created += 1
        if config_summary.get("take_profit_enabled"):
            orders_created += 1

        # Mock processing result
        processing_result = {
            "success": True,
            "message": "Webhook processed successfully",
            "delivery_id": f"demo-delivery-{hash(webhook_path) % 10000}",
            "webhook_id": webhook_path,
            "orders_created": orders_created,
            "orders_executed": orders_executed,
            "processing_time_ms": 75 if is_complete_payload else 50,
            "hmac_verified": x_tradingview_signature is not None,
            "payload_type": "complete" if is_complete_payload else "simple",
            "config_applied": config_summary,
            "exchange_adapters": [],
        }

        # Simular adaptação para exchanges se payload completo
        if is_complete_payload:
            exchange = config_summary.get("exchange", "binance")

            # Mock Binance adapter
            binance_order = {
                "symbol": payload["ticker"],
                "side": payload["action"].upper(),
                "type": payload.get("order_type", "market").upper(),
                "quantity": str(payload.get("quantity", 0.1)),
                "leverage": config_summary["leverage"],
                "marginType": config_summary["margin_mode"].upper(),
            }

            processing_result["exchange_adapters"].append(
                {"exchange": "binance", "order": binance_order, "status": "simulated"}
            )

        print(f"✅ TradingView webhook processed: {webhook_path}")
        print(f"📦 Payload type: {'Complete' if is_complete_payload else 'Simple'}")
        print(f"🔐 HMAC verified: {x_tradingview_signature is not None}")
        if is_complete_payload:
            print(f"⚙️ Config applied: {config_summary}")

        return JSONResponse(status_code=200, content=processing_result)

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        import traceback

        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)},
        )


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Simple Demo Server...")
    print("📱 Frontend: http://localhost:3000")
    print("🔗 Backend: http://localhost:8000")
    print("🔑 Login: demo@tradingview.com / demo123456")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, log_level="info")
