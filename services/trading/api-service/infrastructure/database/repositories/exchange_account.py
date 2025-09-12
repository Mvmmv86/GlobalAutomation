"""ExchangeAccount repository"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import and_, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.models.exchange_account import (
    ExchangeAccount,
    ExchangeType,
    ExchangeEnvironment,
)
from infrastructure.database.repositories.base import BaseRepository


class ExchangeAccountRepository(BaseRepository[ExchangeAccount]):
    """Repository for ExchangeAccount operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(ExchangeAccount, session)

    async def get_user_accounts(
        self, user_id: Union[str, UUID], active_only: bool = True
    ) -> List[ExchangeAccount]:
        """Get all exchange accounts for a user"""
        filters = {"user_id": str(user_id)}
        if active_only:
            filters["is_active"] = True

        return await self.get_multi(filters=filters, order_by="-created_at")

    async def get_user_active_accounts(
        self, user_id: Union[str, UUID]
    ) -> List[ExchangeAccount]:
        """Get active exchange accounts for a user"""
        return await self.get_user_accounts(user_id, active_only=True)

    async def get_by_exchange_type(
        self,
        user_id: Union[str, UUID],
        exchange_type: ExchangeType,
        environment: Optional[ExchangeEnvironment] = None,
    ) -> List[ExchangeAccount]:
        """Get accounts by exchange type and environment"""
        filters = {
            "user_id": str(user_id),
            "exchange_type": exchange_type,
            "is_active": True,
        }

        if environment:
            filters["environment"] = environment

        return await self.get_multi(filters=filters)

    async def get_default_account(
        self,
        user_id: Union[str, UUID],
        exchange_type: ExchangeType,
        environment: ExchangeEnvironment = ExchangeEnvironment.TESTNET,
    ) -> Optional[ExchangeAccount]:
        """Get default account for specific exchange and environment"""
        result = await self.session.execute(
            select(ExchangeAccount).where(
                and_(
                    ExchangeAccount.user_id == str(user_id),
                    ExchangeAccount.exchange_type == exchange_type,
                    ExchangeAccount.environment == environment,
                    ExchangeAccount.is_default == True,
                    ExchangeAccount.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_with_relationships(
        self, account_id: Union[str, UUID]
    ) -> Optional[ExchangeAccount]:
        """Get account with all relationships loaded"""
        result = await self.session.execute(
            select(ExchangeAccount)
            .options(
                selectinload(ExchangeAccount.user),
                selectinload(ExchangeAccount.orders),
                selectinload(ExchangeAccount.positions),
            )
            .where(ExchangeAccount.id == str(account_id))
        )
        return result.scalar_one_or_none()

    async def get_healthy_accounts(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        exchange_type: Optional[ExchangeType] = None,
    ) -> List[ExchangeAccount]:
        """Get accounts with healthy status"""
        filters = {"is_active": True, "health_status": "healthy"}

        if user_id:
            filters["user_id"] = str(user_id)
        if exchange_type:
            filters["exchange_type"] = exchange_type

        return await self.get_multi(filters=filters)

    async def get_tradeable_accounts(
        self, user_id: Union[str, UUID], exchange_type: Optional[ExchangeType] = None
    ) -> List[ExchangeAccount]:
        """Get accounts that can execute trades"""
        result = await self.session.execute(
            select(ExchangeAccount)
            .where(
                and_(
                    ExchangeAccount.user_id == str(user_id),
                    ExchangeAccount.is_active == True,
                    ExchangeAccount.health_status == "healthy",
                    ExchangeAccount.exchange_type == exchange_type
                    if exchange_type
                    else True,
                )
            )
            .order_by(
                ExchangeAccount.is_default.desc(), ExchangeAccount.created_at.desc()
            )
        )
        return list(result.scalars().all())

    async def set_as_default(
        self,
        account_id: Union[str, UUID],
        user_id: Union[str, UUID],
        exchange_type: ExchangeType,
        environment: ExchangeEnvironment,
    ) -> bool:
        """Set account as default and unset others"""
        # First, unset all other default accounts for this exchange/environment
        await self.session.execute(
            update(ExchangeAccount)
            .where(
                and_(
                    ExchangeAccount.user_id == str(user_id),
                    ExchangeAccount.exchange_type == exchange_type,
                    ExchangeAccount.environment == environment,
                    ExchangeAccount.id != str(account_id),
                )
            )
            .values(is_default=False)
        )

        # Set the target account as default
        result = await self.update(account_id, {"is_default": True})
        return result is not None

    async def update_health_status(
        self, account_id: Union[str, UUID], status: str, error: Optional[str] = None
    ) -> bool:
        """Update account health status"""
        account = await self.get(account_id)
        if account:
            account.update_health_status(status, error)
            await self.session.flush()
            return True
        return False

    async def record_order_stats(
        self, account_id: Union[str, UUID], success: bool
    ) -> bool:
        """Record order statistics"""
        account = await self.get(account_id)
        if account:
            account.increment_order_stats(success)
            await self.session.flush()
            return True
        return False

    async def get_accounts_by_health(
        self, health_status: str, skip: int = 0, limit: int = 100
    ) -> List[ExchangeAccount]:
        """Get accounts by health status"""
        return await self.get_multi(
            filters={"health_status": health_status}, skip=skip, limit=limit
        )

    async def get_accounts_needing_health_check(
        self, max_age_minutes: int = 60
    ) -> List[ExchangeAccount]:
        """Get accounts that need health check"""
        from datetime import datetime, timedelta

        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)

        result = await self.session.execute(
            select(ExchangeAccount).where(
                and_(
                    ExchangeAccount.is_active == True,
                    or_(
                        ExchangeAccount.last_health_check.is_(None),
                        ExchangeAccount.last_health_check < cutoff_time,
                    ),
                )
            )
        )
        return list(result.scalars().all())

    async def get_performance_stats(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        exchange_type: Optional[ExchangeType] = None,
    ) -> Dict[str, Any]:
        """Get performance statistics for accounts"""
        base_query = select(ExchangeAccount)

        conditions = [ExchangeAccount.is_active == True]

        if user_id:
            conditions.append(ExchangeAccount.user_id == str(user_id))
        if exchange_type:
            conditions.append(ExchangeAccount.exchange_type == exchange_type)

        if conditions:
            base_query = base_query.where(and_(*conditions))

        # Get statistics
        stats_result = await self.session.execute(
            base_query.with_only_columns(
                func.count(ExchangeAccount.id).label("total_accounts"),
                func.sum(ExchangeAccount.total_orders).label("total_orders"),
                func.sum(ExchangeAccount.successful_orders).label("successful_orders"),
                func.sum(ExchangeAccount.failed_orders).label("failed_orders"),
                func.avg(
                    ExchangeAccount.successful_orders
                    * 100.0
                    / func.nullif(ExchangeAccount.total_orders, 0)
                ).label("avg_success_rate"),
            )
        )

        stats = stats_result.first()

        # Get health distribution
        health_result = await self.session.execute(
            base_query.with_only_columns(
                ExchangeAccount.health_status,
                func.count(ExchangeAccount.id).label("count"),
            ).group_by(ExchangeAccount.health_status)
        )

        health_distribution = {row.health_status: row.count for row in health_result}

        return {
            "total_accounts": stats.total_accounts or 0,
            "total_orders": stats.total_orders or 0,
            "successful_orders": stats.successful_orders or 0,
            "failed_orders": stats.failed_orders or 0,
            "average_success_rate": float(stats.avg_success_rate or 0),
            "health_distribution": health_distribution,
        }

    async def search_accounts(
        self,
        search_term: str,
        user_id: Optional[Union[str, UUID]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ExchangeAccount]:
        """Search accounts by name"""
        query = (
            self._build_query(
                filters={"user_id": str(user_id)} if user_id else None,
                search=search_term,
                search_fields=["name"],
            )
            .offset(skip)
            .limit(limit)
            .order_by(ExchangeAccount.created_at.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_exchange_distribution(
        self, user_id: Optional[Union[str, UUID]] = None
    ) -> Dict[str, Dict[str, int]]:
        """Get distribution of accounts by exchange and environment"""
        base_query = select(ExchangeAccount).where(ExchangeAccount.is_active == True)

        if user_id:
            base_query = base_query.where(ExchangeAccount.user_id == str(user_id))

        result = await self.session.execute(
            base_query.with_only_columns(
                ExchangeAccount.exchange_type,
                ExchangeAccount.environment,
                func.count(ExchangeAccount.id).label("count"),
            ).group_by(ExchangeAccount.exchange_type, ExchangeAccount.environment)
        )

        distribution = {}
        for row in result:
            exchange = row.exchange_type.value
            environment = row.environment.value

            if exchange not in distribution:
                distribution[exchange] = {}
            distribution[exchange][environment] = row.count

        return distribution
