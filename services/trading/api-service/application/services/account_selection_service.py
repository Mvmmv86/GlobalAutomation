"""Account selection service with intelligent routing"""

from typing import List, Optional, Dict, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime

from infrastructure.database.repositories import ExchangeAccountRepository
from infrastructure.database.models.exchange_account import ExchangeAccount
from infrastructure.external.exchange_adapters import BaseExchangeAdapter, ExchangeError
from application.services.exchange_adapter_factory import ExchangeAdapterFactory


class SelectionCriteria(Enum):
    """Account selection criteria"""

    BEST_BALANCE = "best_balance"
    LOWEST_FEES = "lowest_fees"
    BEST_LIQUIDITY = "best_liquidity"
    FASTEST_EXECUTION = "fastest_execution"
    BALANCED = "balanced"


@dataclass
class AccountScore:
    """Account scoring for selection"""

    account: ExchangeAccount
    adapter: BaseExchangeAdapter
    balance_score: float = 0.0
    fee_score: float = 0.0
    liquidity_score: float = 0.0
    speed_score: float = 0.0
    health_score: float = 0.0
    total_score: float = 0.0
    available_balance: Optional[Decimal] = None
    estimated_fee: Optional[Decimal] = None
    connection_latency: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class TradingRequest:
    """Trading request parameters for account selection"""

    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: Decimal
    order_type: str = "market"
    max_fee_bps: Optional[int] = None  # Max fee in basis points
    min_balance_ratio: float = 0.1  # Minimum balance ratio to keep
    exclude_exchanges: Optional[List[str]] = None


