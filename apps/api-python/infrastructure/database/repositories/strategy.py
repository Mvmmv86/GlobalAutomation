"""Strategy repository for CRUD operations"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.models.strategy import (
    Strategy,
    StrategyIndicator,
    StrategyCondition,
    StrategySignal,
    StrategyBacktestResult,
    SignalStatus,
)
from .base import BaseRepository


class StrategyRepository(BaseRepository[Strategy]):
    """Repository for Strategy model with specialized methods"""

    def __init__(self, session: AsyncSession):
        super().__init__(Strategy, session)

    async def get_with_relations(self, id: Union[str, UUID]) -> Optional[Strategy]:
        """Get strategy with all related data (indicators, conditions)"""
        query = (
            select(Strategy)
            .options(
                selectinload(Strategy.indicators),
                selectinload(Strategy.conditions),
            )
            .where(Strategy.id == str(id))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_strategies(self) -> List[Strategy]:
        """Get all active strategies"""
        query = (
            select(Strategy)
            .options(
                selectinload(Strategy.indicators),
                selectinload(Strategy.conditions),
            )
            .where(Strategy.is_active == True)
            .order_by(Strategy.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_bot_id(self, bot_id: str) -> List[Strategy]:
        """Get strategies linked to a specific bot"""
        query = (
            select(Strategy)
            .where(Strategy.bot_id == bot_id)
            .order_by(Strategy.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def activate(self, id: Union[str, UUID]) -> Optional[Strategy]:
        """Activate a strategy"""
        return await self.update(id, {"is_active": True})

    async def deactivate(self, id: Union[str, UUID]) -> Optional[Strategy]:
        """Deactivate a strategy"""
        return await self.update(id, {"is_active": False})

    async def get_strategies_with_stats(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get strategies with signal statistics"""
        query = select(Strategy).options(
            selectinload(Strategy.indicators),
        )

        if is_active is not None:
            query = query.where(Strategy.is_active == is_active)

        if user_id is not None:
            query = query.where(Strategy.created_by == user_id)

        query = query.order_by(Strategy.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        strategies = list(result.scalars().all())

        # Get stats for each strategy
        strategies_with_stats = []
        for strategy in strategies:
            # Count signals today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            signals_today = await self.session.execute(
                select(func.count(StrategySignal.id))
                .where(
                    and_(
                        StrategySignal.strategy_id == strategy.id,
                        StrategySignal.created_at >= today_start
                    )
                )
            )
            signals_count = signals_today.scalar() or 0

            # Get win rate from executed signals
            executed_signals = await self.session.execute(
                select(func.count(StrategySignal.id))
                .where(
                    and_(
                        StrategySignal.strategy_id == strategy.id,
                        StrategySignal.status == SignalStatus.EXECUTED
                    )
                )
            )
            total_executed = executed_signals.scalar() or 0

            strategies_with_stats.append({
                "strategy": strategy,
                "signals_today": signals_count,
                "total_executed": total_executed,
                "indicators": [ind.indicator_type.value for ind in strategy.indicators],
            })

        return strategies_with_stats


