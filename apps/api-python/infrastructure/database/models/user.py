"""User and APIKey models"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class User(Base):
    """User model for authentication and account management"""

    __tablename__ = "users"

    # Basic info
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, comment="User email address"
    )

    name: Mapped[Optional[str]] = mapped_column(String(255), comment="User full name")

    password_hash: Mapped[str] = mapped_column(
        String(255), comment="Bcrypt hashed password"
    )

    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        comment="User account active status",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        comment="Email verification status",
    )

    # 2FA / TOTP
    totp_secret: Mapped[Optional[str]] = mapped_column(
        String(64), comment="TOTP secret key (encrypted)"
    )

    totp_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        comment="Two-factor authentication enabled",
    )

    # Security tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Last successful login timestamp"
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        default=0, server_default="0", comment="Failed login attempts counter"
    )

    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Account lock expiration timestamp"
    )

    # Password reset
    reset_token: Mapped[Optional[str]] = mapped_column(
        String(255), comment="Password reset token"
    )

    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Password reset token expiration"
    )

    # Email verification
    verification_token: Mapped[Optional[str]] = mapped_column(
        String(255), comment="Email verification token"
    )

    # Relationships
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )

    exchange_accounts: Mapped[List["ExchangeAccount"]] = relationship(
        "ExchangeAccount", back_populates="user", cascade="all, delete-orphan"
    )

    webhooks: Mapped[List["Webhook"]] = relationship(
        "Webhook", back_populates="user", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        """Initialize User with default values"""
        # Set defaults
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("is_verified", False)
        kwargs.setdefault("totp_enabled", False)
        kwargs.setdefault("failed_login_attempts", 0)
        super().__init__(**kwargs)

    def activate(self) -> None:
        """Activate user account"""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate user account"""
        self.is_active = False

    def verify_email(self) -> None:
        """Mark email as verified"""
        self.is_verified = True
        self.verification_token = None

    def enable_totp(self, secret: str) -> None:
        """Enable TOTP two-factor authentication"""
        self.totp_secret = secret
        self.totp_enabled = True

    def disable_totp(self) -> None:
        """Disable TOTP two-factor authentication"""
        self.totp_secret = None
        self.totp_enabled = False

    def increment_failed_login(self) -> None:
        """Increment failed login attempts"""
        self.failed_login_attempts += 1

    def reset_failed_login(self) -> None:
        """Reset failed login attempts counter"""
        self.failed_login_attempts = 0

    def lock_account(self, until: datetime) -> None:
        """Lock account until specified time"""
        self.locked_until = until

    def unlock_account(self) -> None:
        """Unlock account"""
        self.locked_until = None
        self.failed_login_attempts = 0

    def is_locked(self) -> bool:
        """Check if account is locked"""
        if self.locked_until is None:
            return False
        return datetime.now() < self.locked_until

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        import bcrypt

        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash"""
        import bcrypt

        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), self.password_hash.encode("utf-8")
            )
        except (ValueError, TypeError):
            return False

    def verify_totp_token(self, token: str) -> bool:
        """Verify TOTP token"""
        if not self.totp_enabled or not self.totp_secret:
            return False

        import pyotp

        try:
            totp = pyotp.TOTP(self.totp_secret)
            return totp.verify(token, valid_window=1)
        except (ValueError, TypeError):
            return False


class APIKey(Base):
    """API Key model for programmatic access"""

    __tablename__ = "api_keys"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), comment="API key friendly name")

    key_hash: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, comment="Hashed API key"
    )

    # Status and limits
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", comment="API key active status"
    )

    rate_limit_per_minute: Mapped[Optional[int]] = mapped_column(
        default=None, comment="Custom rate limit per minute"
    )

    # Security tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="Last usage timestamp"
    )

    usage_count: Mapped[int] = mapped_column(
        default=0, server_default="0", comment="Total usage counter"
    )

    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="API key expiration timestamp"
    )

    # Relationships
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        comment="User owner ID",
    )

    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    def __init__(self, **kwargs):
        """Initialize APIKey with default values"""
        # Set defaults
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("usage_count", 0)
        super().__init__(**kwargs)

    def activate(self) -> None:
        """Activate API key"""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate API key"""
        self.is_active = False

    def record_usage(self) -> None:
        """Record API key usage"""
        self.last_used_at = datetime.now()
        self.usage_count += 1

    def is_expired(self) -> bool:
        """Check if API key is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """Check if API key is valid for use"""
        return self.is_active and not self.is_expired()

    def generate_key_hash(self) -> str:
        """Generate API key hash"""
        import secrets
        import hashlib

        # Generate random API key
        api_key = f"tvgw_{secrets.token_urlsafe(32)}"

        # Hash the key for storage
        self.key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Return the plain key (only shown once)
        return api_key
