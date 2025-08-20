"""Exchange service with business logic"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal

from infrastructure.database.repositories import (
    ExchangeAccountRepository,
    OrderRepository,
    PositionRepository,
    UserRepository,
)
from infrastructure.database.models.exchange_account import ExchangeAccount
from infrastructure.database.models.order import Order, OrderStatus
from infrastructure.database.models.position import Position, PositionStatus


class ExchangeService:
    """Business logic for exchange and trading operations"""

    def __init__(
        self,
        exchange_account_repository: ExchangeAccountRepository,
        order_repository: OrderRepository,
        position_repository: PositionRepository,
        user_repository: UserRepository,
    ):
        self.exchange_account_repository = exchange_account_repository
        self.order_repository = order_repository
        self.position_repository = position_repository
        self.user_repository = user_repository

    async def get_user_accounts(self, user_id: UUID) -> List[ExchangeAccount]:
        """Get all exchange accounts for a user"""
        return await self.exchange_account_repository.get_user_accounts(user_id)

    async def get_active_accounts(self, user_id: UUID) -> List[ExchangeAccount]:
        """Get active exchange accounts for a user"""
        return await self.exchange_account_repository.get_active_accounts(user_id)

    async def create_exchange_account(
        self, user_id: UUID, account_data: Dict[str, Any]
    ) -> ExchangeAccount:
        """Create a new exchange account"""
        # Verify user exists
        user = await self.user_repository.get(user_id)
        if not user:
            raise ValueError("User not found")

        account_data["user_id"] = str(user_id)
        return await self.exchange_account_repository.create(account_data)

    async def update_account_balance(
        self, account_id: UUID, balance_data: Dict[str, Decimal]
    ) -> bool:
        """Update account balance"""
        return await self.exchange_account_repository.update_balance(
            account_id, balance_data
        )

    async def set_default_account(self, user_id: UUID, account_id: UUID) -> bool:
        """Set default account for user"""
        # Verify account belongs to user
        account = await self.exchange_account_repository.get(account_id)
        if not account or account.user_id != str(user_id):
            return False

        return await self.exchange_account_repository.set_default_account(
            user_id, account_id
        )

    async def get_default_account(self, user_id: UUID) -> Optional[ExchangeAccount]:
        """Get user's default account"""
        return await self.exchange_account_repository.get_default_account(user_id)

    async def create_order(self, account_id: UUID, order_data: Dict[str, Any]) -> Order:
        """Create a new order"""
        # Verify account exists and is active
        account = await self.exchange_account_repository.get(account_id)
        if not account or not account.is_active:
            raise ValueError("Account not found or inactive")

        order_data["exchange_account_id"] = str(account_id)
        return await self.order_repository.create(order_data)

    async def get_account_orders(
        self,
        account_id: UUID,
        status: Optional[OrderStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Order]:
        """Get orders for an account"""
        return await self.order_repository.get_account_orders(
            account_id, skip=skip, limit=limit, status=status
        )

    async def get_open_orders(
        self, account_id: Optional[UUID] = None, symbol: Optional[str] = None
    ) -> List[Order]:
        """Get open orders"""
        return await self.order_repository.get_open_orders(account_id, symbol)

    async def cancel_order(self, order_id: UUID, reason: Optional[str] = None) -> bool:
        """Cancel an order"""
        return await self.order_repository.cancel_order(order_id, reason)

    async def get_account_positions(
        self,
        account_id: UUID,
        status: Optional[PositionStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Position]:
        """Get positions for an account"""
        return await self.position_repository.get_account_positions(
            account_id, status=status, skip=skip, limit=limit
        )

    async def get_open_positions(
        self, account_id: Optional[UUID] = None, symbol: Optional[str] = None
    ) -> List[Position]:
        """Get open positions"""
        return await self.position_repository.get_open_positions(account_id, symbol)

    async def get_position_by_symbol(
        self, account_id: UUID, symbol: str
    ) -> Optional[Position]:
        """Get position for a specific symbol"""
        return await self.position_repository.get_position_by_symbol(account_id, symbol)

    async def update_position_pnl(
        self, position_id: UUID, unrealized: Decimal, realized: Optional[Decimal] = None
    ) -> bool:
        """Update position PnL"""
        return await self.position_repository.update_position_pnl(
            position_id, unrealized, realized
        )

    async def close_position(
        self, position_id: UUID, final_pnl: Optional[Decimal] = None
    ) -> bool:
        """Close a position"""
        return await self.position_repository.close_position(position_id, final_pnl)

    async def get_account_performance(
        self, account_id: UUID, days: int = 30
    ) -> Dict[str, Any]:
        """Get account performance metrics"""
        # Get order stats
        order_stats = await self.order_repository.get_order_stats(
            account_id=account_id, days=days
        )

        # Get position stats
        position_stats = await self.position_repository.get_position_stats(
            account_id=account_id, days=days
        )

        # Get account info
        account = await self.exchange_account_repository.get(account_id)

        return {
            "account": {
                "id": str(account.id),
                "name": account.name,
                "exchange": account.exchange,
                "balance": float(account.balance) if account.balance else 0.0,
            },
            "orders": order_stats,
            "positions": position_stats,
            "period_days": days,
        }

    async def get_user_trading_stats(
        self, user_id: UUID, days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive trading statistics for user"""
        # Get order stats across all accounts
        order_stats = await self.order_repository.get_order_stats(
            user_id=user_id, days=days
        )

        # Get position stats across all accounts
        position_stats = await self.position_repository.get_position_stats(
            user_id=user_id, days=days
        )

        # Get account summary
        accounts = await self.exchange_account_repository.get_active_accounts(user_id)

        return {
            "user_id": str(user_id),
            "total_accounts": len(accounts),
            "orders": order_stats,
            "positions": position_stats,
            "period_days": days,
        }

    async def get_portfolio_summary(
        self, user_id: UUID, account_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get portfolio summary for user or specific account"""
        return await self.position_repository.get_portfolio_summary(
            user_id=user_id if not account_id else None, account_id=account_id
        )

    async def get_positions_at_risk(
        self, account_id: Optional[UUID] = None, risk_threshold: float = 80.0
    ) -> List[Position]:
        """Get positions at risk of liquidation"""
        return await self.position_repository.get_positions_at_risk(
            risk_threshold=risk_threshold, account_id=account_id
        )

    async def get_most_active_symbols(
        self, account_id: Optional[UUID] = None, limit: int = 10, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get most actively traded symbols"""
        return await self.order_repository.get_most_active_symbols(
            limit=limit, account_id=account_id, days=days
        )

    async def health_check_account(self, account_id: UUID) -> Dict[str, Any]:
        """Perform health check on exchange account"""
        account = await self.exchange_account_repository.get(account_id)

        if not account:
            return {"healthy": False, "error": "Account not found"}

        # Check account status
        health_status = {
            "healthy": account.is_active and account.health_status == "healthy",
            "account_id": str(account.id),
            "exchange": account.exchange,
            "is_active": account.is_active,
            "health_status": account.health_status,
            "last_health_check": account.last_health_check.isoformat()
            if account.last_health_check
            else None,
        }

        if account.last_error_message:
            health_status["last_error"] = account.last_error_message

        return health_status
