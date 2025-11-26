"""User domain model - Core business logic for users"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class User:
    """User entity representing a platform user"""

    id: UUID
    email: str
    name: Optional[str]
    is_active: bool
    totp_enabled: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self):
        """Validate user data"""
        if not self.email or "@" not in self.email:
            raise ValueError("Invalid email address")

        if self.name is not None and len(self.name.strip()) == 0:
            raise ValueError("Name cannot be empty string")

    def activate(self) -> None:
        """Activate user account"""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate user account"""
        self.is_active = False

    def enable_totp(self) -> None:
        """Enable two-factor authentication"""
        self.totp_enabled = True

    def disable_totp(self) -> None:
        """Disable two-factor authentication"""
        self.totp_enabled = False

    def update_last_login(self, timestamp: datetime) -> None:
        """Update last login timestamp"""
        self.last_login_at = timestamp