class StrategyIndicatorRepository(BaseRepository[StrategyIndicator]):
    """Repository for StrategyIndicator model"""

    def __init__(self, session: AsyncSession):
        super().__init__(StrategyIndicator, session)

    async def get_by_strategy(self, strategy_id: str) -> List[StrategyIndicator]:
        """Get all indicators for a strategy"""
        query = (
            select(StrategyIndicator)
            .where(StrategyIndicator.strategy_id == strategy_id)
            .order_by(StrategyIndicator.order_index)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_by_strategy(self, strategy_id: str) -> int:
        """Delete all indicators for a strategy"""
        from sqlalchemy import delete
        result = await self.session.execute(
            delete(StrategyIndicator).where(StrategyIndicator.strategy_id == strategy_id)
        )
        return result.rowcount


class StrategyConditionRepository(BaseRepository[StrategyCondition]):
    """Repository for StrategyCondition model"""

    def __init__(self, session: AsyncSession):
        super().__init__(StrategyCondition, session)

    async def get_by_strategy(self, strategy_id: str) -> List[StrategyCondition]:
        """Get all conditions for a strategy"""
        query = (
            select(StrategyCondition)
            .where(StrategyCondition.strategy_id == strategy_id)
            .order_by(StrategyCondition.order_index)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_type(
        self,
        strategy_id: str,
        condition_type: str
    ) -> List[StrategyCondition]:
        """Get conditions of a specific type for a strategy"""
        query = (
            select(StrategyCondition)
            .where(
                and_(
                    StrategyCondition.strategy_id == strategy_id,
                    StrategyCondition.condition_type == condition_type
                )
            )
            .order_by(StrategyCondition.order_index)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete_by_strategy(self, strategy_id: str) -> int:
        """Delete all conditions for a strategy"""
        from sqlalchemy import delete
        result = await self.session.execute(
            delete(StrategyCondition).where(StrategyCondition.strategy_id == strategy_id)
        )
        return result.rowcount


class StrategySignalRepository(BaseRepository[StrategySignal]):
    """Repository for StrategySignal model"""

    def __init__(self, session: AsyncSession):
        super().__init__(StrategySignal, session)

    async def get_by_strategy(
        self,
        strategy_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[StrategySignal]:
        """Get signals for a strategy"""
        query = (
            select(StrategySignal)
            .where(StrategySignal.strategy_id == strategy_id)
            .order_by(StrategySignal.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_recent_signals(
        self,
        strategy_id: str,
        hours: int = 24
    ) -> List[StrategySignal]:
        """Get signals from the last N hours"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        query = (
            select(StrategySignal)
            .where(
                and_(
                    StrategySignal.strategy_id == strategy_id,
                    StrategySignal.created_at >= cutoff
                )
            )
            .order_by(StrategySignal.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_pending_signals(self) -> List[StrategySignal]:
        """Get all pending signals"""
        query = (
            select(StrategySignal)
            .where(StrategySignal.status == SignalStatus.PENDING)
            .order_by(StrategySignal.created_at)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_executed(
        self,
        id: Union[str, UUID],
        bot_signal_id: str
    ) -> Optional[StrategySignal]:
        """Mark signal as executed"""
        return await self.update(id, {
            "status": SignalStatus.EXECUTED,
            "bot_signal_id": bot_signal_id
        })

    async def mark_failed(self, id: Union[str, UUID]) -> Optional[StrategySignal]:
        """Mark signal as failed"""
        return await self.update(id, {"status": SignalStatus.FAILED})

    async def count_by_status(
        self,
        strategy_id: str,
        status: SignalStatus
    ) -> int:
        """Count signals by status"""
        result = await self.session.execute(
            select(func.count(StrategySignal.id))
            .where(
                and_(
                    StrategySignal.strategy_id == strategy_id,
                    StrategySignal.status == status
                )
            )
        )
        return result.scalar() or 0


class StrategyBacktestResultRepository(BaseRepository[StrategyBacktestResult]):
    """Repository for StrategyBacktestResult model"""

    def __init__(self, session: AsyncSession):
        super().__init__(StrategyBacktestResult, session)

    async def get_by_strategy(
        self,
        strategy_id: str,
        skip: int = 0,
        limit: int = 10
    ) -> List[StrategyBacktestResult]:
        """Get backtest results for a strategy"""
        query = (
            select(StrategyBacktestResult)
            .where(StrategyBacktestResult.strategy_id == strategy_id)
            .order_by(StrategyBacktestResult.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest(self, strategy_id: str) -> Optional[StrategyBacktestResult]:
        """Get the most recent backtest result for a strategy"""
        query = (
            select(StrategyBacktestResult)
            .where(StrategyBacktestResult.strategy_id == strategy_id)
            .order_by(StrategyBacktestResult.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_best_by_win_rate(
        self,
        strategy_id: str
    ) -> Optional[StrategyBacktestResult]:
        """Get backtest with highest win rate"""
        query = (
            select(StrategyBacktestResult)
            .where(StrategyBacktestResult.strategy_id == strategy_id)
            .order_by(StrategyBacktestResult.win_rate.desc().nulls_last())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
