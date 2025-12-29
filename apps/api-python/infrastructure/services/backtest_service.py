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
    StochasticCalculator,
    StochasticRSICalculator,
    SuperTrendCalculator,
    ADXCalculator,
    VWAPCalculator,
    IchimokuCalculator,
    OBVCalculator,
    RSICalculator,
    MACDCalculator,
    BollingerCalculator,
    EMACrossCalculator,
    EMACalculator,
    ATRCalculator,
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

    # Trailing Stop Loss - Fase 2
    use_trailing_stop: bool = False
    trailing_stop_trigger_percent: Decimal = Decimal("1.0")  # Ativar apos +1% lucro
    trailing_stop_distance_percent: Decimal = Decimal("0.8")  # Trail de 0.8%

    # Break-even automatico - Fase 2
    use_break_even: bool = False
    break_even_trigger_percent: Decimal = Decimal("0.5")  # Mover SL para BE apos +0.5%

    # Partial Take Profit - Fase 2
    use_partial_tp: bool = False
    partial_tp_percent: Decimal = Decimal("50")  # Fechar 50% da posicao no TP1
    partial_tp_1_percent: Decimal = Decimal("2.0")  # TP1 em +2%
    partial_tp_2_percent: Decimal = Decimal("4.0")  # TP2 em +4% (restante)


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

    # Trailing stop tracking - Fase 2
    trailing_stop_active: bool = False
    trailing_stop_price: Decimal = Decimal("0")
    highest_price_since_entry: Decimal = Decimal("0")
    lowest_price_since_entry: Decimal = Decimal("0")

    # Break-even tracking - Fase 2
    break_even_active: bool = False
    current_stop_loss: Decimal = Decimal("0")

    # Partial close tracking - Fase 2
    partial_tp_triggered: bool = False
    original_position_size: Decimal = Decimal("0")


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

    # Indicator factory mapping - Complete list for all strategies
    INDICATOR_CALCULATORS = {
        # Indicadores existentes
        IndicatorType.NADARAYA_WATSON: NadarayaWatsonCalculator,
        IndicatorType.TPO: TPOCalculator,
        # Novos indicadores - Fase 1
        IndicatorType.STOCHASTIC: StochasticCalculator,
        IndicatorType.STOCHASTIC_RSI: StochasticRSICalculator,
        IndicatorType.SUPERTREND: SuperTrendCalculator,
        # Novos indicadores - Fase 3
        IndicatorType.ADX: ADXCalculator,
        IndicatorType.VWAP: VWAPCalculator,
        # Indicadores para estrategias institucionais
        IndicatorType.ICHIMOKU: IchimokuCalculator,
        IndicatorType.OBV: OBVCalculator,
        # Indicadores classicos
        IndicatorType.RSI: RSICalculator,
        IndicatorType.MACD: MACDCalculator,
        IndicatorType.BOLLINGER: BollingerCalculator,
        IndicatorType.EMA_CROSS: EMACrossCalculator,
        IndicatorType.EMA: EMACalculator,
        IndicatorType.ATR: ATRCalculator,
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
        result, _ = await self.run_backtest_with_chart_data(
            strategy_id=strategy_id,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            config=config
        )
        return result

    async def run_backtest_with_chart_data(
        self,
        strategy_id: str,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        config: Optional[BacktestConfig] = None,
    ) -> Tuple[StrategyBacktestResult, Dict[str, Any]]:
        """
        Run a backtest for a strategy and return chart data

        Args:
            strategy_id: Strategy ID
            symbol: Trading symbol (e.g., "BTCUSDT")
            start_date: Backtest start date
            end_date: Backtest end date
            config: Backtest configuration

        Returns:
            Tuple of (StrategyBacktestResult, chart_data dict with candles and indicators)
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

        # NOTE: is_backtesting update disabled temporarily due to connection issues
        # This flag is not critical for the backtest to work

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

            # Run simulation and collect indicator data
            state = BacktestState(capital=config.initial_capital)
            state, indicator_series = await self._run_simulation_with_indicators(
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

            # Sample equity curve to reduce size (max 500 points for storage)
            sampled_equity_curve = self._sample_equity_curve(state.equity_curve, max_points=500)
            logger.debug(
                f"Equity curve sampled: {len(state.equity_curve)} -> {len(sampled_equity_curve)} points"
            )

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
                equity_curve=sampled_equity_curve
            )

            # Save to database with retry on connection issues
            try:
                saved_result = await self._backtest_repo.create_result(result)
            except Exception as db_error:
                logger.warning(
                    f"Failed to save backtest result to DB: {db_error}. Returning result without save."
                )
                # Return unsaved result with a generated ID
                import uuid
                result.id = str(uuid.uuid4())
                saved_result = result

            logger.info(
                f"Backtest completed",
                strategy_id=strategy_id,
                total_trades=metrics["total_trades"],
                win_rate=float(metrics["win_rate"]) if metrics["win_rate"] else 0,
                total_pnl=float(metrics["total_pnl"]) if metrics["total_pnl"] else 0
            )

            # Prepare chart data
            chart_data = {
                "candles": [
                    {
                        "time": int(c.timestamp.timestamp()),
                        "open": float(c.open),
                        "high": float(c.high),
                        "low": float(c.low),
                        "close": float(c.close),
                        "volume": float(c.volume) if c.volume else 0
                    }
                    for c in candles
                ],
                "indicators": indicator_series
            }

            return saved_result, chart_data

        finally:
            # NOTE: is_backtesting update disabled temporarily
            pass

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

        logger.info(
            f"Fetching candles for {symbol} {timeframe}",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            start_ts=start_ts,
            end_ts=end_ts
        )

        batch_count = 0
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
                        error_text = await resp.text()
                        logger.error(f"Failed to fetch klines: {resp.status} - {error_text}")
                        raise ValueError(f"Failed to fetch klines: {resp.status}")

                    klines = await resp.json()

                    if not klines:
                        logger.debug(f"No more klines after batch {batch_count}")
                        break

                    batch_count += 1
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

                    if batch_count % 5 == 0:
                        logger.debug(f"Fetched batch {batch_count}, total candles: {len(candles)}")

                # Rate limiting
                await asyncio.sleep(0.1)

        logger.info(
            f"Fetched {len(candles)} candles for {symbol} {timeframe} in {batch_count} batches"
        )
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
            # Get the indicator type - handle both enum and string
            ind_type = indicator.indicator_type
            if isinstance(ind_type, str):
                # Convert string to enum if needed
                try:
                    ind_type = IndicatorType(ind_type)
                except ValueError:
                    logger.warning(f"Unknown indicator type: {ind_type}")
                    continue

            calc_class = self.INDICATOR_CALCULATORS.get(ind_type)
            if calc_class:
                # Get the string value for the key
                key = ind_type.value if hasattr(ind_type, 'value') else str(ind_type)
                calculators[key] = calc_class(
                    parameters=indicator.parameters
                )
                logger.debug(f"Initialized calculator for {key}")
            else:
                logger.warning(f"No calculator found for indicator type: {ind_type}")

        logger.info(f"Initialized {len(calculators)} calculators: {list(calculators.keys())}")
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
        """Run the backtest simulation (without collecting indicator series)"""
        state, _ = await self._run_simulation_with_indicators(
            candles=candles,
            calculators=calculators,
            conditions=conditions,
            condition_operators=condition_operators,
            config=config,
            state=state
        )
        return state

    async def _run_simulation_with_indicators(
        self,
        candles: List[Candle],
        calculators: Dict[str, BaseIndicatorCalculator],
        conditions: Dict[ConditionType, List[Dict]],
        condition_operators: Dict[ConditionType, LogicOperator],
        config: BacktestConfig,
        state: BacktestState,
    ) -> Tuple[BacktestState, Dict[str, List[Dict[str, Any]]]]:
        """Run the backtest simulation and collect indicator data for charts"""
        min_candles = max(
            (calc.required_candles for calc in calculators.values()),
            default=50
        )

        # Initialize indicator series storage
        indicator_series: Dict[str, List[Dict[str, Any]]] = {}

        for i in range(min_candles, len(candles)):
            # Get candle window
            window = candles[:i + 1]
            current_candle = window[-1]
            timestamp = int(current_candle.timestamp.timestamp())

            # Calculate indicators
            indicator_values = {}
            for name, calculator in calculators.items():
                try:
                    result = calculator.calculate(window)
                    if result and result.values:
                        for key, value in result.values.items():
                            full_key = f"{name}.{key}"
                            indicator_values[full_key] = float(value)

                            # Store in series for chart
                            if full_key not in indicator_series:
                                indicator_series[full_key] = []
                            indicator_series[full_key].append({
                                "time": timestamp,
                                "value": float(value)
                            })
                except Exception as e:
                    # Log only on first occurrence to avoid spam
                    if i == min_candles:
                        logger.warning(f"Error calculating {name}: {e}")
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

            # Check exit conditions if still in position (after stop/TP check)
            if state.position:
                # Determine which exit condition to check based on position type
                exit_condition_type = (
                    ConditionType.EXIT_LONG if state.position == SignalType.LONG
                    else ConditionType.EXIT_SHORT
                )

                exit_cond_list = conditions.get(exit_condition_type, [])
                exit_operator = condition_operators.get(exit_condition_type, LogicOperator.AND)

                # Evaluate exit conditions
                if exit_cond_list and self._evaluate_conditions(exit_cond_list, exit_operator, context):
                    self._close_position(
                        state=state,
                        exit_price=current_candle.close,
                        exit_time=current_candle.timestamp,
                        exit_reason="signal_exit",
                        config=config
                    )
                    logger.debug(
                        "Position closed by signal exit",
                        exit_type=exit_condition_type.value,
                        price=float(current_candle.close)
                    )

            # Skip entry signal evaluation if still in position
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

        return state, indicator_series

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

        # Reset trailing stop tracking
        state.trailing_stop_active = False
        state.trailing_stop_price = Decimal("0")
        state.highest_price_since_entry = Decimal("0")
        state.lowest_price_since_entry = Decimal("0")

        # Reset break-even tracking
        state.break_even_active = False
        state.current_stop_loss = Decimal("0")

        # Reset partial TP tracking
        state.partial_tp_triggered = False
        state.original_position_size = Decimal("0")

    def _close_partial_position(
        self,
        state: BacktestState,
        exit_price: Decimal,
        exit_time: datetime,
        partial_size: Decimal,
        exit_reason: str,
        config: BacktestConfig,
    ) -> None:
        """Close a partial position (for partial take profit)"""
        if not state.position or partial_size <= 0:
            return

        # Store original size if first partial close
        if state.original_position_size == 0:
            state.original_position_size = state.position_size

        # Apply slippage
        actual_exit_price = exit_price
        if config.include_slippage:
            slippage = exit_price * (config.slippage_percent / Decimal("100"))
            if state.position == SignalType.LONG:
                actual_exit_price = exit_price - slippage
            else:
                actual_exit_price = exit_price + slippage

        # Calculate P&L for partial close
        if state.position == SignalType.LONG:
            pnl = (actual_exit_price - state.entry_price) * partial_size
        else:
            pnl = (state.entry_price - actual_exit_price) * partial_size

        # Calculate P&L percentage
        pnl_percent = (pnl / (partial_size * state.entry_price)) * Decimal("100") * config.leverage

        # Apply fees
        if config.include_fees:
            position_value = partial_size * actual_exit_price
            fee = position_value * (config.fee_percent / Decimal("100"))
            pnl -= fee

        # Update capital
        state.capital += pnl

        # Record partial trade
        trade = BacktestTrade(
            entry_time=state.entry_time,
            exit_time=exit_time,
            signal_type=state.position,
            entry_price=state.entry_price,
            exit_price=actual_exit_price,
            quantity=partial_size,
            pnl=pnl,
            pnl_percent=pnl_percent,
            exit_reason=exit_reason
        )
        state.trades.append(trade)

        # Reduce position size (don't close entirely)
        state.position_size -= partial_size

    def _check_stop_take_profit(
        self,
        state: BacktestState,
        current_candle: Candle,
        config: BacktestConfig,
    ) -> None:
        """
        Check if stop loss or take profit is hit

        Includes advanced features:
        - Trailing Stop Loss: Move stop as price moves in favor
        - Break-even: Move stop to entry after profit threshold
        - Partial Take Profit: Close portion at TP1, rest at TP2
        """
        if not state.position:
            return

        high = current_candle.high
        low = current_candle.low
        close = current_candle.close

        # Update price extremes since entry
        if state.position == SignalType.LONG:
            if high > state.highest_price_since_entry:
                state.highest_price_since_entry = high
            if low < state.lowest_price_since_entry or state.lowest_price_since_entry == 0:
                state.lowest_price_since_entry = low
        else:
            if low < state.lowest_price_since_entry or state.lowest_price_since_entry == 0:
                state.lowest_price_since_entry = low
            if high > state.highest_price_since_entry:
                state.highest_price_since_entry = high

        # Calculate current profit percentage
        if state.position == SignalType.LONG:
            current_profit_pct = ((close - state.entry_price) / state.entry_price) * Decimal("100")
        else:
            current_profit_pct = ((state.entry_price - close) / state.entry_price) * Decimal("100")

        # === BREAK-EVEN LOGIC ===
        if config.use_break_even and not state.break_even_active:
            if current_profit_pct >= config.break_even_trigger_percent:
                # Move stop to break-even (entry price)
                state.break_even_active = True
                state.current_stop_loss = state.entry_price

        # === TRAILING STOP LOGIC ===
        if config.use_trailing_stop:
            trigger_pct = config.trailing_stop_trigger_percent
            trail_pct = config.trailing_stop_distance_percent

            if current_profit_pct >= trigger_pct:
                state.trailing_stop_active = True

                if state.position == SignalType.LONG:
                    # Trail below highest price
                    new_trailing_stop = state.highest_price_since_entry * (Decimal("1") - trail_pct / Decimal("100"))
                    if new_trailing_stop > state.trailing_stop_price:
                        state.trailing_stop_price = new_trailing_stop
                else:
                    # Trail above lowest price
                    new_trailing_stop = state.lowest_price_since_entry * (Decimal("1") + trail_pct / Decimal("100"))
                    if state.trailing_stop_price == 0 or new_trailing_stop < state.trailing_stop_price:
                        state.trailing_stop_price = new_trailing_stop

        # === DETERMINE ACTIVE STOP PRICE ===
        sl_distance = state.entry_price * (config.stop_loss_percent / Decimal("100"))

        if state.position == SignalType.LONG:
            # Base stop loss
            base_stop = state.entry_price - sl_distance

            # Use highest of: base stop, break-even stop, trailing stop
            if state.break_even_active and state.current_stop_loss > base_stop:
                stop_price = state.current_stop_loss
            elif state.trailing_stop_active and state.trailing_stop_price > base_stop:
                stop_price = state.trailing_stop_price
            else:
                stop_price = base_stop
        else:
            # Base stop loss (SHORT)
            base_stop = state.entry_price + sl_distance

            # Use lowest of: base stop, break-even stop, trailing stop
            if state.break_even_active and state.current_stop_loss < base_stop:
                stop_price = state.current_stop_loss
            elif state.trailing_stop_active and state.trailing_stop_price > 0 and state.trailing_stop_price < base_stop:
                stop_price = state.trailing_stop_price
            else:
                stop_price = base_stop

        # === PARTIAL TAKE PROFIT LOGIC ===
        if config.use_partial_tp and not state.partial_tp_triggered:
            tp1_pct = config.partial_tp_1_percent

            if current_profit_pct >= tp1_pct:
                # Close partial position
                partial_size = state.position_size * (config.partial_tp_percent / Decimal("100"))

                if state.position == SignalType.LONG:
                    tp1_price = state.entry_price * (Decimal("1") + tp1_pct / Decimal("100"))
                else:
                    tp1_price = state.entry_price * (Decimal("1") - tp1_pct / Decimal("100"))

                # Record partial close
                self._close_partial_position(
                    state=state,
                    exit_price=tp1_price,
                    exit_time=current_candle.timestamp,
                    partial_size=partial_size,
                    exit_reason="partial_take_profit_1",
                    config=config
                )
                state.partial_tp_triggered = True

        # === CHECK STOP LOSS ===
        tp_distance = state.entry_price * (config.take_profit_percent / Decimal("100"))

        if state.position == SignalType.LONG:
            take_price = state.entry_price + tp_distance

            if low <= stop_price:
                exit_reason = "trailing_stop" if state.trailing_stop_active else "stop_loss"
                self._close_position(
                    state=state,
                    exit_price=stop_price,
                    exit_time=current_candle.timestamp,
                    exit_reason=exit_reason,
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
            take_price = state.entry_price - tp_distance

            if high >= stop_price:
                exit_reason = "trailing_stop" if state.trailing_stop_active else "stop_loss"
                self._close_position(
                    state=state,
                    exit_price=stop_price,
                    exit_time=current_candle.timestamp,
                    exit_reason=exit_reason,
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
        """
        Calculate performance metrics

        Includes advanced metrics added in Fase 2:
        - Payoff Ratio: Avg Win / Avg Loss
        - Expectancy: Expected profit per trade
        - Sortino Ratio: Risk-adjusted return (downside only)
        - Consecutive Wins/Losses: Max streaks
        - Average Win/Loss: Average profit/loss per trade
        """
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
                # Metricas adicionais - Fase 2
                "sortino_ratio": None,
                "payoff_ratio": None,
                "expectancy": None,
                "avg_win": None,
                "avg_loss": None,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
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

        # === METRICAS ADICIONAIS - FASE 2 ===

        # Payoff Ratio (Avg Win / Avg Loss)
        winning_pnls = [float(t.pnl) for t in trades if t.pnl and t.pnl > 0]
        losing_pnls = [abs(float(t.pnl)) for t in trades if t.pnl and t.pnl < 0]

        avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
        avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else Decimal("999")

        # Expectancy: (Win Rate x Avg Win) - (Loss Rate x Avg Loss)
        win_rate_decimal = winning_trades / total_trades if total_trades > 0 else 0
        loss_rate_decimal = losing_trades / total_trades if total_trades > 0 else 0
        expectancy = (win_rate_decimal * avg_win) - (loss_rate_decimal * avg_loss)

        # Sortino Ratio (uses only negative returns for volatility)
        sortino = self._calculate_sortino_ratio(trades)

        # Consecutive Wins/Losses
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0

        for t in trades:
            if t.pnl and t.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            elif t.pnl and t.pnl < 0:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
            else:
                current_wins = 0
                current_losses = 0

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
            # Metricas adicionais - Fase 2
            "sortino_ratio": sortino,
            "payoff_ratio": Decimal(str(round(payoff_ratio, 4))) if isinstance(payoff_ratio, float) else payoff_ratio,
            "expectancy": Decimal(str(round(expectancy, 2))),
            "avg_win": Decimal(str(round(avg_win, 2))) if avg_win else None,
            "avg_loss": Decimal(str(round(avg_loss, 2))) if avg_loss else None,
            "max_consecutive_wins": max_consecutive_wins,
            "max_consecutive_losses": max_consecutive_losses,
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

    def _calculate_sortino_ratio(self, trades: List[BacktestTrade]) -> Optional[Decimal]:
        """
        Calculate Sortino Ratio

        Similar to Sharpe Ratio but only uses downside deviation (negative returns)
        for the volatility calculation. This better measures risk-adjusted returns
        when we care more about downside risk than overall volatility.

        Formula:
        Sortino = (Average Return - Risk Free Rate) / Downside Deviation

        We assume Risk Free Rate = 0 for simplicity.
        """
        if len(trades) < 2:
            return None

        returns = [float(t.pnl_percent) for t in trades if t.pnl_percent]

        if not returns:
            return None

        avg_return = sum(returns) / len(returns)

        # Calculate downside deviation (only negative returns)
        negative_returns = [r for r in returns if r < 0]

        if len(negative_returns) < 2:
            # Not enough negative returns to calculate downside deviation
            return None

        # Downside variance: average of squared negative returns
        downside_variance = sum(r ** 2 for r in negative_returns) / len(negative_returns)
        downside_dev = downside_variance ** 0.5

        if downside_dev == 0:
            return None

        # Annualized (assuming daily trades)
        sortino = (avg_return / downside_dev) * (252 ** 0.5)

        return Decimal(str(round(sortino, 4)))

    def _sample_equity_curve(
        self,
        equity_curve: List[Dict[str, Any]],
        max_points: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Sample equity curve to reduce data size for storage.

        Keeps first and last points, and samples evenly in between.
        This preserves the overall shape while reducing storage requirements.
        """
        if len(equity_curve) <= max_points:
            return equity_curve

        # Always include first and last points
        result = [equity_curve[0]]

        # Calculate step size for sampling
        step = (len(equity_curve) - 2) / (max_points - 2)

        # Sample intermediate points
        for i in range(1, max_points - 1):
            idx = int(i * step)
            if idx < len(equity_curve) - 1:
                result.append(equity_curve[idx])

        # Add last point
        result.append(equity_curve[-1])

        return result
