#!/usr/bin/env python3
"""Mock API simples para testar frontend React"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import hashlib
import secrets
from datetime import datetime


# Models
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_active: bool
    is_verified: bool
    created_at: str


class ExchangeAccountRequest(BaseModel):
    name: str
    exchange: str
    apiKey: str
    secretKey: str
    passphrase: str = None
    testnet: bool = True
    isDefault: bool = False


class ExchangeAccountResponse(BaseModel):
    id: str
    name: str
    exchange: str
    testnet: bool
    is_active: bool
    is_default: bool
    created_at: str


# Mock database
mock_users = {}
mock_sessions = {}
mock_exchange_accounts = []

# Create FastAPI app
app = FastAPI(title="Mock Trading API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://192.168.65.6:3001",
        "http://192.168.65.3:3001",
        "http://172.19.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


def hash_password(password: str) -> str:
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token() -> str:
    """Generate simple token"""
    return f"mock_token_{secrets.token_urlsafe(32)}"


@app.get("/")
async def root():
    return {
        "service": "Mock Trading API",
        "version": "1.0.0",
        "status": "healthy",
        "environment": "development",
    }


@app.get("/api/v1/health/")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": "development",
        "services": {"api": "healthy", "database": "healthy"},
    }


@app.post("/api/v1/auth/register")
async def register(request: RegisterRequest):
    """Register new user"""
    # Check if user exists
    if request.email in mock_users:
        raise HTTPException(
            status_code=400, detail="User with this email already exists"
        )

    # Create user
    user_id = f"user_{len(mock_users) + 1}"
    mock_users[request.email] = {
        "id": user_id,
        "email": request.email,
        "name": request.name,
        "password_hash": hash_password(request.password),
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.now().isoformat(),
    }

    return {
        "data": {
            "user_id": user_id,
            "email": request.email,
            "message": "User registered successfully",
        }
    }


@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    """Login user"""
    # Find user
    if request.email not in mock_users:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    user = mock_users[request.email]

    # Check password
    if user["password_hash"] != hash_password(request.password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    # Generate tokens
    access_token = generate_token()
    refresh_token = generate_token()

    # Store session
    mock_sessions[access_token] = {
        "user_email": request.email,
        "created_at": datetime.now().isoformat(),
    }

    return {
        "data": TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=1800,  # 30 minutes
        ).dict()
    }


@app.get("/api/v1/auth/me")
async def get_current_user():
    """Get current user info (mock - sem autenticação por agora)"""
    # Mock user para teste
    return {
        "data": UserResponse(
            id="user_1",
            email="test@example.com",
            name="Test User",
            is_active=True,
            is_verified=True,
            created_at=datetime.now().isoformat(),
        ).dict()
    }


# Trading endpoints (mock data)
@app.get("/api/v1/positions")
async def get_positions():
    return {
        "success": True,
        "data": [
            {
                "id": "1",
                "symbol": "BTCUSDT",
                "side": "long",
                "size": 0.5,
                "entryPrice": 43250.00,
                "currentPrice": 43580.50,
                "pnl": 165.25,
                "pnlPercent": 0.76,
                "leverage": 10,
                "margin": 2162.50,
            }
        ],
    }


@app.get("/api/v1/accounts")
async def get_accounts():
    return {
        "success": True,
        "data": [
            {
                "id": "binance-main",
                "name": "Binance Principal",
                "exchange": "binance",
                "balance": 15420.85,
                "availableBalance": 12250.30,
                "currency": "USDT",
            }
        ],
    }


# Exchange Accounts endpoints
@app.get("/api/v1/exchange-accounts")
async def get_exchange_accounts():
    """Get all exchange accounts"""
    return {"success": True, "data": mock_exchange_accounts}


@app.post("/api/v1/exchange-accounts")
async def create_exchange_account(request: ExchangeAccountRequest):
    """Create new exchange account"""
    # Create new account
    account_id = f"exchange_{len(mock_exchange_accounts) + 1}"
    new_account = {
        "id": account_id,
        "name": request.name,
        "exchange": request.exchange,
        "testnet": request.testnet,
        "is_active": True,
        "is_default": request.isDefault,
        "created_at": datetime.now().isoformat(),
        # Keys are encrypted in real implementation
        "api_key_encrypted": f"encrypted_{request.apiKey[:10]}...",
        "secret_key_encrypted": f"encrypted_{request.secretKey[:10]}...",
    }

    # If this is set as default, remove default from others
    if request.isDefault:
        for account in mock_exchange_accounts:
            account["is_default"] = False

    mock_exchange_accounts.append(new_account)

    return {
        "success": True,
        "data": ExchangeAccountResponse(
            id=new_account["id"],
            name=new_account["name"],
            exchange=new_account["exchange"],
            testnet=new_account["testnet"],
            is_active=new_account["is_active"],
            is_default=new_account["is_default"],
            created_at=new_account["created_at"],
        ),
        "message": "Exchange account created successfully",
    }


@app.delete("/api/v1/exchange-accounts/{account_id}")
async def delete_exchange_account(account_id: str):
    """Delete exchange account"""
    global mock_exchange_accounts

    # Find and remove account
    original_length = len(mock_exchange_accounts)
    mock_exchange_accounts = [
        acc for acc in mock_exchange_accounts if acc["id"] != account_id
    ]

    if len(mock_exchange_accounts) == original_length:
        raise HTTPException(status_code=404, detail="Account not found")

    return {"success": True, "message": "Exchange account deleted successfully"}


if __name__ == "__main__":
    print("🚀 Mock API starting on http://localhost:8000")
    print("📊 Available endpoints:")
    print("   POST /api/v1/auth/register")
    print("   POST /api/v1/auth/login")
    print("   GET  /api/v1/auth/me")
    print("   GET  /api/v1/health/")
    print("   GET  /api/v1/positions")
    print("   GET  /api/v1/accounts")
    print("\n💡 Frontend should use: VITE_API_URL=http://localhost:8000")

    uvicorn.run(
        "mock_api_simple:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )
