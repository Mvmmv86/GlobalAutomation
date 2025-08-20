"""Secure Exchange Service - Integrates exchange adapters with encrypted credentials"""

from typing import Optional, Dict, Any, List
from uuid import UUID
import asyncio
import structlog

from infrastructure.external.exchange_adapters import BaseExchangeAdapter, ExchangeError
from application.services.exchange_credentials_service import ExchangeCredentialsService
from application.services.exchange_adapter_factory import ExchangeAdapterFactory


logger = structlog.get_logger()


class SecureExchangeService:
    """Service that provides secure access to exchange APIs using encrypted credentials"""

    def __init__(self, exchange_credentials_service: ExchangeCredentialsService):
        self.exchange_credentials_service = exchange_credentials_service
        self._adapter_cache: Dict[str, BaseExchangeAdapter] = {}
        self._cache_timeout = 300  # 5 minutes

    async def get_exchange_adapter(
        self, account_id: UUID, user_id: UUID, force_refresh: bool = False
    ) -> BaseExchangeAdapter:
        """
        Get a configured exchange adapter with decrypted credentials

        Args:
            account_id: Exchange account ID
            user_id: User ID for security validation
            force_refresh: Force refresh of cached adapter

        Returns:
            Configured exchange adapter

        Raises:
            ValueError: If account not found or credentials invalid
            ExchangeError: If adapter creation fails
        """
        cache_key = f"{account_id}:{user_id}"

        # Check cache first (unless forced refresh)
        if not force_refresh and cache_key in self._adapter_cache:
            adapter = self._adapter_cache[cache_key]
            try:
                # Quick health check on cached adapter
                if (
                    hasattr(adapter, "session")
                    and adapter.session
                    and not adapter.session.closed
                ):
                    return adapter
            except Exception:
                # Remove from cache if health check fails
                del self._adapter_cache[cache_key]

        try:
            # Get decrypted credentials
            credentials = (
                await self.exchange_credentials_service.get_decrypted_credentials(
                    account_id, user_id
                )
            )

            # Create adapter using factory
            exchange_type = credentials["exchange_type"]
            is_testnet = credentials["environment"] == "testnet"

            # Create adapter with appropriate parameters
            if "passphrase" in credentials:
                # Some exchanges (like KuCoin) require passphrase
                adapter = ExchangeAdapterFactory.create_adapter(
                    exchange_name=exchange_type,
                    api_key=credentials["api_key"],
                    api_secret=credentials["api_secret"],
                    testnet=is_testnet,
                    passphrase=credentials["passphrase"],
                )
            else:
                adapter = ExchangeAdapterFactory.create_adapter(
                    exchange_name=exchange_type,
                    api_key=credentials["api_key"],
                    api_secret=credentials["api_secret"],
                    testnet=is_testnet,
                )

            # Cache the adapter
            self._adapter_cache[cache_key] = adapter

            logger.info(
                "Exchange adapter created",
                account_id=str(account_id),
                exchange_type=exchange_type,
                environment=credentials["environment"],
            )

            return adapter

        except Exception as e:
            logger.error(
                "Failed to create exchange adapter",
                account_id=str(account_id),
                user_id=str(user_id),
                error=str(e),
            )
            raise

    async def test_connection(self, account_id: UUID, user_id: UUID) -> bool:
        """
        Test connection to exchange using account credentials

        Args:
            account_id: Exchange account ID
            user_id: User ID for security validation

        Returns:
            True if connection successful
        """
        try:
            adapter = await self.get_exchange_adapter(account_id, user_id)
            success = await adapter.test_connection()

            if success:
                # Update account health status
                await self.exchange_credentials_service.verify_credentials(
                    account_id, user_id
                )

            logger.info(
                "Connection test completed", account_id=str(account_id), success=success
            )

            return success

        except Exception as e:
            logger.warning(
                "Connection test failed", account_id=str(account_id), error=str(e)
            )
            return False

    async def get_account_info(self, account_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """
        Get exchange account information

        Args:
            account_id: Exchange account ID
            user_id: User ID for security validation

        Returns:
            Account information from exchange
        """
        adapter = await self.get_exchange_adapter(account_id, user_id)
        return await adapter.get_account_info()

    async def get_balances(
        self, account_id: UUID, user_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get account balances from exchange

        Args:
            account_id: Exchange account ID
            user_id: User ID for security validation

        Returns:
            List of balance information
        """
        adapter = await self.get_exchange_adapter(account_id, user_id)
        balances = await adapter.get_balances()

        # Convert Balance objects to dictionaries
        return [
            {
                "asset": balance.asset,
                "free": str(balance.free),
                "locked": str(balance.locked),
                "total": str(balance.total),
            }
            for balance in balances
        ]

    async def get_positions(
        self, account_id: UUID, user_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get open positions from exchange

        Args:
            account_id: Exchange account ID
            user_id: User ID for security validation

        Returns:
            List of position information
        """
        adapter = await self.get_exchange_adapter(account_id, user_id)
        positions = await adapter.get_positions()

        # Convert Position objects to dictionaries
        return [
            {
                "symbol": position.symbol,
                "side": position.side,
                "size": str(position.size),
                "entry_price": str(position.entry_price),
                "mark_price": str(position.mark_price),
                "unrealized_pnl": str(position.unrealized_pnl),
                "percentage": str(position.percentage),
            }
            for position in positions
        ]

    async def create_order(
        self,
        account_id: UUID,
        user_id: UUID,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a new order on the exchange

        Args:
            account_id: Exchange account ID
            user_id: User ID for security validation
            symbol: Trading symbol (e.g., 'BTCUSDT')
            side: Order side ('buy' or 'sell')
            order_type: Order type ('market', 'limit', etc.)
            quantity: Order quantity
            price: Order price (for limit orders)
            **kwargs: Additional order parameters

        Returns:
            Order response information
        """
        adapter = await self.get_exchange_adapter(account_id, user_id)

        # Convert string enums to proper types
        from infrastructure.external.exchange_adapters.base_adapter import (
            OrderSide,
            OrderType,
        )
        from decimal import Decimal

        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        order_type_map = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "stop": OrderType.STOP,
            "stop_limit": OrderType.STOP_LIMIT,
        }
        order_type_enum = order_type_map.get(order_type.lower(), OrderType.MARKET)

        order_response = await adapter.create_order(
            symbol=symbol,
            side=order_side,
            order_type=order_type_enum,
            quantity=Decimal(quantity),
            price=Decimal(price) if price else None,
            **kwargs,
        )

        # Convert OrderResponse to dictionary
        return {
            "order_id": order_response.order_id,
            "symbol": order_response.symbol,
            "side": order_response.side.value,
            "order_type": order_response.order_type.value,
            "quantity": str(order_response.quantity),
            "price": str(order_response.price) if order_response.price else None,
            "status": order_response.status.value,
            "filled_quantity": str(order_response.filled_quantity),
            "average_price": str(order_response.average_price)
            if order_response.average_price
            else None,
            "created_at": order_response.created_at.isoformat()
            if order_response.created_at
            else None,
            "updated_at": order_response.updated_at.isoformat()
            if order_response.updated_at
            else None,
            "fees": {k: str(v) for k, v in order_response.fees.items()}
            if order_response.fees
            else None,
        }

    async def cancel_order(
        self, account_id: UUID, user_id: UUID, symbol: str, order_id: str
    ) -> bool:
        """
        Cancel an order on the exchange

        Args:
            account_id: Exchange account ID
            user_id: User ID for security validation
            symbol: Trading symbol
            order_id: Order ID to cancel

        Returns:
            True if cancellation successful
        """
        adapter = await self.get_exchange_adapter(account_id, user_id)
        return await adapter.cancel_order(symbol, order_id)

    async def get_order_status(
        self, account_id: UUID, user_id: UUID, symbol: str, order_id: str
    ) -> Dict[str, Any]:
        """
        Get order status from exchange

        Args:
            account_id: Exchange account ID
            user_id: User ID for security validation
            symbol: Trading symbol
            order_id: Order ID

        Returns:
            Order status information
        """
        adapter = await self.get_exchange_adapter(account_id, user_id)
        order_response = await adapter.get_order(symbol, order_id)

        # Convert to dictionary (same as create_order)
        return {
            "order_id": order_response.order_id,
            "symbol": order_response.symbol,
            "side": order_response.side.value,
            "order_type": order_response.order_type.value,
            "quantity": str(order_response.quantity),
            "price": str(order_response.price) if order_response.price else None,
            "status": order_response.status.value,
            "filled_quantity": str(order_response.filled_quantity),
            "average_price": str(order_response.average_price)
            if order_response.average_price
            else None,
            "created_at": order_response.created_at.isoformat()
            if order_response.created_at
            else None,
            "updated_at": order_response.updated_at.isoformat()
            if order_response.updated_at
            else None,
            "fees": {k: str(v) for k, v in order_response.fees.items()}
            if order_response.fees
            else None,
        }

    async def get_ticker_price(
        self, account_id: UUID, user_id: UUID, symbol: str
    ) -> str:
        """
        Get current ticker price for symbol

        Args:
            account_id: Exchange account ID
            user_id: User ID for security validation
            symbol: Trading symbol

        Returns:
            Current price as string
        """
        adapter = await self.get_exchange_adapter(account_id, user_id)
        price = await adapter.get_ticker_price(symbol)
        return str(price)

    async def batch_test_connections(
        self, user_id: UUID, account_ids: Optional[List[UUID]] = None
    ) -> Dict[UUID, bool]:
        """
        Test connections for multiple accounts in batch

        Args:
            user_id: User ID
            account_ids: List of account IDs to test (if None, test all user accounts)

        Returns:
            Dictionary mapping account_id to connection success
        """
        if account_ids is None:
            # Get all user accounts
            status = await self.exchange_credentials_service.get_account_status(user_id)
            account_ids = [account["id"] for account in status]

        results = {}

        # Test connections concurrently
        async def test_single(account_id: UUID) -> tuple[UUID, bool]:
            try:
                success = await self.test_connection(account_id, user_id)
                return account_id, success
            except Exception as e:
                logger.warning(f"Batch test failed for account {account_id}: {e}")
                return account_id, False

        # Run tests concurrently (max 5 at a time to avoid rate limits)
        semaphore = asyncio.Semaphore(5)

        async def test_with_semaphore(account_id: UUID):
            async with semaphore:
                return await test_single(account_id)

        tasks = [test_with_semaphore(account_id) for account_id in account_ids]
        test_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in test_results:
            if isinstance(result, tuple):
                account_id, success = result
                results[account_id] = success
            else:
                logger.error(f"Batch test exception: {result}")

        logger.info(
            "Batch connection test completed",
            user_id=str(user_id),
            total_accounts=len(account_ids),
            successful=sum(results.values()),
            failed=len(results) - sum(results.values()),
        )

        return results

    async def cleanup_adapters(self):
        """Clean up cached adapters and close connections"""
        for adapter in self._adapter_cache.values():
            try:
                if hasattr(adapter, "close"):
                    await adapter.close()
            except Exception as e:
                logger.warning(f"Failed to close adapter: {e}")

        self._adapter_cache.clear()
        logger.info("Exchange adapters cleaned up")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cached_adapters": len(self._adapter_cache),
            "cache_keys": list(self._adapter_cache.keys()),
            "cache_timeout": self._cache_timeout,
        }

    async def refresh_all_cached_adapters(self) -> int:
        """Refresh all cached adapters"""
        refreshed = 0
        cache_keys = list(self._adapter_cache.keys())

        for cache_key in cache_keys:
            try:
                account_id_str, user_id_str = cache_key.split(":")
                account_id = UUID(account_id_str)
                user_id = UUID(user_id_str)

                # Force refresh
                await self.get_exchange_adapter(account_id, user_id, force_refresh=True)
                refreshed += 1

            except Exception as e:
                logger.warning(f"Failed to refresh adapter {cache_key}: {e}")
                # Remove problematic cache entry
                if cache_key in self._adapter_cache:
                    del self._adapter_cache[cache_key]

        logger.info(f"Refreshed {refreshed} cached adapters")
        return refreshed
