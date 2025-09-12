"""Authentication controller without DI dependencies"""

import bcrypt
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel
from jose import JWTError, jwt

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.config.settings import get_settings

# Models
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    refresh_token: str
    user: dict

class UserProfileResponse(BaseModel):
    success: bool
    user: dict

def create_auth_router() -> APIRouter:
    """Create simplified auth router without DI dependencies"""
    router = APIRouter(prefix="/auth", tags=["Authentication"])
    settings = get_settings()

    def create_access_token(data: dict) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    def create_refresh_token(data: dict) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)  # 7 days
        to_encode.update({"exp": expire, "type": "refresh"})
        
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    async def get_user_by_email(email: str) -> Optional[dict]:
        """Get user by email from database"""
        try:
            user = await transaction_db.fetchrow(
                "SELECT id, email, password_hash, name, is_active, created_at FROM users WHERE email = $1",
                email
            )
            
            if user:
                return {
                    "id": str(user["id"]),
                    "email": user["email"],
                    "password_hash": user["password_hash"],
                    "name": user["name"],
                    "is_active": user["is_active"],
                    "created_at": user["created_at"].isoformat() if user["created_at"] else None,
                }
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    def verify_token(token: str) -> Optional[dict]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            return payload
        except JWTError:
            return None

    @router.post("/login", response_model=LoginResponse)
    async def login(request: LoginRequest):
        """Login endpoint"""
        try:
            # Get user by email
            user = await get_user_by_email(request.email)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Verify password
            if not verify_password(request.password, user["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            if not user["is_active"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is disabled"
                )
            
            # Create tokens
            token_data = {"user_id": user["id"], "email": user["email"]}
            access_token = create_access_token(token_data)
            refresh_token = create_refresh_token(token_data)
            
            # Remove sensitive data from user response
            user_response = {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "created_at": user["created_at"]
            }
            
            return LoginResponse(
                success=True,
                message="Login successful",
                access_token=access_token,
                refresh_token=refresh_token,
                user=user_response
            )
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"Login error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    @router.get("/me", response_model=UserProfileResponse)
    async def get_current_user_profile(request: Request):
        """Get current user profile"""
        try:
            # Get token from Authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing or invalid authorization header"
                )
            
            token = auth_header.split(" ")[1]
            
            # Verify token
            payload = verify_token(token)
            if not payload or payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token"
                )
            
            # Get user from database
            user = await get_user_by_email(payload["email"])
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Return user profile
            user_response = {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "created_at": user["created_at"]
            }
            
            return UserProfileResponse(success=True, user=user_response)
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"Get profile error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    return router