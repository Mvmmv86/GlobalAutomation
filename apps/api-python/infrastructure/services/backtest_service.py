"""
Backtest Service

Provides backtesting functionality for trading strategies.
Simulates strategy execution on historical data to evaluate performance.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import structlog

from infrastructure.database.models.strategy import (
    ConditionType,
    IndicatorType,
    LogicOperator,
    SignalType,
    Strategy,
    StrategyBacktestResult,
)
from infrastructure.database.repositories.strategy import (
    StrategyBacktestResultRepository,
    StrategyRepository,
)
from infrastructure.indicators import (
    BaseIndicatorCalculator,
    Candle,
    IndicatorResult,
    NadarayaWatsonCalculator,
    TPOCalculator,
)

logger = structlog.get_logger(__name__)


@dataclass
class BacktestTrade:
    """Represents a single trade in backtest"""
    entry_time: datetime
    exit_time: Optional[datetime]
    signal_type: SignalType  # LONG or SHORT
    entry_price: Decimal
    exit_price: Optional[Decimal]
    quantity: Decimal
    pnl: Optional[Decimal]
    pnl_percent: Optional[Decimal]
    exit_reason: Optional[str]  # "take_profit", "stop_loss", "signal"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "signal_type": self.signal_type.value,
            "entry_price": float(self.entry_price),
            "exit_price": float(self.exit_price) if self.exit_price else None,
            "quantity": float(self.quantity),
            "pnl": float(self.pnl) if self.pnl else None,
            "pnl_percent": float(self.pnl_percent) if self.pnl_percent else None,
            "exit_reason": self.exit_reason
        }


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    initial_capital: Decimal = Decimal("10000")
    leverage: int = 10
    margin_percent: Decimal = Decimal("5.00")  # % of capital per trade
    stop_loss_percent: Decimal = Decimal("2.00")
    take_profit_percent: Decimal = Decimal("4.00")
    include_fees: bool = True
    include_slippage: bool = True
    fee_percent: Decimal = Decimal("0.04")  # 0.04% taker fee
    slippage_percent: Decimal = Decimal("0.05")  # 0.05% slippage


@dataclass
class BacktestState:
    """State during backtest execution"""
    capital: Decimal
    position: Optional[SignalType] = None
    position_size: Decimal = Decimal("0")
    entry_price: Decimal = Decimal("0")
    entry_time: Optional[datetime] = None
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)


class BacktestService:
    """
    Backtest Service

    Simulates strategy execution on historical data.

    Features:
    - Fetches historical klines from Binance
    - Calculates indicators for each bar
    - Evaluates entry/exit conditions
    - Tracks trades with P&L
    - Calculates performance metrics
    - Saves results to database
    """

    # Indicator factory mapping
    INDICATOR_CALCULATORS = {
        IndicatorType.NADARAYA_WATSON: NadarayaWatsonCalculator,
        IndicatorType.TPO: TPOCalculator,
    }

    def __init__(self, db_pool):
        self.db = db_pool
        self._strategy_repo = StrategyRepository(db_pool)
        self._backtest_repo = StrategyBacktestResultRepository(db_pool)

    async def run_backtest(
        self,
        strategy_id: str,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        config: Optional[BacktestConfig] = None,
    ) -> StrategyBacktestResult:
        """
        Run a backtest for a strategy

        Args:
            strategy_id: Strategy ID
            symbol: Trading symbol (e.g., "BTCUSDT")
            start_date: Backtest start date
            end_date: Backtest end date
            config: Backtest configuration

        Returns:
            StrategyBacktestResult with performance metrics
        """
        if config is None:
            config = BacktestConfig()

        logger.info(
            f"Starting backtest",
            strategy_id=strategy_id,
            symbol=symbol,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )

        # Mark strategy as backtesting
        await self._strategy_repo.update(strategy_id, is_backtesting=True)

        try:
            # Load strategy with relations
            strategy = await self._strategy_repo.get_with_relations(strategy_id)
            if not strategy:
                raise ValueError(f"Strategy {strategy_id} not found")

            # Fetch historical data
            candles = await self._fetch_historical_data(
                symbol=symbol,
                timeframe=strategy.timeframe,
                start_date=start_date,
                end_date=end_date
            )

            if len(candles) < 100:
                raise ValueError(f"Insufficient data: only {len(candles)} candles")

            # Initialize calculators
            calculators = self._initialize_calculators(strategy)

            # Load conditions
            conditions, condition_operators = self._load_conditions(strategy)

            # Run simulation
            state = BacktestState(capital=config.initial_capital)
            state = await self._run_simulation(
                candles=candles,
                calculators=calculators,
                conditions=conditions,
                condition_operators=condition_operators,
                config=config,
                state=state
            )

            # Close any open position at the end
            if state.position:
                self._close_position(
                    state=state,
                    exit_price=candles[-1].close,
                    exit_time=candles[-1].timestamp,
                    exit_reason="end_of_backtest",
                    config=config
                )

            # Calculate metrics
            metrics = self._calculate_metrics(state, config)

            # Create result record
            result = StrategyBacktestResult(
                strategy_id=strategy_id,
                start_date=start_date,
                end_date=end_date,
                symbol=symbol,
                initial_capital=config.initial_capital,
                leverage=config.leverage,
                margin_percent=config.margin_percent,
                stop_loss_percent=config.stop_loss_percent,
                take_profit_percent=config.take_profit_percent,
                include_fees=config.include_fees,
                include_slippage=config.include_slippage,
                total_trades=metrics["total_trades"],
                winning_trades=metrics["winning_trades"],
                losing_trades=metrics["losing_trades"],
                win_rate=metrics["win_rate"],
                profit_factor=metrics["profit_factor"],
                total_pnl=metrics["total_pnl"],
                total_pnl_percent=metrics["total_pnl_percent"],
                max_drawdown=metrics["max_drawdown"],
                sharpe_ratio=metrics["sharpe_ratio"],
                trades=[t.to_dict() for t in state.trades],
                equity_curve=state.equity_curve
            )

            # Save to database
            saved_result = await self._backtest_repo.create(result)

            logger.info(
                f"Backtest completed",
                strategy_id=strategy_id,
                total_trades=metrics["total_trades"],
                win_rate=float(metrics["win_rate"]) if metrics["win_rate"] else 0,
                total_pnl=float(metrics["total_pnl"]) if metrics["total_pnl"] else 0
            )

            return saved_result

        finally:
            # Mark strategy as not backtesting
            await self._strategy_repo.update(strategy_id, is_backtesting=False)

    async def _fetch_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Candle]:
        """Fetch historical klines from Binance"""
        candles = []

        # Convert timeframe to milliseconds
        tf_ms = self._timeframe_to_ms(timeframe)

        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)

        url = "https://fapi.binance.com/fapi/v1/klines"

        async with aiohttp.ClientSession() as session:
            current_ts = start_ts

            while current_ts < end_ts:
                params = {
                    "symbol": symbol.upper(),
                    "interval": timeframe,
                    "startTime": current_ts,
                    "endTime": end_ts,
                    "limit": 1000
                }

                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        raise ValueError(f"Failed to fetch klines: {resp.status}")

                    klines = await resp.json()

                    if not klines:
                        break

                    for k in klines:
                        candle = Candle(
                            timestamp=datetime.fromtimestamp(k[0] / 1000),
                            open=Decimal(str(k[1])),
                            high=Decimal(str(k[2])),
                            low=Decimal(str(k[3])),
                            close=Decimal(str(k[4])),
                            volume=Decimal(str(k[5]))
                        )
                        candles.append(candle)

                    # Move to next batch
                    current_ts = klines[-1][0] + tf_ms

                # Rate limiting
                await asyncio.sleep(0.1)

        logger.info(f"Fetched {len(candles)} candles for {symbol} {timeframe}")
        return candles

    def _timeframe_to_ms(self, timeframe: str) -> int:
        """Convert timeframe string to milliseconds"""
        multipliers = {
            "m": 60 * 1000,
            "h": 60 * 60 * 1000,
            "d": 24 * 60 * 60 * 1000,
            "w": 7 * 24 * 60 * 60 * 1000,
        }

        unit = timeframe[-1]
        value = int(timeframe[:-1])

        return value * multipliers.get(unit, 60 * 1000)

    def _initialize_calculators(
        self,
        strategy: Strategy
    ) -> Dict[str, BaseIndicatorCalculator]:
        """Initialize indicator calculators from strategy config"""
        calculators = {}

        for indicator in strategy.indicators:
            calc_class = self.INDICATOR_CALCULATORS.get(indicator.indicator_type)
            if calc_class:
                calculators[indicator.indicator_type.value] = calc_class(
                    parameters=indicator.parameters
                )

        return calculators

    def _load_conditions(
        self,
        strategy: Strategy
    ) -> Tuple[Dict[ConditionType, List[Dict]], Dict[ConditionType, LogicOperator]]:
        """Load conditions from strategy"""
        conditions = {}
        operators = {}

        for condition in strategy.conditions:
            conditions[condition.condition_type] = condition.get_conditions_list()
            operators[condition.condition_type] = condition.logic_operator

        return conditions, operators

    async def _run_simulation(
        self,
        candles: List[Candle],
        calculators: Dict[str, BaseIndicatorCalculator],
        conditions: Dict[ConditionType, List[Dict]],
        condition_operators: Dict[ConditionType, LogicOperator],
        config: BacktestConfig,
        state: BacktestState,
    ) -> BacktestState:
        """Run the backtest simulation"""
        min_candles = max(
            (calc.required_candles for calc in calculators.values()),
            default=50
        )

        for i in range(min_candles, len(candles)):
            # Get candle window
            window = candles[:i + 1]
            current_candle = window[-1]

            # Calculate indicators
            indicator_values = {}
            for name, calculator in calculators.items():
                try:
                    result = calculator.calculate(window)
                    for key, value in result.values.items():
                        indicator_values[f"{name}.{key}"] = float(value)
                except Exception:
                    continue

            # Build context
            context = {
                "close": float(current_candle.close),
                "open": float(current_candle.open),
                "high": float(current_candle.high),
                "low": float(current_candle.low),
                **indicator_values
            }

            # Check stop loss / take profit if in position
            if state.position:
                self._check_stop_take_profit(
                    state=state,
                    current_candle=current_candle,
                    config=config
                )

            # Skip signal evaluation if still in position
            if state.position:
                # Record equity
                unrealized_pnl = self._calculate_unrealized_pnl(
                    state, current_candle.close, config
                )
                state.equity_curve.append({
                    "timestamp": current_candle.timestamp.isoformat(),
                    "equity": float(state.capital + unrealized_pnl),
                    "price": float(current_candle.close)
                })
                continue

            # Evaluate entry conditions
            for condition_type in [ConditionType.ENTRY_LONG, ConditionType.ENTRY_SHORT]:
                cond_list = conditions.get(condition_type, [])
                operator = condition_operators.get(condition_type, LogicOperator.AND)

                if cond_list and self._evaluate_conditions(cond_list, operator, context):
                    signal_type = SignalType.LONG if condition_type == ConditionType.ENTRY_LONG else SignalType.SHORT

                    self._open_position(
                        state=state,
                        signal_type=signal_type,
                        entry_price=current_candle.close,
                        entry_time=current_candle.timestamp,
                        config=config
                    )
                    break

            # Record equity
            state.equity_curve.append({
                "timestamp": current_candle.timestamp.isoformat(),
                "equity": float(state.capital),
                "price": float(current_candle.close)
            })

        return state

    def _evaluate_conditions(
        self,
        conditions: List[Dict],
        operator: LogicOperator,
        context: Dict[str, float]
    ) -> bool:
        """Evaluate condition set"""
        results = []

        for cond in conditions:
            left_key = cond.get("left", "")
            right_key = cond.get("right", "")
            op = cond.get("operator", "")

            left_val = self._get_value(left_key, context)
            right_val = self._get_value(right_key, context)

            if left_val is None or right_val is None:
                continue

            result = self._compare(left_val, op, right_val)
            results.append(result)

        if not results:
            return False

        return all(results) if operator == LogicOperator.AND else any(results)

    def _get_value(self, key: str, context: Dict[str, float]) -> Optional[float]:
        """Get value from context or parse as number"""
        if key in context:
            return context[key]

        # Aliases
        aliases = {
            "ndy.lower": "nadaraya_watson.lower",
            "ndy.upper": "nadaraya_watson.upper",
            "tpo.val": "tpo.val",
            "tpo.vah": "tpo.vah",
        }
        if key in aliases and aliases[key] in context:
            return context[aliases[key]]

        try:
            return float(key)
        except ValueError:
            return None

    def _compare(self, left: float, op: str, right: float) -> bool:
        """Compare values"""
        ops = {
            "<": lambda a, b: a < b,
            ">": lambda a, b: a > b,
            "<=": lambda a, b: a <= b,
            ">=": lambda a, b: a >= b,
            "==": lambda a, b: abs(a - b) < 0.0001,
        }
        return ops.get(op, lambda a, b: False)(left, right)

    def _open_position(
        self,
        state: BacktestState,
        signal_type: SignalType,
        entry_price: Decimal,
        entry_time: datetime,
        config: BacktestConfig,
    ) -> None:
        """Open a new position"""
        # Calculate position size
        margin = state.capital * (config.margin_percent / Decimal("100"))
        position_value = margin * config.leverage

        # Apply slippage
        if config.include_slippage:
            slippage = entry_price * (config.slippage_percent / Decimal("100"))
            if signal_type == SignalType.LONG:
                entry_price = entry_price + slippage
            else:
                entry_price = entry_price - slippage

        position_size = position_value / entry_price

        # Apply fees
        if config.include_fees:
            fee = position_value * (config.fee_percent / Decimal("100"))
            state.capital -= fee

        state.position = signal_type
        state.position_size = position_size
        state.entry_price = entry_price
        state.entry_time = entry_time

    def _close_position(
        self,
        state: BacktestState,
        exit_price: Decimal,
        exit_time: datetime,
        exit_reason: str,
        config: BacktestConfig,
    ) -> None:
        """Close current position"""
        if not state.position:
            return

        # Apply slippage
        if config.include_slippage:
            slippage = exit_price * (config.slippage_percent / Decimal("100"))
            if state.position == SignalType.LONG:
                exit_price = exit_price - slippage
            else:
                exit_price = exit_price + slippage

        # Calculate P&L
        if state.position == SignalType.LONG:
            pnl = (exit_price - state.entry_price) * state.position_size
        else:
            pnl = (state.entry_price - exit_price) * state.position_size

        # Apply leverage to P&L
        pnl_percent = (pnl / (state.position_size * state.entry_price)) * Decimal("100") * config.leverage

        # Apply fees
        if config.include_fees:
            position_value = state.position_size * exit_price
            fee = position_value * (config.fee_percent / Decimal("100"))
            pnl -= fee

        # Update capital
        state.capital += pnl

        # Record trade
        trade = BacktestTrade(
            entry_time=state.entry_time,
            exit_time=exit_time,
            signal_type=state.position,
            entry_price=state.entry_price,
            exit_price=exit_price,
            quantity=state.position_size,
            pnl=pnl,
            pnl_percent=pnl_percent,
            exit_reason=exit_reason
        )
        state.trades.append(trade)

        # Reset position
        state.position = None
        state.position_size = Decimal("0")
        state.entry_price = Decimal("0")
        state.entry_time = None

    def _check_stop_take_profit(
        self,
        state: BacktestState,
        current_candle: Candle,
        config: BacktestConfig,
    ) -> None:
        """Check if stop loss or take profit is hit"""
        if not state.position:
            return

        high = current_candle.high
        low = current_candle.low

        sl_distance = state.entry_price * (config.stop_loss_percent / Decimal("100"))
        tp_distance = state.entry_price * (config.take_profit_percent / Decimal("100"))

        if state.position == SignalType.LONG:
            stop_price = state.entry_price - sl_distance
            take_price = state.entry_price + tp_distance

            if low <= stop_price:
                self._close_position(
                    state=state,
                    exit_price=stop_price,
                    exit_time=current_candle.timestamp,
                    exit_reason="stop_loss",
                    config=config
                )
            elif high >= take_price:
                self._close_position(
                    state=state,
                    exit_price=take_price,
                    exit_time=current_candle.timestamp,
                    exit_reason="take_profit",
                    config=config
                )
        else:  # SHORT
            stop_price = state.entry_price + sl_distance
            take_price = state.entry_price - tp_distance

            if high >= stop_price:
                self._close_position(
                    state=state,
                    exit_price=stop_price,
                    exit_time=current_candle.timestamp,
                    exit_reason="stop_loss",
                    config=config
                )
            elif low <= take_price:
                self._close_position(
                    state=state,
                    exit_price=take_price,
                    exit_time=current_candle.timestamp,
                    exit_reason="take_profit",
                    config=config
                )

    def _calculate_unrealized_pnl(
        self,
        state: BacktestState,
        current_price: Decimal,
        config: BacktestConfig,
    ) -> Decimal:
        """Calculate unrealized P&L for open position"""
        if not state.position:
            return Decimal("0")

        if state.position == SignalType.LONG:
            return (current_price - state.entry_price) * state.position_size
        else:
            return (state.entry_price - current_price) * state.position_size

    def _calculate_metrics(
        self,
        state: BacktestState,
        config: BacktestConfig,
    ) -> Dict[str, Any]:
        """Calculate performance metrics"""
        trades = state.trades
        total_trades = len(trades)

        if total_trades == 0:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": None,
                "profit_factor": None,
                "total_pnl": Decimal("0"),
                "total_pnl_percent": Decimal("0"),
                "max_drawdown": Decimal("0"),
                "sharpe_ratio": None,
            }

        winning_trades = sum(1 for t in trades if t.pnl and t.pnl > 0)
        losing_trades = sum(1 for t in trades if t.pnl and t.pnl < 0)

        win_rate = Decimal(str(winning_trades / total_trades * 100))

        # Profit factor
        gross_profit = sum(t.pnl for t in trades if t.pnl and t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl and t.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else Decimal("999")

        # Total P&L
        total_pnl = sum(t.pnl for t in trades if t.pnl)
        total_pnl_percent = (total_pnl / config.initial_capital) * Decimal("100")

        # Max drawdown
        max_drawdown = self._calculate_max_drawdown(state.equity_curve)

        # Sharpe ratio (simplified)
        sharpe = self._calculate_sharpe_ratio(trades)

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl,
            "total_pnl_percent": total_pnl_percent,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe,
        }

    def _calculate_max_drawdown(self, equity_curve: List[Dict]) -> Decimal:
        """Calculate maximum drawdown from equity curve"""
        if not equity_curve:
            return Decimal("0")

        equities = [e["equity"] for e in equity_curve]
        peak = equities[0]
        max_dd = 0

        for equity in equities:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd

        return Decimal(str(max_dd))

    def _calculate_sharpe_ratio(self, trades: List[BacktestTrade]) -> Optional[Decimal]:
        """Calculate simplified Sharpe ratio"""
        if len(trades) < 2:
            return None

        returns = [float(t.pnl_percent) for t in trades if t.pnl_percent]

        if not returns:
            return None

        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return None

        # Annualized (assuming daily trades)
        sharpe = (avg_return / std_dev) * (252 ** 0.5)

        return Decimal(str(round(sharpe, 4)))
