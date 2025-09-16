"""Enhanced JWT Manager with refresh token rotation and security features"""

import jwt
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

import structlog
from infrastructure.config.settings import get_settings

logger = structlog.get_logger(__name__)


class TokenType(Enum):
    """JWT token types"""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    VERIFY = "verify"


@dataclass
class TokenPair:
    """Access and refresh token pair"""
    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_expires_in: int
    token_type: str = "bearer"


@dataclass
class TokenValidationResult:
    """Token validation result"""
    is_valid: bool
    payload: Optional[Dict] = None
    error: Optional[str] = None
    expired: bool = False
    user_id: Optional[str] = None


class JWTManager:
    """Enhanced JWT manager with security features"""
    
    def __init__(self):
        self.settings = get_settings()
        self.secret_key = self.settings.secret_key
        self.algorithm = "HS256"
        
        # Token expiration times
        self.access_token_expire = timedelta(minutes=30)
        self.refresh_token_expire = timedelta(days=7)
        self.reset_token_expire = timedelta(hours=1)
        self.verify_token_expire = timedelta(hours=24)
        
        # In production, this would be stored in Redis/database
        # For now, using in-memory storage with cleanup
        self.refresh_token_store: Dict[str, Dict] = {}
        self.blacklisted_tokens: set = set()
        
        # Cleanup counters
        self.cleanup_counter = 0
        self.cleanup_interval = 100
    
    def create_token_pair(self, user_id: str, user_email: str, additional_claims: Optional[Dict] = None) -> TokenPair:
        """Create access and refresh token pair with rotation"""
        
        now = datetime.utcnow()
        
        # Create access token
        access_payload = {
            "user_id": str(user_id),
            "email": user_email,
            "type": TokenType.ACCESS.value,
            "iat": now,
            "exp": now + self.access_token_expire,
            "jti": self._generate_jti(),  # JWT ID for tracking
        }
        
        if additional_claims:
            access_payload.update(additional_claims)
        
        # Create refresh token with longer expiration
        refresh_jti = self._generate_jti()
        refresh_payload = {
            "user_id": str(user_id),
            "email": user_email,
            "type": TokenType.REFRESH.value,
            "iat": now,
            "exp": now + self.refresh_token_expire,
            "jti": refresh_jti,
        }
        
        # Generate tokens
        access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)
        
        # Store refresh token info for validation and rotation
        refresh_token_hash = self._hash_token(refresh_token)
        self.refresh_token_store[refresh_token_hash] = {
            "user_id": str(user_id),
            "email": user_email,
            "created_at": now,
            "expires_at": now + self.refresh_token_expire,
            "jti": refresh_jti,
            "used": False
        }
        
        # Cleanup old tokens periodically
        self._periodic_cleanup()
        
        logger.info(
            "Token pair created",
            user_id=str(user_id),
            access_expires_in=int(self.access_token_expire.total_seconds()),
            refresh_expires_in=int(self.refresh_token_expire.total_seconds())
        )
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_in=int(self.access_token_expire.total_seconds()),
            refresh_expires_in=int(self.refresh_token_expire.total_seconds())
        )
    
    def validate_access_token(self, token: str) -> TokenValidationResult:
        """Validate access token"""
        return self._validate_token(token, TokenType.ACCESS)
    
    def validate_refresh_token(self, token: str) -> TokenValidationResult:
        """Validate refresh token"""
        # First validate JWT structure and signature
        validation_result = self._validate_token(token, TokenType.REFRESH)
        
        if not validation_result.is_valid:
            return validation_result
        
        # Check if refresh token is in our store and not used
        token_hash = self._hash_token(token)
        stored_token = self.refresh_token_store.get(token_hash)
        
        if not stored_token:
            logger.warning("Refresh token not found in store", token_hash=token_hash[:16])
            return TokenValidationResult(
                is_valid=False,
                error="Invalid refresh token"
            )
        
        if stored_token.get("used", False):
            logger.warning("Refresh token already used", 
                          user_id=stored_token.get("user_id"),
                          token_hash=token_hash[:16])
            # Invalidate all tokens for this user (security measure)
            self._revoke_user_tokens(stored_token.get("user_id"))
            return TokenValidationResult(
                is_valid=False,
                error="Refresh token already used"
            )
        
        return validation_result
    
    def refresh_tokens(self, refresh_token: str) -> Optional[TokenPair]:
        """Refresh access token using refresh token with rotation"""
        
        # Validate refresh token
        validation_result = self.validate_refresh_token(refresh_token)
        
        if not validation_result.is_valid:
            return None
        
        # Mark old refresh token as used
        token_hash = self._hash_token(refresh_token)
        if token_hash in self.refresh_token_store:
            self.refresh_token_store[token_hash]["used"] = True
        
        # Create new token pair
        user_id = validation_result.payload["user_id"]
        user_email = validation_result.payload["email"]
        
        logger.info("Tokens refreshed", user_id=user_id)
        
        return self.create_token_pair(user_id, user_email)
    
    def create_reset_token(self, user_id: str, user_email: str) -> str:
        """Create password reset token"""
        
        now = datetime.utcnow()
        payload = {
            "user_id": str(user_id),
            "email": user_email,
            "type": TokenType.RESET.value,
            "iat": now,
            "exp": now + self.reset_token_expire,
            "jti": self._generate_jti(),
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.info("Reset token created", user_id=str(user_id))
        
        return token
    
    def create_verify_token(self, user_id: str, user_email: str) -> str:
        """Create email verification token"""
        
        now = datetime.utcnow()
        payload = {
            "user_id": str(user_id),
            "email": user_email,
            "type": TokenType.VERIFY.value,
            "iat": now,
            "exp": now + self.verify_token_expire,
            "jti": self._generate_jti(),
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.info("Verification token created", user_id=str(user_id))
        
        return token
    
    def revoke_token(self, token: str):
        """Add token to blacklist"""
        try:
            # Decode token to get JTI
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            jti = payload.get("jti")
            if jti:
                self.blacklisted_tokens.add(jti)
                logger.info("Token revoked", jti=jti)
        except jwt.InvalidTokenError:
            logger.warning("Attempted to revoke invalid token")
    
    def revoke_user_tokens(self, user_id: str):
        """Revoke all tokens for a specific user"""
        self._revoke_user_tokens(user_id)
    
    def _validate_token(self, token: str, expected_type: TokenType) -> TokenValidationResult:
        """Internal token validation"""
        
        try:
            # Decode token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            token_type = payload.get("type")
            if token_type != expected_type.value:
                return TokenValidationResult(
                    is_valid=False,
                    error=f"Invalid token type. Expected {expected_type.value}, got {token_type}"
                )
            
            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and jti in self.blacklisted_tokens:
                return TokenValidationResult(
                    is_valid=False,
                    error="Token has been revoked"
                )
            
            # Token is valid
            return TokenValidationResult(
                is_valid=True,
                payload=payload,
                user_id=payload.get("user_id")
            )
            
        except jwt.ExpiredSignatureError:
            logger.info("Token expired", token_type=expected_type.value)
            return TokenValidationResult(
                is_valid=False,
                error="Token has expired",
                expired=True
            )
        
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token", error=str(e), token_type=expected_type.value)
            return TokenValidationResult(
                is_valid=False,
                error="Invalid token"
            )
        
        except Exception as e:
            logger.error("Token validation error", error=str(e), exc_info=True)
            return TokenValidationResult(
                is_valid=False,
                error="Token validation failed"
            )
    
    def _generate_jti(self) -> str:
        """Generate JWT ID for token tracking"""
        return secrets.token_urlsafe(32)
    
    def _hash_token(self, token: str) -> str:
        """Hash token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _revoke_user_tokens(self, user_id: str):
        """Revoke all refresh tokens for a user"""
        tokens_to_remove = []
        
        for token_hash, token_data in self.refresh_token_store.items():
            if token_data.get("user_id") == str(user_id):
                tokens_to_remove.append(token_hash)
                # Add JTI to blacklist if available
                if "jti" in token_data:
                    self.blacklisted_tokens.add(token_data["jti"])
        
        for token_hash in tokens_to_remove:
            del self.refresh_token_store[token_hash]
        
        logger.info("User tokens revoked", user_id=str(user_id), tokens_count=len(tokens_to_remove))
    
    def _periodic_cleanup(self):
        """Periodic cleanup of expired tokens"""
        self.cleanup_counter += 1
        
        if self.cleanup_counter % self.cleanup_interval == 0:
            now = datetime.utcnow()
            expired_tokens = []
            
            # Clean expired refresh tokens
            for token_hash, token_data in self.refresh_token_store.items():
                if token_data.get("expires_at", now) < now:
                    expired_tokens.append(token_hash)
            
            for token_hash in expired_tokens:
                del self.refresh_token_store[token_hash]
            
            # Limit blacklist size (keep only recent entries)
            if len(self.blacklisted_tokens) > 10000:
                # In production, implement proper cleanup based on token expiration
                self.blacklisted_tokens = set(list(self.blacklisted_tokens)[-5000:])
            
            if expired_tokens:
                logger.info(f"Cleaned up {len(expired_tokens)} expired refresh tokens")
    
    def get_token_info(self, token: str) -> Optional[Dict]:
        """Get token information without validation"""
        try:
            # Decode without verification to get payload
            payload = jwt.decode(token, options={"verify_signature": False})
            return {
                "user_id": payload.get("user_id"),
                "email": payload.get("email"),
                "type": payload.get("type"),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0)),
                "issued_at": datetime.fromtimestamp(payload.get("iat", 0)),
                "jti": payload.get("jti")
            }
        except Exception:
            return None


# Global instance
jwt_manager = JWTManager()