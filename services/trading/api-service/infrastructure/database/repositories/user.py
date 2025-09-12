"""User and APIKey repositories"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import and_, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.models.user import User, APIKey
from infrastructure.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_with_relationships(self, user_id: Union[str, UUID]) -> Optional[User]:
        """Get user with all relationships loaded"""
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.api_keys),
                selectinload(User.exchange_accounts),
                selectinload(User.webhooks),
            )
            .where(User.id == str(user_id))
        )
        return result.scalar_one_or_none()

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all active users"""
        return await self.get_multi(
            skip=skip, limit=limit, filters={"is_active": True}, order_by="-created_at"
        )

    async def get_verified_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all verified users"""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"is_verified": True, "is_active": True},
            order_by="-created_at",
        )

    async def search_users(
        self, search_term: str, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Search users by email or name"""
        query = (
            self._build_query(search=search_term, search_fields=["email", "name"])
            .offset(skip)
            .limit(limit)
            .order_by(User.created_at.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_locked_users(self) -> List[User]:
        """Get users who are currently locked"""
        result = await self.session.execute(
            select(User).where(
                and_(User.locked_until.isnot(None), User.locked_until > func.now())
            )
        )
        return list(result.scalars().all())

    async def get_users_with_totp_enabled(
        self, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Get users with TOTP enabled"""
        return await self.get_multi(
            skip=skip, limit=limit, filters={"totp_enabled": True, "is_active": True}
        )

    async def update_last_login(self, user_id: Union[str, UUID]) -> bool:
        """Update user's last login timestamp"""
        result = await self.update(
            user_id,
            {
                "last_login_at": func.now(),
                "failed_login_attempts": 0,
                "locked_until": None,
            },
        )
        return result is not None

    async def increment_failed_login(self, user_id: Union[str, UUID]) -> Optional[User]:
        """Increment failed login attempts for user"""
        user = await self.get(user_id)
        if user:
            user.increment_failed_login()
            await self.session.flush()
            await self.session.refresh(user)
        return user

    async def get_stats(self) -> Dict[str, int]:
        """Get user statistics"""
        total_result = await self.session.execute(select(func.count(User.id)))
        active_result = await self.session.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        verified_result = await self.session.execute(
            select(func.count(User.id)).where(User.is_verified == True)
        )
        totp_result = await self.session.execute(
            select(func.count(User.id)).where(User.totp_enabled == True)
        )

        return {
            "total": total_result.scalar() or 0,
            "active": active_result.scalar() or 0,
            "verified": verified_result.scalar() or 0,
            "totp_enabled": totp_result.scalar() or 0,
        }


class APIKeyRepository(BaseRepository[APIKey]):
    """Repository for APIKey operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(APIKey, session)

    async def get_by_key_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by key hash"""
        result = await self.session.execute(
            select(APIKey)
            .options(selectinload(APIKey.user))
            .where(APIKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def get_user_api_keys(
        self, user_id: Union[str, UUID], active_only: bool = True
    ) -> List[APIKey]:
        """Get all API keys for a user"""
        filters = {"user_id": str(user_id)}
        if active_only:
            filters["is_active"] = True

        return await self.get_multi(filters=filters, order_by="-created_at")

    async def get_active_keys(self, skip: int = 0, limit: int = 100) -> List[APIKey]:
        """Get all active API keys"""
        result = await self.session.execute(
            select(APIKey)
            .options(selectinload(APIKey.user))
            .where(
                and_(
                    APIKey.is_active == True,
                    or_(APIKey.expires_at.is_(None), APIKey.expires_at > func.now()),
                )
            )
            .order_by(APIKey.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_expired_keys(self) -> List[APIKey]:
        """Get all expired API keys"""
        result = await self.session.execute(
            select(APIKey).where(
                and_(APIKey.expires_at.isnot(None), APIKey.expires_at <= func.now())
            )
        )
        return list(result.scalars().all())

    async def record_usage(self, api_key_id: Union[str, UUID]) -> bool:
        """Record API key usage"""
        api_key = await self.get(api_key_id)
        if api_key:
            api_key.record_usage()
            await self.session.flush()
            return True
        return False

    async def get_usage_stats(
        self, user_id: Optional[Union[str, UUID]] = None
    ) -> Dict[str, Any]:
        """Get API key usage statistics"""
        base_query = select(APIKey)

        if user_id:
            base_query = base_query.where(APIKey.user_id == str(user_id))

        # Total API keys
        total_result = await self.session.execute(
            select(func.count(APIKey.id)).select_from(base_query.subquery())
        )

        # Active API keys
        active_result = await self.session.execute(
            base_query.where(APIKey.is_active == True).with_only_columns(
                func.count(APIKey.id)
            )
        )

        # Usage statistics
        usage_result = await self.session.execute(
            base_query.with_only_columns(
                func.sum(APIKey.usage_count).label("total_usage"),
                func.avg(APIKey.usage_count).label("avg_usage"),
                func.max(APIKey.usage_count).label("max_usage"),
            )
        )

        usage_stats = usage_result.first()

        return {
            "total_keys": total_result.scalar() or 0,
            "active_keys": active_result.scalar() or 0,
            "total_usage": usage_stats.total_usage or 0,
            "average_usage": float(usage_stats.avg_usage or 0),
            "max_usage": usage_stats.max_usage or 0,
        }

    async def cleanup_expired_keys(self) -> int:
        """Soft delete expired API keys"""
        expired_keys = await self.get_expired_keys()
        count = 0

        for key in expired_keys:
            if await self.soft_delete(key.id):
                count += 1

        return count

    async def get_most_used_keys(
        self, limit: int = 10, user_id: Optional[Union[str, UUID]] = None
    ) -> List[APIKey]:
        """Get most used API keys"""
        query = (
            select(APIKey)
            .options(selectinload(APIKey.user))
            .order_by(APIKey.usage_count.desc())
            .limit(limit)
        )

        if user_id:
            query = query.where(APIKey.user_id == str(user_id))

        result = await self.session.execute(query)
        return list(result.scalars().all())
