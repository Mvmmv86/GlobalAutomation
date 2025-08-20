"""Authentication service with JWT and TOTP support"""

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
import pyotp
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from infrastructure.config.settings import get_settings


class AuthService:
    """Service for authentication operations"""

    def __init__(self):
        self.settings = get_settings()

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False

    def generate_totp_secret(self) -> str:
        """Generate TOTP secret for 2FA"""
        return pyotp.random_base32()

    def get_totp_provisioning_uri(
        self, secret: str, email: str, issuer: str = "TradingView Gateway"
    ) -> str:
        """Get TOTP provisioning URI for QR code"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)

    def verify_totp_token(self, secret: str, token: str) -> bool:
        """Verify TOTP token"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=1)  # Allow 1 step tolerance
        except (ValueError, TypeError):
            return False

    def create_access_token(
        self, user_id: str, email: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.settings.access_token_expire_minutes
            )

        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
        }

        return jwt.encode(
            payload, self.settings.secret_key, algorithm=self.settings.algorithm
        )

    def create_refresh_token(
        self, user_id: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT refresh token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                days=30
            )  # Refresh tokens last longer

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
        }

        return jwt.encode(
            payload, self.settings.secret_key, algorithm=self.settings.algorithm
        )

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token, self.settings.secret_key, algorithms=[self.settings.algorithm]
            )
            return payload
        except ExpiredSignatureError:
            return None
        except InvalidTokenError:
            return None

    def create_token_pair(self, user_id: str, email: str) -> Tuple[str, str]:
        """Create access and refresh token pair"""
        access_token = self.create_access_token(user_id, email)
        refresh_token = self.create_refresh_token(user_id)
        return access_token, refresh_token

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create new access token from refresh token"""
        payload = self.verify_token(refresh_token)

        if not payload or payload.get("type") != "refresh":
            return None

        # Note: In production, you'd want to get user email from database
        # For now, we'll create a minimal access token
        user_id = payload.get("sub")
        if not user_id:
            return None

        return self.create_access_token(user_id, "")

    def extract_user_id_from_token(self, token: str) -> Optional[str]:
        """Extract user ID from token"""
        payload = self.verify_token(token)
        if payload and payload.get("type") == "access":
            return payload.get("sub")
        return None

    def is_token_valid(self, token: str) -> bool:
        """Check if token is valid"""
        return self.verify_token(token) is not None
