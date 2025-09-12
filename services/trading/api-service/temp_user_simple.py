"""Temporary simplified user model for testing"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.base import Base


class UserSimple(Base):
    """Simplified User model with only existing columns"""

    __tablename__ = "users"

    # Basic info - only columns that exist in DB
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))

    # Status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # 2FA
    totp_secret: Mapped[Optional[str]] = mapped_column(String(32))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Activity tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    def verify_password(self, password: str) -> bool:
        """Verify password (mock implementation)"""
        # Simple mock for testing
        import hashlib

        expected = hashlib.sha256(password.encode()).hexdigest()
        return self.password_hash == expected

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password (mock implementation)"""
        import hashlib

        return hashlib.sha256(password.encode()).hexdigest()
