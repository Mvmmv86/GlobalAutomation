"""Order repository"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.models.order import Order, OrderStatus, TimeInForce
from infrastructure.database.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Repository for Order operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def get_by_client_order_id(self, client_order_id: str) -> Optional[Order]:
        """Get order by client order ID"""
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.exchange_account))
            .where(Order.client_order_id == client_order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_id: str) -> Optional[Order]:
        """Get order by exchange external ID"""
        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.exchange_account))
            .where(Order.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def get_user_orders(
        self,
        user_id: Union[str, UUID],
        skip: int = 0,
        limit: int = 100,
        status: Optional[OrderStatus] = None,
        symbol: Optional[str] = None,
    ) -> List[Order]:
        """Get orders for a user"""
        # Join with exchange_account to filter by user
        query = (
            select(Order)
            .join(Order.exchange_account)
            .options(selectinload(Order.exchange_account))
            .where(Order.exchange_account.has(user_id=str(user_id)))
        )

        if status:
            query = query.where(Order.status == status)
        if symbol:
            query = query.where(Order.symbol == symbol.upper())

        query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_account_orders(
        self,
        account_id: Union[str, UUID],
        skip: int = 0,
        limit: int = 100,
        status: Optional[OrderStatus] = None,
    ) -> List[Order]:
        """Get orders for a specific exchange account"""
        filters = {"exchange_account_id": str(account_id)}
        if status:
            filters["status"] = status

        return await self.get_multi(
            filters=filters, skip=skip, limit=limit, order_by="-created_at"
        )

    async def get_open_orders(
        self,
        account_id: Optional[Union[str, UUID]] = None,
        symbol: Optional[str] = None,
    ) -> List[Order]:
        """Get all open orders"""
        conditions = [
            Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED])
        ]

        if account_id:
            conditions.append(Order.exchange_account_id == str(account_id))
        if symbol:
            conditions.append(Order.symbol == symbol.upper())

        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.exchange_account))
            .where(and_(*conditions))
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_pending_orders(
        self, account_id: Optional[Union[str, UUID]] = None
    ) -> List[Order]:
        """Get orders pending submission"""
        conditions = [Order.status == OrderStatus.PENDING]

        if account_id:
            conditions.append(Order.exchange_account_id == str(account_id))

        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.exchange_account))
            .where(and_(*conditions))
            .order_by(Order.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_orders_by_webhook_delivery(
        self, webhook_delivery_id: Union[str, UUID]
    ) -> List[Order]:
        """Get orders created from a specific webhook delivery"""
        return await self.get_multi(
            filters={"webhook_delivery_id": str(webhook_delivery_id)},
            order_by="-created_at",
        )

    async def get_expired_orders(self) -> List[Order]:
        """Get orders that should be expired"""
        result = await self.session.execute(
            select(Order).where(
                and_(
                    Order.time_in_force == TimeInForce.GTD,
                    Order.good_till_date <= func.now(),
                    Order.status.in_(
                        [
                            OrderStatus.OPEN,
                            OrderStatus.PARTIALLY_FILLED,
                            OrderStatus.SUBMITTED,
                        ]
                    ),
                )
            )
        )
        return list(result.scalars().all())

    async def get_orders_by_symbol(
        self,
        symbol: str,
        account_id: Optional[Union[str, UUID]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Order]:
        """Get orders for a specific symbol"""
        filters = {"symbol": symbol.upper()}
        if account_id:
            filters["exchange_account_id"] = str(account_id)

        return await self.get_multi(
            filters=filters, skip=skip, limit=limit, order_by="-created_at"
        )

    async def get_orders_by_timeframe(
        self,
        start_time: datetime,
        end_time: datetime,
        account_id: Optional[Union[str, UUID]] = None,
        status: Optional[OrderStatus] = None,
    ) -> List[Order]:
        """Get orders within a time frame"""
        conditions = [Order.created_at >= start_time, Order.created_at <= end_time]

        if account_id:
            conditions.append(Order.exchange_account_id == str(account_id))
        if status:
            conditions.append(Order.status == status)

        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.exchange_account))
            .where(and_(*conditions))
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def submit_order(
        self, order_id: Union[str, UUID], external_id: Optional[str] = None
    ) -> bool:
        """Mark order as submitted"""
        order = await self.get(order_id)
        if order:
            order.submit(external_id)
            await self.session.flush()
            return True
        return False

    async def add_fill(
        self,
        order_id: Union[str, UUID],
        quantity: Decimal,
        price: Decimal,
        fee: Decimal = Decimal("0"),
        fee_currency: Optional[str] = None,
    ) -> bool:
        """Add a fill to an order"""
        order = await self.get(order_id)
        if order:
            order.add_fill(quantity, price, fee, fee_currency)
            await self.session.flush()
            return True
        return False

    async def cancel_order(
        self, order_id: Union[str, UUID], reason: Optional[str] = None
    ) -> bool:
        """Cancel an order"""
        order = await self.get(order_id)
        if order:
            order.cancel(reason)
            await self.session.flush()
            return True
        return False

    async def cleanup_old_orders(self, cutoff_date: datetime) -> int:
        """Clean up old completed orders"""
        result = await self.session.execute(
            delete(Order).where(
                and_(
                    Order.status.in_([OrderStatus.FILLED, OrderStatus.CANCELLED]),
                    Order.created_at < cutoff_date,
                )
            )
        )
        return result.rowcount

    async def get_order_stats(
        self,
        account_id: Optional[Union[str, UUID]] = None,
        user_id: Optional[Union[str, UUID]] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get order statistics"""
        start_time = datetime.now() - timedelta(days=days)

        base_query = select(Order).where(Order.created_at >= start_time)

        if account_id:
            base_query = base_query.where(Order.exchange_account_id == str(account_id))
        elif user_id:
            base_query = base_query.join(Order.exchange_account).where(
                Order.exchange_account.has(user_id=str(user_id))
            )

        # Basic stats
        stats_result = await self.session.execute(
            base_query.with_only_columns(
                func.count(Order.id).label("total_orders"),
                func.sum(Order.quantity).label("total_quantity"),
                func.sum(Order.filled_quantity).label("total_filled"),
                func.sum(Order.fees_paid).label("total_fees"),
                func.avg(Order.filled_quantity * 100.0 / Order.quantity).label(
                    "avg_fill_rate"
                ),
            )
        )

        stats = stats_result.first()

        # Status distribution
        status_result = await self.session.execute(
            base_query.with_only_columns(
                Order.status, func.count(Order.id).label("count")
            ).group_by(Order.status)
        )

        status_distribution = {row.status.value: row.count for row in status_result}

        # Side distribution
        side_result = await self.session.execute(
            base_query.with_only_columns(
                Order.side,
                func.count(Order.id).label("count"),
                func.sum(Order.quantity).label("total_quantity"),
            ).group_by(Order.side)
        )

        side_distribution = {
            row.side.value: {
                "count": row.count,
                "total_quantity": float(row.total_quantity or 0),
            }
            for row in side_result
        }

        # Type distribution
        type_result = await self.session.execute(
            base_query.with_only_columns(
                Order.type, func.count(Order.id).label("count")
            ).group_by(Order.type)
        )

        type_distribution = {row.type.value: row.count for row in type_result}

        return {
            "total_orders": stats.total_orders or 0,
            "total_quantity": float(stats.total_quantity or 0),
            "total_filled": float(stats.total_filled or 0),
            "total_fees": float(stats.total_fees or 0),
            "average_fill_rate": float(stats.avg_fill_rate or 0),
            "status_distribution": status_distribution,
            "side_distribution": side_distribution,
            "type_distribution": type_distribution,
        }

    async def get_most_active_symbols(
        self,
        limit: int = 10,
        account_id: Optional[Union[str, UUID]] = None,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get most actively traded symbols"""
        start_time = datetime.now() - timedelta(days=days)

        base_query = select(Order).where(Order.created_at >= start_time)

        if account_id:
            base_query = base_query.where(Order.exchange_account_id == str(account_id))

        result = await self.session.execute(
            base_query.with_only_columns(
                Order.symbol,
                func.count(Order.id).label("order_count"),
                func.sum(Order.quantity).label("total_quantity"),
                func.sum(Order.filled_quantity).label("total_filled"),
            )
            .group_by(Order.symbol)
            .order_by(func.count(Order.id).desc())
            .limit(limit)
        )

        return [
            {
                "symbol": row.symbol,
                "order_count": row.order_count,
                "total_quantity": float(row.total_quantity or 0),
                "total_filled": float(row.total_filled or 0),
            }
            for row in result
        ]

    async def search_orders(
        self,
        search_term: str,
        user_id: Optional[Union[str, UUID]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Order]:
        """Search orders by symbol, client order ID, or external ID"""
        conditions = [
            or_(
                Order.symbol.ilike(f"%{search_term.upper()}%"),
                Order.client_order_id.ilike(f"%{search_term}%"),
                Order.external_id.ilike(f"%{search_term}%"),
            )
        ]

        if user_id:
            conditions.append(Order.exchange_account.has(user_id=str(user_id)))

        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.exchange_account))
            .where(and_(*conditions))
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def cleanup_old_orders(
        self, days_old: int = 365, keep_partial_fills: bool = True
    ) -> int:
        """Clean up old completed orders"""
        cutoff_date = datetime.now() - timedelta(days=days_old)

        conditions = [
            Order.created_at < cutoff_date,
            Order.status.in_(
                [
                    OrderStatus.FILLED,
                    OrderStatus.CANCELED,
                    OrderStatus.REJECTED,
                    OrderStatus.EXPIRED,
                    OrderStatus.FAILED,
                ]
            ),
        ]

        if keep_partial_fills:
            conditions.append(Order.status != OrderStatus.PARTIALLY_FILLED)

        result = await self.session.execute(
            select(func.count(Order.id)).where(and_(*conditions))
        )
        count = result.scalar() or 0

        # Perform the deletion
        await self.session.execute(delete(Order).where(and_(*conditions)))

        return count