class AccountSelectionService:
    """Service for intelligent account/exchange selection"""

    def __init__(self, exchange_account_repository: ExchangeAccountRepository):
        self.exchange_account_repository = exchange_account_repository
        self._adapter_cache: Dict[str, BaseExchangeAdapter] = {}
        self._score_weights = {
            SelectionCriteria.BEST_BALANCE: {
                "balance": 0.6,
                "fee": 0.2,
                "liquidity": 0.1,
                "speed": 0.1,
                "health": 0.0,
            },
            SelectionCriteria.LOWEST_FEES: {
                "balance": 0.2,
                "fee": 0.6,
                "liquidity": 0.1,
                "speed": 0.05,
                "health": 0.05,
            },
            SelectionCriteria.BEST_LIQUIDITY: {
                "balance": 0.1,
                "fee": 0.2,
                "liquidity": 0.6,
                "speed": 0.05,
                "health": 0.05,
            },
            SelectionCriteria.FASTEST_EXECUTION: {
                "balance": 0.1,
                "fee": 0.1,
                "liquidity": 0.2,
                "speed": 0.5,
                "health": 0.1,
            },
            SelectionCriteria.BALANCED: {
                "balance": 0.25,
                "fee": 0.25,
                "liquidity": 0.2,
                "speed": 0.15,
                "health": 0.15,
            },
        }

    async def select_best_account(
        self,
        user_id: str,
        trading_request: TradingRequest,
        criteria: SelectionCriteria = SelectionCriteria.BALANCED,
        max_candidates: int = 5,
    ) -> Optional[AccountScore]:
        """Select the best account for a trading request"""

        # Get active accounts for user
        accounts = await self.exchange_account_repository.get_user_active_accounts(
            user_id
        )

        if not accounts:
            return None

        # Filter accounts based on request criteria
        filtered_accounts = self._filter_accounts(accounts, trading_request)

        if not filtered_accounts:
            return None

        # Score each account
        scored_accounts = await self._score_accounts(
            filtered_accounts, trading_request, criteria
        )

        # Sort by total score and return best
        scored_accounts.sort(key=lambda x: x.total_score, reverse=True)

        # Return best account if it has a valid score
        best_account = scored_accounts[0] if scored_accounts else None

        if best_account and best_account.total_score > 0:
            return best_account

        return None

    async def get_ranked_accounts(
        self,
        user_id: str,
        trading_request: TradingRequest,
        criteria: SelectionCriteria = SelectionCriteria.BALANCED,
        limit: int = 5,
    ) -> List[AccountScore]:
        """Get ranked list of accounts for a trading request"""

        accounts = await self.exchange_account_repository.get_user_active_accounts(
            user_id
        )

        if not accounts:
            return []

        filtered_accounts = self._filter_accounts(accounts, trading_request)
        scored_accounts = await self._score_accounts(
            filtered_accounts, trading_request, criteria
        )

        # Sort by total score
        scored_accounts.sort(key=lambda x: x.total_score, reverse=True)

        return scored_accounts[:limit]

    def _filter_accounts(
        self, accounts: List[ExchangeAccount], trading_request: TradingRequest
    ) -> List[ExchangeAccount]:
        """Filter accounts based on trading request criteria"""
        filtered = []

        for account in accounts:
            # Skip if exchange is explicitly excluded
            if (
                trading_request.exclude_exchanges
                and account.exchange_type.value in trading_request.exclude_exchanges
            ):
                continue

            # Skip if account is not active
            if not account.is_active:
                continue

            # Skip if exchange is not supported
            if not ExchangeAdapterFactory.is_supported(account.exchange_type.value):
                continue

            filtered.append(account)

        return filtered

    async def _score_accounts(
        self,
        accounts: List[ExchangeAccount],
        trading_request: TradingRequest,
        criteria: SelectionCriteria,
    ) -> List[AccountScore]:
        """Score accounts based on various criteria"""

        weights = self._score_weights[criteria]
        scored_accounts = []

        # Process accounts concurrently for better performance
        tasks = [
            self._score_single_account(account, trading_request, weights)
            for account in accounts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, AccountScore):
                scored_accounts.append(result)

        return scored_accounts

    async def _score_single_account(
        self,
        account: ExchangeAccount,
        trading_request: TradingRequest,
        weights: Dict[str, float],
    ) -> AccountScore:
        """Score a single account"""

        score = AccountScore(account=account, adapter=None)

        try:
            # Get or create adapter
            adapter = await self._get_adapter(account)
            score.adapter = adapter

            # Test connection and measure latency
            start_time = datetime.now()
            connection_ok = await adapter.test_connection()
            latency = (datetime.now() - start_time).total_seconds() * 1000
            score.connection_latency = latency

            if not connection_ok:
                score.health_score = 0.0
                score.error_message = "Connection failed"
                return score

            score.health_score = 1.0

            # Get balance information
            balances = await adapter.get_balances()
            quote_asset = self._extract_quote_asset(trading_request.symbol)

            quote_balance = None
            for balance in balances:
                if balance.asset == quote_asset:
                    quote_balance = balance
                    break

            if quote_balance:
                score.available_balance = quote_balance.free

                # Calculate required balance for trade
                estimated_value = await self._estimate_trade_value(
                    adapter, trading_request
                )

                if estimated_value and estimated_value > 0:
                    balance_ratio = float(quote_balance.free / estimated_value)

                    # Score based on available balance vs required
                    if balance_ratio >= 10:  # 10x required balance
                        score.balance_score = 1.0
                    elif balance_ratio >= 5:  # 5x required balance
                        score.balance_score = 0.8
                    elif balance_ratio >= 2:  # 2x required balance
                        score.balance_score = 0.6
                    elif balance_ratio >= 1.2:  # 1.2x required balance
                        score.balance_score = 0.4
                    elif balance_ratio >= 1:  # Just enough balance
                        score.balance_score = 0.2
                    else:  # Insufficient balance
                        score.balance_score = 0.0
                else:
                    score.balance_score = 0.5  # Default if estimation fails
            else:
                score.balance_score = 0.0
                score.available_balance = Decimal("0")

            # Score based on estimated fees (simplified)
            score.estimated_fee = await self._estimate_fees(adapter, trading_request)
            if score.estimated_fee:
                # Lower fees = higher score
                fee_bps = float(score.estimated_fee * 10000)  # Convert to basis points
                if fee_bps <= 5:  # 0.05% or less
                    score.fee_score = 1.0
                elif fee_bps <= 10:  # 0.10% or less
                    score.fee_score = 0.8
                elif fee_bps <= 20:  # 0.20% or less
                    score.fee_score = 0.6
                elif fee_bps <= 50:  # 0.50% or less
                    score.fee_score = 0.4
                else:  # Higher than 0.50%
                    score.fee_score = 0.2
            else:
                score.fee_score = 0.5  # Default

            # Score based on liquidity (simplified - could use order book depth)
            score.liquidity_score = await self._score_liquidity(
                adapter, trading_request
            )

            # Score based on speed (connection latency)
            if latency <= 50:  # Very fast
                score.speed_score = 1.0
            elif latency <= 100:  # Fast
                score.speed_score = 0.8
            elif latency <= 200:  # Medium
                score.speed_score = 0.6
            elif latency <= 500:  # Slow
                score.speed_score = 0.4
            else:  # Very slow
                score.speed_score = 0.2

        except Exception as e:
            score.error_message = str(e)
            score.health_score = 0.0

        # Calculate total weighted score
        score.total_score = (
            weights["balance"] * score.balance_score
            + weights["fee"] * score.fee_score
            + weights["liquidity"] * score.liquidity_score
            + weights["speed"] * score.speed_score
            + weights["health"] * score.health_score
        )

        return score

    async def _get_adapter(self, account: ExchangeAccount) -> BaseExchangeAdapter:
        """Get or create adapter for account"""
        cache_key = f"{account.id}_{account.exchange_type.value}"

        if cache_key not in self._adapter_cache:
            # For now, using dummy credentials since the model has encrypted fields
            # In production, these would be decrypted
            adapter = ExchangeAdapterFactory.create_adapter(
                account.exchange_type.value,
                "dummy_api_key",  # account.api_key_encrypted would be decrypted
                "dummy_api_secret",  # account.api_secret_encrypted would be decrypted
                account.environment.value == "testnet",
            )
            self._adapter_cache[cache_key] = adapter

        return self._adapter_cache[cache_key]

    def _extract_quote_asset(self, symbol: str) -> str:
        """Extract quote asset from trading symbol"""
        # Simple extraction for common patterns
        common_quotes = ["USDT", "USDC", "USD", "BTC", "ETH", "BNB"]

        for quote in common_quotes:
            if symbol.endswith(quote):
                return quote

        # Default fallback
        return "USDT"

    async def _estimate_trade_value(
        self, adapter: BaseExchangeAdapter, trading_request: TradingRequest
    ) -> Optional[Decimal]:
        """Estimate the value required for the trade"""
        try:
            if trading_request.side.lower() == "buy":
                # For buy orders, we need quote asset
                current_price = await adapter.get_ticker_price(trading_request.symbol)
                return trading_request.quantity * current_price
            else:
                # For sell orders, we need base asset quantity
                return trading_request.quantity
        except Exception:
            return None

    async def _estimate_fees(
        self, adapter: BaseExchangeAdapter, trading_request: TradingRequest
    ) -> Optional[Decimal]:
        """Estimate trading fees"""
        # This is a simplified estimation
        # In production, you'd get actual fee rates from the exchange

        if adapter.name == "binance":
            return Decimal("0.001")  # 0.1% default
        elif adapter.name == "bybit":
            return Decimal("0.001")  # 0.1% default
        else:
            return Decimal("0.002")  # 0.2% default for unknown exchanges

    async def _score_liquidity(
        self, adapter: BaseExchangeAdapter, trading_request: TradingRequest
    ) -> float:
        """Score liquidity for the trading pair"""
        # Simplified liquidity scoring
        # In production, you'd analyze order book depth, spreads, volume etc.

        try:
            # Basic check - if we can get price, assume reasonable liquidity
            await adapter.get_ticker_price(trading_request.symbol)
            return 0.8  # Default good liquidity score
        except Exception:
            return 0.2  # Poor liquidity if we can't even get price

    async def validate_account_for_trade(
        self, account: ExchangeAccount, trading_request: TradingRequest
    ) -> Tuple[bool, Optional[str]]:
        """Validate if account can execute the trade"""
        try:
            adapter = await self._get_adapter(account)

            # Test connection
            if not await adapter.test_connection():
                return False, "Connection failed"

            # Check balance
            balances = await adapter.get_balances()
            quote_asset = self._extract_quote_asset(trading_request.symbol)

            required_balance = await self._estimate_trade_value(
                adapter, trading_request
            )
            if required_balance:
                available = Decimal("0")
                for balance in balances:
                    if balance.asset == quote_asset:
                        available = balance.free
                        break

                if available < required_balance:
                    return (
                        False,
                        f"Insufficient balance. Required: {required_balance}, Available: {available}",
                    )

            # Validate order parameters
            await adapter.validate_order_params(
                trading_request.symbol, trading_request.quantity
            )

            return True, None

        except ExchangeError as e:
            return False, f"Exchange error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    async def close_adapters(self):
        """Close all cached adapters"""
        for adapter in self._adapter_cache.values():
            if hasattr(adapter, "close"):
                await adapter.close()

        self._adapter_cache.clear()
