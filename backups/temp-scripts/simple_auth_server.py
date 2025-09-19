#!/usr/bin/env python3
"""Simple authentication server for testing"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import bcrypt
import jwt
import uvicorn
from datetime import datetime, timedelta
from typing import Optional
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import sqlite3
import json
import os

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3002", "http://127.0.0.1:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)
SECRET_KEY = "super-secret-key-for-testing"
ALGORITHM = "HS256"

# Database file
DB_FILE = "trading_platform.db"

def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create exchange_accounts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exchange_accounts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            exchange TEXT NOT NULL,
            api_key TEXT NOT NULL,
            secret_key TEXT NOT NULL,
            testnet BOOLEAN DEFAULT 1,
            is_default BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    
    # Create synced_data table for orders, balances, positions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS synced_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            data_type TEXT NOT NULL,
            data_json TEXT NOT NULL,
            synced_at TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES exchange_accounts (id)
        )
    """)
    
    conn.commit()
    conn.close()

def get_all_exchange_accounts():
    """Get all exchange accounts from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM exchange_accounts")
    accounts = []
    for row in cursor.fetchall():
        accounts.append({
            "id": row[0],
            "name": row[1],
            "exchange": row[2],
            "apiKey": "***" + row[3][-4:] if len(row[3]) > 4 else "***",
            "secretKey": "***" + row[4][-4:] if len(row[4]) > 4 else "***", 
            "testnet": bool(row[5]),
            "isDefault": bool(row[6]),
            "isActive": bool(row[7]),
            "createdAt": row[8]
        })
    conn.close()
    return accounts

def save_exchange_account(account_data):
    """Save exchange account to database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO exchange_accounts (id, name, exchange, api_key, secret_key, testnet, is_default, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        account_data["id"],
        account_data["name"],
        account_data["exchange"],
        account_data["api_key"],  # Store real key
        account_data["secret_key"],  # Store real secret
        account_data["testnet"],
        account_data["is_default"],
        account_data["is_active"],
        account_data["created_at"]
    ))
    conn.commit()
    conn.close()

def get_real_credentials(account_id):
    """Get real API credentials for an account"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT api_key, secret_key, testnet FROM exchange_accounts WHERE id = ?", (account_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"api_key": result[0], "secret_key": result[1], "testnet": bool(result[2])}
    return None

# Initialize database on startup
init_database()

# In-memory storage for synced data (still using for performance)
SYNCED_ORDERS = []
SYNCED_BALANCES = []
SYNCED_POSITIONS = []

# In-memory user storage
USERS = {
    "test@test.com": {
        "password": "Test123!@#",  # Updated to match frontend
        "name": "Test User",
        "id": "user-1"
    },
    "admin@trading.com": {
        "password": "Admin@123", 
        "name": "Admin User",
        "id": "user-2"
    },
    "trader@demo.com": {
        "password": "Trader@123",
        "name": "Demo Trader",
        "id": "user-3"
    }
}

# Request/Response models
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

def create_token(user_id: str, email: str):
    """Create JWT token"""
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials):
    """Verify JWT token"""
    if not credentials:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials, 
            SECRET_KEY, 
            algorithms=[ALGORITHM]
        )
        return payload
    except jwt.InvalidTokenError:
        return None

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/auth/login")
async def login(request: LoginRequest):
    """Login endpoint"""
    # Debug logging
    print(f"🔐 Login attempt - Email: {request.email}, Password: {request.password}")
    
    user = USERS.get(request.email)
    
    if not user:
        print(f"❌ User not found: {request.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user["password"] != request.password:
        print(f"❌ Password mismatch - Expected: {user['password']}, Got: {request.password}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    print(f"✅ Login successful for: {request.email}")
    token = create_token(user["id"], request.email)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": request.email,
            "name": user["name"]
        }
    }

@app.post("/auth/register")
async def register(request: RegisterRequest):
    """Register endpoint"""
    if request.email in USERS:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Add new user
    user_id = f"user-{len(USERS) + 1}"
    USERS[request.email] = {
        "password": request.password,
        "name": request.name,
        "id": user_id
    }
    
    token = create_token(user_id, request.email)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": request.email,
            "name": request.name
        }
    }

@app.get("/auth/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user info"""
    payload = verify_token(credentials)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    email = payload.get("email")
    user = USERS.get(email)
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {
        "id": user["id"],
        "email": email,
        "name": user["name"]
    }

# Dashboard data endpoints
# Exchange Accounts endpoints
@app.get("/api/v1/exchange-accounts")
async def get_exchange_accounts_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get exchange accounts list"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return get_all_exchange_accounts()

