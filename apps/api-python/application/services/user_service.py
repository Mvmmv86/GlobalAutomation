"""User service with business logic"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from infrastructure.database.repositories import UserRepository, APIKeyRepository
from infrastructure.database.models.user import User, APIKey


class UserService:
    """Business logic for user operations"""

    def __init__(
        self, user_repository: UserRepository, api_key_repository: APIKeyRepository
    ):
        self.user_repository = user_repository
        self.api_key_repository = api_key_repository

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        return await self.user_repository.get(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email (case insensitive)"""
        return await self.user_repository.get_by_email(email)

    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user"""
        # Business rules validation
        if await self.user_repository.get_by_email(user_data["email"]):
            raise ValueError("Email already registered")

        # Ensure email is lowercase
        user_data["email"] = user_data["email"].lower()

        return await self.user_repository.create(user_data)

    async def update_user(
        self, user_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[User]:
        """Update user data"""
        # Remove sensitive fields that shouldn't be updated directly
        sensitive_fields = {
            "password_hash",
            "totp_secret",
            "failed_login_attempts",
            "locked_until",
        }
        update_data = {
            k: v for k, v in update_data.items() if k not in sensitive_fields
        }

        return await self.user_repository.update(user_id, update_data)

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await self.user_repository.get_by_email(email)

        if not user:
            return None

        # Check if user is locked
        if user.is_locked():
            return None

        # Verify password (would use proper password hashing here)
        if not user.verify_password(password):
            await self.user_repository.increment_failed_login(user.id)
            return None

        # Update last login
        await self.user_repository.update_last_login(user.id)
        return user

    async def change_password(
        self, user_id: UUID, old_password: str, new_password: str
    ) -> bool:
        """Change user password"""
        user = await self.user_repository.get(user_id)

        if not user or not user.verify_password(old_password):
            return False

        # Hash new password and update
        hashed_password = user.hash_password(new_password)
        await self.user_repository.update(user_id, {"password_hash": hashed_password})

        return True

    async def enable_2fa(self, user_id: UUID, totp_secret: str) -> bool:
        """Enable 2FA for user"""
        return (
            await self.user_repository.update(
                user_id, {"totp_secret": totp_secret, "totp_enabled": True}
            )
            is not None
        )

    async def disable_2fa(self, user_id: UUID) -> bool:
        """Disable 2FA for user"""
        return (
            await self.user_repository.update(
                user_id, {"totp_secret": None, "totp_enabled": False}
            )
            is not None
        )

    async def verify_2fa_token(self, user_id: UUID, token: str) -> bool:
        """Verify 2FA token"""
        user = await self.user_repository.get(user_id)

        if not user or not user.totp_enabled:
            return False

        return user.verify_totp_token(token)

    async def get_user_api_keys(self, user_id: UUID) -> List[APIKey]:
        """Get all API keys for user"""
        return await self.api_key_repository.get_user_api_keys(user_id)

    async def create_api_key(
        self, user_id: UUID, name: str, expires_days: Optional[int] = None
    ) -> APIKey:
        """Create new API key for user"""
        key_data = {"user_id": str(user_id), "name": name, "is_active": True}

        if expires_days:
            key_data["expires_at"] = datetime.now() + timedelta(days=expires_days)

        api_key = await self.api_key_repository.create(key_data)

        # Generate the actual key hash (would be more secure in production)
        api_key.generate_key_hash()
        await self.api_key_repository.update(api_key.id, {"key_hash": api_key.key_hash})

        return api_key

    async def revoke_api_key(self, user_id: UUID, key_id: UUID) -> bool:
        """Revoke an API key"""
        # Verify the key belongs to the user
        api_key = await self.api_key_repository.get(key_id)

        if not api_key or api_key.user_id != str(user_id):
            return False

        return await self.api_key_repository.soft_delete(key_id)

    async def authenticate_api_key(self, key_hash: str) -> Optional[User]:
        """Authenticate user by API key"""
        api_key = await self.api_key_repository.get_by_key_hash(key_hash)

        if not api_key or not api_key.is_active:
            return None

        if api_key.is_expired():
            return None

        # Record usage
        await self.api_key_repository.record_usage(api_key.id)

        return await self.user_repository.get(api_key.user_id)

    async def get_user_stats(self) -> Dict[str, int]:
        """Get user statistics"""
        return await self.user_repository.get_stats()

    async def search_users(
        self, search_term: str, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Search users"""
        return await self.user_repository.search_users(search_term, skip, limit)

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get active users"""
        return await self.user_repository.get_active_users(skip, limit)

    async def deactivate_user(
        self, user_id: UUID, reason: Optional[str] = None
    ) -> bool:
        """Deactivate user account"""
        update_data = {"is_active": False}
        if reason:
            update_data["deactivation_reason"] = reason

        return await self.user_repository.update(user_id, update_data) is not None

    async def reactivate_user(self, user_id: UUID) -> bool:
        """Reactivate user account"""
        return (
            await self.user_repository.update(
                user_id, {"is_active": True, "deactivation_reason": None}
            )
            is not None
        )
