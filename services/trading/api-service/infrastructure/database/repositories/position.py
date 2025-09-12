"""Position repository"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.models.position import (
    Position,
    PositionSide,
    PositionStatus,
)
from infrastructure.database.repositories.base import BaseRepository


class PositionRepository(BaseRepository[Position]):
    """Repository for Position operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(Position, session)

    async def get_by_external_id(self, external_id: str) -> Optional[Position]:
        """Get position by exchange external ID"""
        result = await self.session.execute(
            select(Position)
            .options(selectinload(Position.exchange_account))
            .where(Position.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def get_user_positions(
        self,
        user_id: Union[str, UUID],
        status: Optional[PositionStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Position]:
        """Get positions for a user"""
        # Join with exchange_account to filter by user
        query = (
            select(Position)
            .join(Position.exchange_account)
            .options(selectinload(Position.exchange_account))
            .where(Position.exchange_account.has(user_id=str(user_id)))
        )

        if status:
            query = query.where(Position.status == status)

        query = query.order_by(Position.last_update_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_account_positions(
        self,
        account_id: Union[str, UUID],
        status: Optional[PositionStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Position]:
        """Get positions for a specific exchange account"""
        filters = {"exchange_account_id": str(account_id)}
        if status:
            filters["status"] = status

        return await self.get_multi(
            filters=filters, skip=skip, limit=limit, order_by="-last_update_at"
        )

    async def get_open_positions(
        self,
        account_id: Optional[Union[str, UUID]] = None,
        symbol: Optional[str] = None,
    ) -> List[Position]:
        """Get all open positions"""
        conditions = [
            Position.status.in_([PositionStatus.OPEN, PositionStatus.CLOSING])
        ]

        if account_id:
            conditions.append(Position.exchange_account_id == str(account_id))
        if symbol:
            conditions.append(Position.symbol == symbol.upper())

        result = await self.session.execute(
            select(Position)
            .options(selectinload(Position.exchange_account))
            .where(and_(*conditions))
            .order_by(Position.last_update_at.desc())
        )
        return list(result.scalars().all())

    async def get_position_by_symbol(
        self,
        account_id: Union[str, UUID],
        symbol: str,
        side: Optional[PositionSide] = None,
    ) -> Optional[Position]:
        """Get position for a specific symbol and account"""
        conditions = [
            Position.exchange_account_id == str(account_id),
            Position.symbol == symbol.upper(),
            Position.status.in_([PositionStatus.OPEN, PositionStatus.CLOSING]),
        ]

        if side:
            conditions.append(Position.side == side)

        result = await self.session.execute(
            select(Position)
            .options(selectinload(Position.exchange_account))
            .where(and_(*conditions))
            .order_by(Position.last_update_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_positions_by_symbol(
        self,
        symbol: str,
        account_id: Optional[Union[str, UUID]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Position]:
        """Get positions for a specific symbol"""
        filters = {"symbol": symbol.upper()}
        if account_id:
            filters["exchange_account_id"] = str(account_id)

        return await self.get_multi(
            filters=filters, skip=skip, limit=limit, order_by="-last_update_at"
        )

    async def get_profitable_positions(
        self,
        account_id: Optional[Union[str, UUID]] = None,
        min_pnl: Optional[Decimal] = None,
    ) -> List[Position]:
        """Get positions with positive PnL"""
        conditions = [
            Position.status == PositionStatus.OPEN,
            Position.unrealized_pnl + Position.realized_pnl > 0,
        ]

        if account_id:
            conditions.append(Position.exchange_account_id == str(account_id))
        if min_pnl:
            conditions.append(
                Position.unrealized_pnl + Position.realized_pnl >= min_pnl
            )

        result = await self.session.execute(
            select(Position)
            .options(selectinload(Position.exchange_account))
            .where(and_(*conditions))
            .order_by((Position.unrealized_pnl + Position.realized_pnl).desc())
        )
        return list(result.scalars().all())

    async def get_positions_at_risk(
        self,
        risk_threshold: float = 80.0,
        account_id: Optional[Union[str, UUID]] = None,
    ) -> List[Position]:
        """Get positions at risk of liquidation"""
        conditions = [
            Position.status == PositionStatus.OPEN,
            Position.liquidation_price.isnot(None),
            Position.mark_price.isnot(None),
        ]

        if account_id:
            conditions.append(Position.exchange_account_id == str(account_id))

        result = await self.session.execute(
            select(Position)
            .options(selectinload(Position.exchange_account))
            .where(and_(*conditions))
        )

        # Filter by risk threshold in Python since SQL calculation is complex
        positions = list(result.scalars().all())
        at_risk = []

        for position in positions:
            if position.is_at_risk(risk_threshold):
                at_risk.append(position)

        # Sort by risk level (closest to liquidation first)
        return sorted(at_risk, key=lambda p: abs(p.mark_price - p.liquidation_price))

    async def get_positions_by_timeframe(
        self,
        start_time: datetime,
        end_time: datetime,
        account_id: Optional[Union[str, UUID]] = None,
        status: Optional[PositionStatus] = None,
    ) -> List[Position]:
        """Get positions within a time frame"""
        conditions = [Position.opened_at >= start_time, Position.opened_at <= end_time]

        if account_id:
            conditions.append(Position.exchange_account_id == str(account_id))
        if status:
            conditions.append(Position.status == status)

        result = await self.session.execute(
            select(Position)
            .options(selectinload(Position.exchange_account))
            .where(and_(*conditions))
            .order_by(Position.opened_at.desc())
        )
        return list(result.scalars().all())

    async def update_position_size(
        self, position_id: Union[str, UUID], new_size: Decimal, avg_price: Decimal
    ) -> bool:
        """Update position size"""
        position = await self.get(position_id)
        if position:
            position.update_size(new_size, avg_price)
            await self.session.flush()
            return True
        return False

    async def update_position_pnl(
        self,
        position_id: Union[str, UUID],
        unrealized: Decimal,
        realized: Optional[Decimal] = None,
    ) -> bool:
        """Update position PnL"""
        position = await self.get(position_id)
        if position:
            position.update_pnl(unrealized, realized)
            await self.session.flush()
            return True
        return False

    async def update_mark_price(
        self, position_id: Union[str, UUID], mark_price: Decimal
    ) -> bool:
        """Update position mark price and recalculate PnL"""
        position = await self.get(position_id)
        if position:
            position.update_mark_price(mark_price)
            await self.session.flush()
            return True
        return False

    async def close_position(
        self, position_id: Union[str, UUID], final_pnl: Optional[Decimal] = None
    ) -> bool:
        """Close a position"""
        position = await self.get(position_id)
        if position:
            position.close(final_pnl)
            await self.session.flush()
            return True
        return False

    async def liquidate_position(
        self, position_id: Union[str, UUID], liquidation_price: Decimal
    ) -> bool:
        """Mark position as liquidated"""
        position = await self.get(position_id)
        if position:
            position.liquidate(liquidation_price)
            await self.session.flush()
            return True
        return False

    async def get_position_stats(
        self,
        account_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get position statistics"""
        start_time = datetime.now() - timedelta(days=days)

        base_query = select(Position).where(Position.opened_at >= start_time)

        if account_id:
            base_query = base_query.where(
                Position.exchange_account_id == str(account_id)
            )
        elif user_id:
            base_query = base_query.join(Position.exchange_account).where(
                Position.exchange_account.has(user_id=str(user_id))
            )

        # Basic stats
        stats_result = await self.session.execute(
            base_query.with_only_columns(
                func.count(Position.id).label("total_positions"),
                func.sum(Position.size).label("total_size"),
                func.sum(Position.realized_pnl + Position.unrealized_pnl).label(
                    "total_pnl"
                ),
                func.sum(Position.total_fees).label("total_fees"),
                func.avg(Position.leverage).label("avg_leverage"),
            )
        )

        stats = stats_result.first()

        # Status distribution
        status_result = await self.session.execute(
            base_query.with_only_columns(
                Position.status, func.count(Position.id).label("count")
            ).group_by(Position.status)
        )

        status_distribution = {row.status.value: row.count for row in status_result}

        # Side distribution
        side_result = await self.session.execute(
            base_query.with_only_columns(
                Position.side,
                func.count(Position.id).label("count"),
                func.sum(Position.size).label("total_size"),
                func.sum(Position.realized_pnl + Position.unrealized_pnl).label(
                    "total_pnl"
                ),
            ).group_by(Position.side)
        )

        side_distribution = {
            row.side.value: {
                "count": row.count,
                "total_size": float(row.total_size or 0),
                "total_pnl": float(row.total_pnl or 0),
            }
            for row in side_result
        }

        # Profitable vs losing positions
        profitable_result = await self.session.execute(
            base_query.with_only_columns(
                func.count(Position.id).label("profitable_count")
            ).where(Position.realized_pnl + Position.unrealized_pnl > 0)
        )

        profitable_count = profitable_result.scalar() or 0
        total_count = stats.total_positions or 0
        losing_count = total_count - profitable_count

        return {
            "total_positions": total_count,
            "profitable_positions": profitable_count,
            "losing_positions": losing_count,
            "win_rate": (profitable_count / total_count * 100)
            if total_count > 0
            else 0,
            "total_size": float(stats.total_size or 0),
            "total_pnl": float(stats.total_pnl or 0),
            "total_fees": float(stats.total_fees or 0),
            "average_leverage": float(stats.avg_leverage or 0),
            "status_distribution": status_distribution,
            "side_distribution": side_distribution,
        }

    async def get_most_active_symbols(
        self,
        limit: int = 10,
        account_id: Optional[Union[str, UUID]] = None,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get most actively traded symbols by position count"""
        start_time = datetime.now() - timedelta(days=days)

        base_query = select(Position).where(Position.opened_at >= start_time)

        if account_id:
            base_query = base_query.where(
                Position.exchange_account_id == str(account_id)
            )

        result = await self.session.execute(
            base_query.with_only_columns(
                Position.symbol,
                func.count(Position.id).label("position_count"),
                func.sum(Position.size).label("total_size"),
                func.sum(Position.realized_pnl + Position.unrealized_pnl).label(
                    "total_pnl"
                ),
            )
            .group_by(Position.symbol)
            .order_by(func.count(Position.id).desc())
            .limit(limit)
        )

        return [
            {
                "symbol": row.symbol,
                "position_count": row.position_count,
                "total_size": float(row.total_size or 0),
                "total_pnl": float(row.total_pnl or 0),
            }
            for row in result
        ]

    async def search_positions(
        self,
        search_term: str,
        user_id: Optional[Union[str, UUID]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Position]:
        """Search positions by symbol or external ID"""
        conditions = [
            or_(
                Position.symbol.ilike(f"%{search_term.upper()}%"),
                Position.external_id.ilike(f"%{search_term}%"),
            )
        ]

        if user_id:
            conditions.append(Position.exchange_account.has(user_id=str(user_id)))

        result = await self.session.execute(
            select(Position)
            .options(selectinload(Position.exchange_account))
            .where(and_(*conditions))
            .order_by(Position.last_update_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_portfolio_summary(
        self,
        user_id: Optional[Union[str, UUID]] = None,
        account_id: Optional[Union[str, UUID]] = None,
    ) -> Dict[str, Any]:
        """Get portfolio summary for open positions"""
        conditions = [Position.status == PositionStatus.OPEN]

        if account_id:
            conditions.append(Position.exchange_account_id == str(account_id))
        elif user_id:
            conditions.append(Position.exchange_account.has(user_id=str(user_id)))

        result = await self.session.execute(select(Position).where(and_(*conditions)))

        positions = list(result.scalars().all())

        if not positions:
            return {
                "total_positions": 0,
                "total_unrealized_pnl": 0.0,
                "total_realized_pnl": 0.0,
                "total_pnl": 0.0,
                "total_margin": 0.0,
                "total_fees": 0.0,
                "symbols": [],
            }

        total_unrealized = sum(p.unrealized_pnl for p in positions)
        total_realized = sum(p.realized_pnl for p in positions)
        total_margin = sum(p.initial_margin for p in positions)
        total_fees = sum(p.total_fees for p in positions)

        # Group by symbol
        symbol_summary = {}
        for position in positions:
            symbol = position.symbol
            if symbol not in symbol_summary:
                symbol_summary[symbol] = {
                    "symbol": symbol,
                    "positions": [],
                    "total_size": Decimal("0"),
                    "total_pnl": Decimal("0"),
                    "total_margin": Decimal("0"),
                }

            symbol_summary[symbol]["positions"].append(position.id)
            symbol_summary[symbol]["total_size"] += position.size
            symbol_summary[symbol]["total_pnl"] += (
                position.unrealized_pnl + position.realized_pnl
            )
            symbol_summary[symbol]["total_margin"] += position.initial_margin

        return {
            "total_positions": len(positions),
            "total_unrealized_pnl": float(total_unrealized),
            "total_realized_pnl": float(total_realized),
            "total_pnl": float(total_unrealized + total_realized),
            "total_margin": float(total_margin),
            "total_fees": float(total_fees),
            "symbols": [
                {
                    "symbol": data["symbol"],
                    "position_count": len(data["positions"]),
                    "total_size": float(data["total_size"]),
                    "total_pnl": float(data["total_pnl"]),
                    "total_margin": float(data["total_margin"]),
                }
                for data in symbol_summary.values()
            ],
        }