@app.post("/api/v1/exchange-accounts")
async def create_exchange_account(request: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Create new exchange account"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    print(f"📊 Creating exchange account: {request}")
    
    # Generate unique ID
    current_accounts = get_all_exchange_accounts()
    new_id = f"acc-{len(current_accounts) + 1}"
    
    account_data = {
        "id": new_id,
        "name": request.get("name", "New Account"),
        "exchange": request.get("exchange", "binance"),
        "api_key": request.get("api_key", ""),  # Store real key in DB
        "secret_key": request.get("secret_key", ""),  # Store real secret in DB
        "testnet": request.get("testnet", True),
        "is_default": request.get("is_default", False),
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Save to database
    save_exchange_account(account_data)
    
    # Return account with masked keys
    return_account = {
        "id": account_data["id"],
        "name": account_data["name"],
        "exchange": account_data["exchange"],
        "apiKey": "***" + account_data["api_key"][-4:] if len(account_data["api_key"]) > 4 else "***",
        "secretKey": "***" + account_data["secret_key"][-4:] if len(account_data["secret_key"]) > 4 else "***",
        "testnet": account_data["testnet"],
        "isDefault": account_data["is_default"],
        "isActive": account_data["is_active"],
        "createdAt": account_data["created_at"]
    }
    
    print(f"✅ Exchange account saved to database: {new_id}")
    
    return return_account

# Webhooks endpoints
@app.get("/api/v1/webhooks")
async def get_webhooks(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get webhooks list"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return []

# Orders endpoints
@app.get("/api/v1/orders")
async def get_api_orders(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get orders list"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return SYNCED_ORDERS

@app.get("/api/v1/orders/stats")
async def get_orders_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get orders statistics"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    total = len(SYNCED_ORDERS)
    filled = len([o for o in SYNCED_ORDERS if o.get("status") == "FILLED"])
    partial = len([o for o in SYNCED_ORDERS if o.get("status") == "PARTIALLY_FILLED"])
    pending = total - filled - partial
    
    return {
        "totalOrders": total,
        "pendingOrders": pending,
        "filledOrders": filled,
        "failedOrders": 0
    }

# Positions endpoints
@app.get("/api/v1/positions")
async def get_api_positions(status: str = "all", credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get positions list"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Filter by status if needed
    return SYNCED_POSITIONS

@app.get("/api/v1/positions/metrics")
async def get_positions_metrics(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get positions metrics"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    open_positions = len(SYNCED_POSITIONS)
    total_pnl = sum(float(p.get("pnl", 0)) for p in SYNCED_POSITIONS)
    
    return {
        "openPositions": open_positions,
        "totalPnL": total_pnl,
        "winRate": 68.5 if open_positions > 0 else 0,
        "avgHoldTime": 24 if open_positions > 0 else 0
    }

# Server IPs endpoint
@app.get("/api/v1/server/ips")
async def get_server_ips(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get server IPs for exchange whitelisting"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Simulate getting server IPs
    import socket
    import requests
    
    try:
        # Get internal IP
        hostname = socket.gethostname()
        internal_ip = socket.gethostbyname(hostname)
        
        # Try to get external IP
        external_ip = "Unable to fetch"
        try:
            external_response = requests.get('https://api.ipify.org', timeout=5)
            external_ip = external_response.text
        except:
            external_ip = "Check connection"
        
        return {
            "ips": [
                {
                    "type": "Internal IP",
                    "ip": internal_ip,
                    "description": "Internal container/server IP"
                },
                {
                    "type": "External IP", 
                    "ip": external_ip,
                    "description": "Public IP (if available)"
                },
                {
                    "type": "Localhost",
                    "ip": "127.0.0.1",
                    "description": "Local development"
                },
                {
                    "type": "Container IP",
                    "ip": "172.17.0.1",
                    "description": "Docker container IP"
                }
            ],
            "note": "Add these IPs to your Binance API whitelist"
        }
    except Exception as e:
        return {
            "ips": [
                {
                    "type": "Default",
                    "ip": "127.0.0.1",
                    "description": "Local development IP"
                }
            ],
            "note": "Unable to detect all IPs, use 127.0.0.1 for local testing",
            "error": str(e)
        }

# Sync endpoints for Binance data
@app.post("/api/v1/sync/orders/{account_id}")
async def sync_orders(account_id: str, auth_credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Sync orders from Binance account"""
    print(f"🔍 Debug - Token received: {auth_credentials.credentials if auth_credentials else 'None'}")
    print(f"🔍 Debug - Token verification result: {verify_token(auth_credentials)}")
    
    if not verify_token(auth_credentials):
        print("❌ Token verification failed!")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    print(f"🔄 Syncing orders for account: {account_id}")
    
    # Get real credentials from database
    api_credentials = get_real_credentials(account_id)
    if not api_credentials:
        raise HTTPException(status_code=404, detail="Account not found")
    
    try:
        api_key = api_credentials["api_key"]
        secret_key = api_credentials["secret_key"]
        testnet = api_credentials["testnet"]
        
        if not api_key or not secret_key or len(api_key) < 10:
            return {"error": "Invalid API credentials", "orders": []}
        
        # Connect to Binance
        try:
            # Use real credentials
            client = Client(api_key, secret_key, testnet=testnet)
            
            # Get account info to test connection
            account_info = client.get_account()
            print(f"✅ Connected to Binance! Account status: {account_info.get('accountType', 'SPOT')}")
            
            # Get recent orders from all open orders and order history
            try:
                # Try to get open orders first (no symbol required)
                open_orders = client.get_open_orders()
                
                # Get order history from account trades (more comprehensive)
                recent_trades = client.get_my_trades()
                
                # Convert trades to order-like format
                orders = []
                
                # Add open orders
                for order in open_orders:
                    orders.append(order)
                
                # Convert recent trades to orders format (limit to 50)
                for trade in recent_trades[-50:]:
                    order_data = {
                        "orderId": trade.get("orderId", trade.get("id", 0)),
                        "symbol": trade["symbol"],
                        "side": "BUY" if trade["isBuyer"] else "SELL",
                        "origQty": trade["qty"],
                        "price": trade["price"],
                        "status": "FILLED",
                        "time": trade["time"],
                        "executedQty": trade["qty"]
                    }
                    orders.append(order_data)
                
            except Exception as e:
                print(f"⚠️ Fallback: Using account info approach - {str(e)}")
                # Fallback: Get from most popular trading pairs
                popular_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
                orders = []
                
                for symbol in popular_symbols:
                    try:
                        symbol_orders = client.get_all_orders(symbol=symbol, limit=10)
                        orders.extend(symbol_orders)
                    except:
                        continue
                
                if not orders:
                    # Last fallback - return empty list with success
                    return {
                        "success": True,
                        "orders": [],
                        "count": 0,
                        "message": "Connected successfully but no recent orders found"
                    }
            
            # Convert to our format
            formatted_orders = []
            for order in orders[-20:]:  # Last 20 orders
                formatted_order = {
                    "id": str(order["orderId"]),
                    "symbol": order["symbol"],
                    "side": order["side"],
                    "quantity": float(order["origQty"]),
                    "price": float(order["price"]) if order["price"] != "0.00000000" else 0,
                    "status": order["status"],
                    "timestamp": datetime.fromtimestamp(order["time"]/1000).isoformat() + "Z",
                    "executedQty": float(order["executedQty"])
                }
                formatted_orders.append(formatted_order)
            
            # Save to memory
            global SYNCED_ORDERS
            SYNCED_ORDERS = formatted_orders  # Replace with real data
            
            return {
                "success": True,
                "orders": formatted_orders,
                "count": len(formatted_orders),
                "message": f"Synced {len(formatted_orders)} real orders from Binance"
            }
            
        except BinanceAPIException as e:
            error_msg = f"Binance API Error: {e.message}"
            print(f"❌ {error_msg}")
            return {"error": error_msg, "orders": []}
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            print(f"❌ {error_msg}")
            return {"error": error_msg, "orders": []}
        
    except Exception as e:
        return {
            "error": f"Failed to sync orders: {str(e)}",
            "orders": []
        }

@app.post("/api/v1/sync/balances/{account_id}")
async def sync_balances(account_id: str, auth_credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Sync balances from Binance account"""
    if not verify_token(auth_credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    print(f"💰 Syncing balances for account: {account_id}")
    
    # Find the account
    accounts_response = await get_exchange_accounts(auth_credentials)
    accounts = accounts_response if isinstance(accounts_response, list) else []
    account = next((acc for acc in accounts if acc["id"] == account_id), None)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    try:
        # Get real credentials from database
        api_credentials = get_real_credentials(account_id)
        if not api_credentials:
            raise HTTPException(status_code=404, detail="Account not found")
        
        api_key = api_credentials["api_key"]
        secret_key = api_credentials["secret_key"]
        testnet = api_credentials["testnet"]
        
        if not api_key or not secret_key or len(api_key) < 10:
            return {"error": "Invalid API credentials", "balances": []}
        
        # Connect to Binance
        try:
            client = Client(api_key, secret_key, testnet=testnet)
            
            # Get account info with balances
            account_info = client.get_account()
            print(f"✅ Connected to Binance for balances! Account status: {account_info.get('accountType', 'SPOT')}")
            
            # Get balances (only non-zero balances)
            all_balances = account_info.get('balances', [])
            real_balances = []
            
            for balance in all_balances:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                # Only include balances with some amount
                if total > 0:
                    real_balances.append({
                        "asset": balance['asset'],
                        "free": balance['free'],
                        "locked": balance['locked'],
                        "total": str(total)
                    })
            
            # Save to memory
            global SYNCED_BALANCES
            SYNCED_BALANCES = real_balances  # Replace with real data
            
            return {
                "success": True,
                "balances": real_balances,
                "count": len(real_balances),
                "message": f"Synced {len(real_balances)} real balances from Binance"
            }
            
        except BinanceAPIException as e:
            error_msg = f"Binance API Error: {e.message}"
            print(f"❌ {error_msg}")
            return {"error": error_msg, "balances": []}
        except Exception as e:
            error_msg = f"Connection Error: {str(e)}"
            print(f"❌ {error_msg}")
            return {"error": error_msg, "balances": []}
        
    except Exception as e:
        return {
            "error": f"Failed to sync balances: {str(e)}",
            "balances": []
        }

@app.post("/api/v1/sync/positions/{account_id}")
async def sync_positions(account_id: str, auth_credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Sync positions from Binance account"""
    if not verify_token(auth_credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    print(f"📊 Syncing positions for account: {account_id}")
    
    # Find the account
    accounts_response = await get_exchange_accounts(auth_credentials)
    accounts = accounts_response if isinstance(accounts_response, list) else []
    account = next((acc for acc in accounts if acc["id"] == account_id), None)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    try:
        # Get real credentials from database
        api_credentials = get_real_credentials(account_id)
        if not api_credentials:
            raise HTTPException(status_code=404, detail="Account not found")
        
        api_key = api_credentials["api_key"]
        secret_key = api_credentials["secret_key"]
        testnet = api_credentials["testnet"]
        
        if not api_key or not secret_key or len(api_key) < 10:
            return {"error": "Invalid API credentials", "positions": []}
        
        # Connect to Binance
        try:
            client = Client(api_key, secret_key, testnet=testnet)
            
            # For SPOT accounts, positions are typically just the balances
            # But we'll try to get futures positions if available
            real_positions = []
            
            try:
                # Try to get futures positions (this might fail for SPOT-only accounts)
                positions = client.futures_position_information()
                
                for position in positions:
                    position_amt = float(position.get('positionAmt', '0'))
                    
                    # Only include positions with actual amounts
                    if abs(position_amt) > 0:
                        real_positions.append({
                            "symbol": position['symbol'],
                            "positionAmt": position['positionAmt'],
                            "entryPrice": position['entryPrice'],
                            "markPrice": position['markPrice'],
                            "pnl": position['unRealizedProfit'],
                            "pnlPercentage": position.get('percentage', '0'),
                            "side": "LONG" if position_amt > 0 else "SHORT",
                            "leverage": position.get('leverage', '1')
                        })
                
                print(f"✅ Connected to Binance Futures! Found {len(real_positions)} active positions")
                
            except Exception as futures_error:
                print(f"ℹ️ No futures positions available (SPOT account): {str(futures_error)}")
                # For SPOT accounts, we can represent current balances as "positions"
                account_info = client.get_account()
                
                for balance in account_info.get('balances', []):
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked
                    
                    if total > 0:
                        real_positions.append({
                            "symbol": f"{balance['asset']}USDT",
                            "positionAmt": str(total),
                            "entryPrice": "0.0",
                            "markPrice": "0.0", 
                            "pnl": "0.0",
                            "pnlPercentage": "0.0",
                            "side": "HOLD",
                            "leverage": "1"
                        })
            
            # Save to memory
            global SYNCED_POSITIONS  
            SYNCED_POSITIONS = real_positions  # Replace with real data
            
            return {
                "success": True,
                "positions": real_positions,
                "count": len(real_positions),
                "message": f"Synced {len(real_positions)} real positions from Binance"
            }
            
        except BinanceAPIException as e:
            error_msg = f"Binance API Error: {e.message}"
            print(f"❌ {error_msg}")
            return {"error": error_msg, "positions": []}
        except Exception as e:
            error_msg = f"Connection Error: {str(e)}"
            print(f"❌ {error_msg}")
            return {"error": error_msg, "positions": []}
        
    except Exception as e:
        return {
            "error": f"Failed to sync positions: {str(e)}",
            "positions": []
        }

@app.post("/api/v1/sync/all/{account_id}")
async def sync_all_data(account_id: str, auth_credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Sync all data from Binance account"""
    if not verify_token(auth_credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    print(f"🔄 Syncing ALL data for account: {account_id}")
    
    # Find the account
    accounts_response = await get_exchange_accounts(auth_credentials)
    accounts = accounts_response if isinstance(accounts_response, list) else []
    account = next((acc for acc in accounts if acc["id"] == account_id), None)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    try:
        # Call all sync functions
        orders_result = await sync_orders(account_id, auth_credentials)
        balances_result = await sync_balances(account_id, auth_credentials)
        positions_result = await sync_positions(account_id, auth_credentials)
        
        return {
            "success": True,
            "message": "All data synced successfully",
            "results": {
                "orders": orders_result,
                "balances": balances_result, 
                "positions": positions_result
            }
        }
        
    except Exception as e:
        return {
            "error": f"Failed to sync all data: {str(e)}"
        }

# Dashboard utility functions
def get_default_account(user_id: str = "user-1"):
    """Get the default/active exchange account for dashboard"""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            # First try to get default account (without user_id filter for now)
            cursor.execute("""
                SELECT * FROM exchange_accounts 
                WHERE is_default = 1 AND is_active = 1
                ORDER BY created_at DESC LIMIT 1
            """)
            
            account = cursor.fetchone()
            if account:
                return {
                    "id": account[0],
                    "user_id": account[1] if len(account) > 1 else "user-1", 
                    "name": account[2] if len(account) > 2 else account[1],
                    "exchange": account[3] if len(account) > 3 else account[2],
                    "apiKey": (account[4][:6] + "***") if len(account) > 4 else "***",
                    "testnet": bool(account[7]) if len(account) > 7 else False,
                    "isDefault": bool(account[8]) if len(account) > 8 else True,
                    "isActive": bool(account[9]) if len(account) > 9 else True
                }
            
            # Fallback: get first active account
            cursor.execute("""
                SELECT * FROM exchange_accounts 
                WHERE is_active = 1
                ORDER BY created_at DESC LIMIT 1
            """)
            
            account = cursor.fetchone()
            if account:
                return {
                    "id": account[0],
                    "user_id": account[1] if len(account) > 1 else "user-1",
                    "name": account[2] if len(account) > 2 else account[1], 
                    "exchange": account[3] if len(account) > 3 else account[2],
                    "apiKey": (account[4][:6] + "***") if len(account) > 4 else "***",
                    "testnet": bool(account[7]) if len(account) > 7 else False,
                    "isDefault": bool(account[8]) if len(account) > 8 else False,
                    "isActive": bool(account[9]) if len(account) > 9 else True
                }
            
            return None
    except Exception as e:
        print(f"Error getting default account: {e}")
        return None

def get_crypto_day_range():
    """Get crypto day range (21:00 yesterday to 20:59 today UTC)"""
    from datetime import datetime, timedelta
    import pytz
    
    utc = pytz.UTC
    now = datetime.now(utc)
    
    # Crypto day starts at 21:00 UTC
    if now.hour >= 21:
        # We're in today's crypto day
        start_time = now.replace(hour=21, minute=0, second=0, microsecond=0)
        end_time = (now + timedelta(days=1)).replace(hour=20, minute=59, second=59, microsecond=999999)
    else:
        # We're in yesterday's crypto day continuation
        start_time = (now - timedelta(days=1)).replace(hour=21, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=20, minute=59, second=59, microsecond=999999)
    
    return start_time, end_time

def get_week_range():
    """Get current week range"""
    from datetime import datetime, timedelta
    import pytz
    
    utc = pytz.UTC
    now = datetime.now(utc)
    
    # Start of week (Monday)
    start_week = now - timedelta(days=now.weekday())
    start_week = start_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # End of week (Sunday)
    end_week = start_week + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
    
    return start_week, end_week

# Dashboard endpoints
@app.get("/api/v1/dashboard/default-account")
async def get_dashboard_default_account(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get default account for dashboard"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    account = get_default_account("user-1")
    if not account:
        raise HTTPException(status_code=404, detail="No active account found")
    
    return account

@app.get("/api/v1/dashboard/total-pnl")
async def get_total_pnl(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get total P&L from Futures + Spot"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    account = get_default_account("user-1")
    if not account:
        return {"total_pnl": 0, "error": "No active account"}
    
    try:
        # Get real credentials
        api_credentials = get_real_credentials(account["id"])
        if not api_credentials:
            return {"total_pnl": 0, "error": "Invalid credentials"}
        
        api_key = api_credentials["api_key"]
        secret_key = api_credentials["secret_key"]
        testnet = api_credentials["testnet"]
        
        client = Client(api_key, secret_key, testnet=testnet)
        
        total_pnl = 0
        
        try:
            # Get spot account PnL (from trades)
            spot_trades = client.get_my_trades()
            spot_pnl = 0
            
            for trade in spot_trades:
                if trade["isBuyer"]:
                    spot_pnl -= float(trade["quoteQty"])  # Cost
                else:
                    spot_pnl += float(trade["quoteQty"])  # Revenue
            
            total_pnl += spot_pnl
            
        except Exception as e:
            print(f"Spot PnL error: {e}")
        
        try:
            # Get futures account PnL
            futures_account = client.futures_account()
            futures_pnl = float(futures_account.get("totalUnrealizedProfit", 0))
            total_pnl += futures_pnl
            
        except Exception as e:
            print(f"Futures PnL error: {e}")
        
        return {
            "total_pnl": round(total_pnl, 2),
            "currency": "USDT"
        }
        
    except Exception as e:
        return {"total_pnl": 0, "error": str(e)}

@app.get("/api/v1/dashboard/orders-today")
async def get_orders_today(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get orders from crypto day (21:00 to 20:59)"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    account = get_default_account("user-1")
    if not account:
        return {"count": 0, "orders": [], "error": "No active account"}
    
    try:
        # Get time range for last 24 hours (simpler than crypto day)
        now = datetime.utcnow()
        start_time = now - timedelta(hours=24)
        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(now.timestamp() * 1000)
        
        # Get real credentials
        api_credentials = get_real_credentials(account["id"])
        if not api_credentials:
            return {"count": 0, "orders": [], "error": "Invalid credentials"}
        
        api_key = api_credentials["api_key"]
        secret_key = api_credentials["secret_key"]
        testnet = api_credentials["testnet"]
        
        client = Client(api_key, secret_key, testnet=testnet)
        
        # Get trades for today
        today_orders = []
        
        try:
            # First, get all open orders for today
            open_orders = client.get_open_orders()
            
            for order in open_orders:
                order_time = order["time"]
                if start_timestamp <= order_time <= end_timestamp:
                    today_orders.append({
                        "id": str(order["orderId"]),
                        "symbol": order["symbol"],
                        "side": order["side"],
                        "quantity": float(order["origQty"]),
                        "price": float(order["price"]) if order["price"] != "0.00000000" else 0,
                        "timestamp": datetime.fromtimestamp(order_time/1000).isoformat() + "Z",
                        "status": order["status"]
                    })
            
            # Get recent orders from known symbols (SOL que você mencionou)
            popular_symbols = ['SOLUSDT', 'BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            
            for symbol in popular_symbols:
                try:
                    # Get recent orders for this symbol
                    symbol_orders = client.get_all_orders(symbol=symbol, limit=50)
                    
                    # Filter for today only
                    for order in symbol_orders:
                        order_time = order["time"]
                        if start_timestamp <= order_time <= end_timestamp:
                            # Avoid duplicates from open orders
                            if not any(o["id"] == str(order["orderId"]) for o in today_orders):
                                today_orders.append({
                                    "id": str(order["orderId"]),
                                    "symbol": order["symbol"],
                                    "side": order["side"],
                                    "quantity": float(order["origQty"]),
                                    "price": float(order["price"]) if order["price"] != "0.00000000" else 0,
                                    "timestamp": datetime.fromtimestamp(order_time/1000).isoformat() + "Z",
                                    "status": order["status"]
                                })
                                
                except Exception as symbol_error:
                    print(f"Error getting orders for {symbol}: {symbol_error}")
                    continue
            
        except Exception as e:
            print(f"Orders today error: {e}")
        
        return {
            "count": len(today_orders),
            "orders": today_orders[:10],  # Limit to 10 recent
            "period": "last_24h"
        }
        
    except Exception as e:
        return {"count": 0, "orders": [], "error": str(e)}

@app.get("/api/v1/dashboard/active-positions")
async def get_active_positions(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get active positions (futures + spot holdings)"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    account = get_default_account("user-1")
    if not account:
        return {"count": 0, "positions": [], "error": "No active account"}
    
    try:
        # Get real credentials
        api_credentials = get_real_credentials(account["id"])
        if not api_credentials:
            return {"count": 0, "positions": [], "error": "Invalid credentials"}
        
        api_key = api_credentials["api_key"]
        secret_key = api_credentials["secret_key"]
        testnet = api_credentials["testnet"]
        
        client = Client(api_key, secret_key, testnet=testnet)
        
        active_positions = []
        
        try:
            # Get futures positions
            futures_positions = client.futures_position_information()
            
            for position in futures_positions:
                position_amt = float(position.get('positionAmt', '0'))
                if abs(position_amt) > 0:
                    active_positions.append({
                        "symbol": position['symbol'],
                        "type": "FUTURES",
                        "side": "LONG" if position_amt > 0 else "SHORT",
                        "amount": abs(position_amt),
                        "entry_price": float(position['entryPrice']),
                        "mark_price": float(position['markPrice']),
                        "pnl": float(position['unRealizedProfit']),
                        "leverage": position.get('leverage', '1')
                    })
                    
        except Exception as e:
            print(f"Futures positions error: {e}")
        
        try:
            # Get spot balances as "positions" - only significant holdings
            account_info = client.get_account()
            
            # Define minimum values for each type of asset to be considered a "position"
            # Increased thresholds to show only significant positions
            min_values = {
                'BTC': 0.001,      # ~$70+ 
                'ETH': 0.01,       # ~$30+
                'BNB': 0.1,        # ~$50+
                'SOL': 1.0,        # ~$200+
                'LINK': 5.0,       # ~$100+
                'USDT': 50,        # $50+
                'USDC': 50,        # $50+
                'BUSD': 50,        # $50+
                'AGI': 500,        # Minimum 500 tokens
                'FLR': 100,        # Minimum 100 tokens  
                'ARKM': 100,       # Minimum 100 tokens
                'ENA': 100,        # Minimum 100 tokens
                'default': 10      # Higher default minimum
            }
            
            for balance in account_info.get('balances', []):
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                asset = balance['asset']
                min_value = min_values.get(asset, min_values['default'])
                
                # Only show significant positions
                if total >= min_value:
                    active_positions.append({
                        "symbol": balance['asset'],
                        "type": "SPOT",
                        "side": "HOLD", 
                        "amount": total,
                        "entry_price": 0,
                        "mark_price": 0,
                        "pnl": 0,
                        "leverage": "1"
                    })
                    
        except Exception as e:
            print(f"Spot balances error: {e}")
        
        return {
            "count": len(active_positions),
            "positions": active_positions
        }
        
    except Exception as e:
        return {"count": 0, "positions": [], "error": str(e)}

@app.get("/api/v1/dashboard/weekly-orders")
async def get_weekly_orders(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get total orders this week"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    account = get_default_account("user-1")
    if not account:
        return {"count": 0, "error": "No active account"}
    
    try:
        # Get time range for this week
        start_week, end_week = get_week_range()
        start_timestamp = int(start_week.timestamp() * 1000)
        end_timestamp = int(end_week.timestamp() * 1000)
        
        # Get real credentials
        api_credentials = get_real_credentials(account["id"])
        if not api_credentials:
            return {"count": 0, "error": "Invalid credentials"}
        
        api_key = api_credentials["api_key"]
        secret_key = api_credentials["secret_key"]
        testnet = api_credentials["testnet"]
        
        client = Client(api_key, secret_key, testnet=testnet)
        
        weekly_orders = []
        
        try:
            recent_trades = client.get_my_trades()
            
            for trade in recent_trades:
                trade_time = trade["time"]
                if start_timestamp <= trade_time <= end_timestamp:
                    weekly_orders.append(trade)
        
        except Exception as e:
            print(f"Weekly orders error: {e}")
        
        return {
            "count": len(weekly_orders),
            "period": "current_week"
        }
        
    except Exception as e:
        return {"count": 0, "error": str(e)}

@app.get("/api/v1/dashboard/webhooks-count")
async def get_webhooks_count(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get active webhooks count"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # For now return mock data - we'll implement webhook storage later
    return {
        "active_webhooks": 3,
        "total_webhooks": 5,
        "status": "active"
    }

@app.get("/api/v1/dashboard/accounts-count")  
async def get_accounts_count(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get connected exchange accounts count"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM exchange_accounts WHERE is_active = 1")
            active_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM exchange_accounts")
            total_count = cursor.fetchone()[0]
            
        return {
            "active_accounts": active_count,
            "total_accounts": total_count,
            "status": "connected"
        }
        
    except Exception as e:
        return {"active_accounts": 0, "total_accounts": 0, "error": str(e)}

@app.get("/api/v1/dashboard/success-rate")
async def get_success_rate(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get weekly success rate and profit"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    account = get_default_account("user-1")
    if not account:
        return {"success_rate": 0, "weekly_profit": 0, "error": "No active account"}
    
    try:
        # Get time range for this week
        start_week, end_week = get_week_range()
        start_timestamp = int(start_week.timestamp() * 1000)
        end_timestamp = int(end_week.timestamp() * 1000)
        
        # Get real credentials
        api_credentials = get_real_credentials(account["id"])
        if not api_credentials:
            return {"success_rate": 0, "weekly_profit": 0, "error": "Invalid credentials"}
        
        api_key = api_credentials["api_key"]
        secret_key = api_credentials["secret_key"]
        testnet = api_credentials["testnet"]
        
        client = Client(api_key, secret_key, testnet=testnet)
        
        weekly_trades = []
        weekly_profit = 0
        profitable_trades = 0
        
        try:
            recent_trades = client.get_my_trades()
            
            for trade in recent_trades:
                trade_time = trade["time"]
                if start_timestamp <= trade_time <= end_timestamp:
                    weekly_trades.append(trade)
                    
                    # Simple P&L calculation
                    trade_value = float(trade["quoteQty"])
                    if trade["isBuyer"]:
                        weekly_profit -= trade_value  # Cost
                    else:
                        weekly_profit += trade_value  # Revenue
                        if trade_value > 0:
                            profitable_trades += 1
        
        except Exception as e:
            print(f"Success rate error: {e}")
        
        total_trades = len(weekly_trades)
        success_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "success_rate": round(success_rate, 1),
            "weekly_profit": round(weekly_profit, 2),
            "total_trades": total_trades,
            "profitable_trades": profitable_trades,
            "period": "current_week"
        }
        
    except Exception as e:
        return {"success_rate": 0, "weekly_profit": 0, "error": str(e)}

@app.get("/api/v1/dashboard/recent-orders")
async def get_recent_orders(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get recent orders (last 7 days)"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    account = get_default_account("user-1")
    if not account:
        return {"orders": [], "error": "No active account"}
    
    try:
        # Get time range for last 7 days
        now = datetime.utcnow()
        start_week = now - timedelta(days=7)
        start_timestamp = int(start_week.timestamp() * 1000)
        end_timestamp = int(now.timestamp() * 1000)
        
        # Get real credentials
        api_credentials = get_real_credentials(account["id"])
        if not api_credentials:
            return {"orders": [], "error": "Invalid credentials"}
        
        api_key = api_credentials["api_key"]
        secret_key = api_credentials["secret_key"]
        testnet = api_credentials["testnet"]
        
        client = Client(api_key, secret_key, testnet=testnet)
        
        recent_orders = []
        
        try:
            # Get all open orders first
            open_orders = client.get_open_orders()
            
            for order in open_orders:
                recent_orders.append({
                    "id": str(order["orderId"]),
                    "symbol": order["symbol"],
                    "side": order["side"],
                    "quantity": float(order["origQty"]),
                    "price": float(order["price"]) if order["price"] != "0.00000000" else 0,
                    "total": float(order["origQty"]) * float(order["price"]) if order["price"] != "0.00000000" else 0,
                    "timestamp": datetime.fromtimestamp(order["time"]/1000).isoformat() + "Z",
                    "status": order["status"]
                })
            
            # Get historical orders from known symbols
            popular_symbols = ['SOLUSDT', 'BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            
            for symbol in popular_symbols:
                try:
                    # Get recent orders for this symbol (last week)
                    symbol_orders = client.get_all_orders(symbol=symbol, limit=100)
                    
                    # Filter for this week and add to list
                    for order in symbol_orders:
                        order_time = order["time"]
                        if start_timestamp <= order_time <= end_timestamp:
                            # Avoid duplicates
                            if not any(o["id"] == str(order["orderId"]) for o in recent_orders):
                                recent_orders.append({
                                    "id": str(order["orderId"]),
                                    "symbol": order["symbol"],
                                    "side": order["side"],
                                    "quantity": float(order["origQty"]),
                                    "price": float(order["price"]) if order["price"] != "0.00000000" else 0,
                                    "total": float(order["executedQty"]) * float(order["price"]) if order["price"] != "0.00000000" else 0,
                                    "timestamp": datetime.fromtimestamp(order_time/1000).isoformat() + "Z",
                                    "status": order["status"]
                                })
                                
                except Exception as symbol_error:
                    print(f"Error getting recent orders for {symbol}: {symbol_error}")
                    continue
        
        except Exception as e:
            print(f"Recent orders error: {e}")
        
        # Sort by timestamp descending and limit to 20
        recent_orders.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "orders": recent_orders[:20],
            "count": len(recent_orders),
            "period": "last_7_days"
        }
        
    except Exception as e:
        return {"orders": [], "error": str(e)}

@app.get("/dashboard/stats")
async def dashboard_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get dashboard statistics"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {
        "totalOrders": 33,
        "activePositions": 5,
        "totalProfit": 12543.67,
        "winRate": 68.5,
        "todayOrders": 7,
        "pendingWebhooks": 2
    }

@app.get("/orders")
async def get_orders(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get orders list"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return [
        {
            "id": "order-1",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.001,
            "price": 65432.10,
            "status": "FILLED",
            "timestamp": "2025-08-28T10:30:00Z"
        },
        {
            "id": "order-2",
            "symbol": "ETHUSDT",
            "side": "SELL",
            "quantity": 0.5,
            "price": 3234.50,
            "status": "PENDING",
            "timestamp": "2025-08-28T11:15:00Z"
        },
        {
            "id": "order-3",
            "symbol": "SOLUSDT", 
            "side": "BUY",
            "quantity": 10,
            "price": 145.23,
            "status": "FILLED",
            "timestamp": "2025-08-28T12:00:00Z"
        }
    ]

@app.get("/positions")
async def get_positions(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get positions list"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return [
        {
            "id": "pos-1",
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": 0.001,
            "entryPrice": 64000,
            "currentPrice": 65432,
            "pnl": 143.20,
            "pnlPercentage": 2.24
        },
        {
            "id": "pos-2",
            "symbol": "ETHUSDT",
            "side": "SHORT",
            "quantity": 0.5,
            "entryPrice": 3300,
            "currentPrice": 3234,
            "pnl": 33.00,
            "pnlPercentage": 1.00
        }
    ]

@app.get("/webhooks")
async def get_webhooks(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get webhooks list"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return [
        {
            "id": "webhook-1",
            "name": "TradingView Strategy 1",
            "url": "http://localhost:3001/webhook/tradingview",
            "status": "active",
            "lastTriggered": "2025-08-28T09:30:00Z"
        },
        {
            "id": "webhook-2", 
            "name": "Custom Alert",
            "url": "http://localhost:3001/webhook/custom",
            "status": "inactive",
            "lastTriggered": null
        }
    ]

@app.get("/exchange-accounts")
async def get_exchange_accounts(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get exchange accounts"""
    if not verify_token(credentials):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return [
        {
            "id": "acc-1",
            "name": "Binance Main",
            "exchange": "binance",
            "status": "connected",
            "balance": 10000.00
        },
        {
            "id": "acc-2",
            "name": "Bybit Trading",
            "exchange": "bybit", 
            "status": "disconnected",
            "balance": 0
        }
    ]

if __name__ == "__main__":
    print("\n🚀 Starting Simple Auth Server")
    print("="*50)
    print("📍 Server URL: http://localhost:3001")
    print("\n📧 Available test accounts:")
    print("  • test@test.com (Password: Test123!@#)")
    print("  • admin@trading.com (Password: Admin@123)")
    print("  • trader@demo.com (Password: Trader@123)")
    print("="*50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=3001)