#!/usr/bin/env python3
"""Mock API Server for Testing the Trading Platform"""

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import jwt
import bcrypt
import uuid
import json

# Initialize FastAPI app
app = FastAPI(
    title="Trading Platform Mock API",
    description="Mock API server for testing the trading platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
SECRET_KEY = "mock_secret_key_for_testing_only"
ALGORITHM = "HS256"

# In-memory storage for demo
users_db = {}
orders_db = {}
webhooks_db = {}
positions_db = {}

# Demo users
demo_users = [
    {
        "id": str(uuid.uuid4()),
        "email": "admin@trading.com",
        "password": "Admin@123",
        "name": "Admin User",
        "is_active": True,
        "is_verified": True
    },
    {
        "id": str(uuid.uuid4()),
        "email": "trader@demo.com",
        "password": "Trader@123",
        "name": "Demo Trader",
        "is_active": True,
        "is_verified": True
    },
    {
        "id": str(uuid.uuid4()),
        "email": "test@test.com",
        "password": "Test@123",
        "name": "Test User",
        "is_active": True,
        "is_verified": True
    }
]

# Initialize demo users
for user in demo_users:
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(user["password"].encode('utf-8'), salt).decode('utf-8')
    users_db[user["email"]] = {
        "id": user["id"],
        "email": user["email"],
        "password_hash": password_hash,
        "name": user["name"],
        "is_active": user["is_active"],
        "is_verified": user["is_verified"],
        "created_at": datetime.utcnow().isoformat()
    }

# Pydantic models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    user: Dict[str, Any]

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_active: bool
    is_verified: bool
    created_at: str

class OrderRequest(BaseModel):
    symbol: str
    side: str  # buy/sell
    type: str  # market/limit
    quantity: float
    price: Optional[float] = None

class OrderResponse(BaseModel):
    id: str
    symbol: str
    side: str
    type: str
    quantity: float
    price: Optional[float]
    status: str
    created_at: str

class WebhookRequest(BaseModel):
    name: str
    url: str
    secret: Optional[str] = None
    active: bool = True

# Helper functions
def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=1)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return email
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# Routes
@app.get("/")
async def root():
    return {
        "service": "Trading Platform Mock API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/v1/auth/login",
            "dashboard": "/api/v1/dashboard",
            "orders": "/api/v1/orders",
            "webhooks": "/api/v1/webhooks"
        }
    }

@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "mock-api",
        "database": "in-memory"
    }

@app.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    user = users_db.get(request.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not bcrypt.checkpw(request.password.encode('utf-8'), user["password_hash"].encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create tokens
    access_token = create_access_token({"sub": user["email"]})
    refresh_token = create_access_token({"sub": user["email"]}, timedelta(days=7))
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "is_active": user["is_active"],
            "is_verified": user["is_verified"]
        }
    )

@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    if request.email in users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(request.password.encode('utf-8'), salt).decode('utf-8')
    
    # Create user
    user_id = str(uuid.uuid4())
    users_db[request.email] = {
        "id": user_id,
        "email": request.email,
        "password_hash": password_hash,
        "name": request.name,
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.utcnow().isoformat()
    }
    
    return {
        "id": user_id,
        "email": request.email,
        "name": request.name,
        "message": "User registered successfully"
    }

@app.get("/api/v1/auth/me")
async def get_current_user(email: str = Depends(verify_token)):
    user = users_db.get(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "is_active": user["is_active"],
        "is_verified": user["is_verified"]
    }

@app.get("/api/v1/dashboard")
async def get_dashboard(email: str = Depends(verify_token)):
    # Mock dashboard data
    user_orders = [o for o in orders_db.values() if o.get("user_email") == email]
    
    return {
        "stats": {
            "total_orders": len(user_orders),
            "active_positions": 5,
            "total_profit": 1250.50,
            "win_rate": 0.65,
            "total_volume": 50000.00
        },
        "recent_orders": user_orders[-5:] if user_orders else [],
        "chart_data": {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "values": [1200, 1400, 1100, 1600, 1800, 1500, 2000]
        }
    }

@app.get("/api/v1/orders")
async def get_orders(email: str = Depends(verify_token)):
    user_orders = [o for o in orders_db.values() if o.get("user_email") == email]
    return {
        "orders": user_orders,
        "total": len(user_orders)
    }

@app.post("/api/v1/orders", response_model=OrderResponse)
async def create_order(request: OrderRequest, email: str = Depends(verify_token)):
    order_id = str(uuid.uuid4())
    order = {
        "id": order_id,
        "user_email": email,
        "symbol": request.symbol,
        "side": request.side,
        "type": request.type,
        "quantity": request.quantity,
        "price": request.price,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    orders_db[order_id] = order
    
    return OrderResponse(**order)

@app.get("/api/v1/webhooks")
async def get_webhooks(email: str = Depends(verify_token)):
    user_webhooks = [w for w in webhooks_db.values() if w.get("user_email") == email]
    return {
        "webhooks": user_webhooks,
        "total": len(user_webhooks)
    }

@app.post("/api/v1/webhooks")
async def create_webhook(request: WebhookRequest, email: str = Depends(verify_token)):
    webhook_id = str(uuid.uuid4())
    webhook = {
        "id": webhook_id,
        "user_email": email,
        "name": request.name,
        "url": request.url,
        "secret": request.secret or str(uuid.uuid4()),
        "active": request.active,
        "created_at": datetime.utcnow().isoformat()
    }
    webhooks_db[webhook_id] = webhook
    
    return webhook

@app.get("/api/v1/positions")
async def get_positions(email: str = Depends(verify_token)):
    # Mock positions data
    return {
        "positions": [
            {
                "id": "1",
                "symbol": "BTC/USDT",
                "side": "long",
                "quantity": 0.5,
                "entry_price": 45000,
                "current_price": 46500,
                "pnl": 750,
                "pnl_percentage": 3.33
            },
            {
                "id": "2",
                "symbol": "ETH/USDT",
                "side": "long",
                "quantity": 10,
                "entry_price": 3000,
                "current_price": 3150,
                "pnl": 1500,
                "pnl_percentage": 5.0
            }
        ],
        "total_pnl": 2250,
        "total_positions": 2
    }

@app.get("/api/v1/exchange-accounts")
async def get_exchange_accounts(email: str = Depends(verify_token)):
    return {
        "accounts": [
            {
                "id": "1",
                "name": "Binance Main",
                "exchange": "binance",
                "active": True,
                "testnet": False
            },
            {
                "id": "2",
                "name": "Bybit Test",
                "exchange": "bybit",
                "active": True,
                "testnet": True
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Mock API Server...")
    print("\n" + "="*60)
    print("📌 DEMO USERS AVAILABLE:")
    print("="*60)
    for user in demo_users:
        print(f"\n📧 Email: {user['email']}")
        print(f"🔑 Password: {user['password']}")
        print(f"👤 Name: {user['name']}")
    print("\n" + "="*60)
    print("\n✅ Server running at: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔄 Redoc: http://localhost:8000/redoc")
    print("\nPress CTRL+C to stop the server")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)