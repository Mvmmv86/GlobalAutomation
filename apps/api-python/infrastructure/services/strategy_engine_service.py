"""
Strategy Engine Service

Core engine for automated trading strategies.
Monitors market data and evaluates trading conditions
to generate signals that are forwarded to bot_broadcast_service.

IMPORTANT: This service REUSES the indicator calculation methods from
IndicatorAlertMonitor to avoid code duplication. All indicator calculations
are done via the shared IndicatorAlertMonitor instance.
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

import structlog

from infrastructure.database.models.strategy import (
    ConditionType,
    IndicatorType,
    LogicOperator,
    SignalStatus,
    SignalType,
    Strategy,
)
from infrastructure.database.repositories.strategy_sql import (
    StrategyRepositorySQL,
    StrategySignalRepositorySQL,
)
from infrastructure.services.bot_broadcast_service import BotBroadcastService
from infrastructure.services.indicator_alert_monitor import IndicatorAlertMonitor

# Try to import numpy
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

# Lazy import for modular indicators
MODULAR_INDICATORS_AVAILABLE = False
StochasticCalculator = None
StochasticRSICalculator = None
SuperTrendCalculator = None
ADXCalculator = None
VWAPCalculator = None
IchimokuCalculator = None
OBVCalculator = None
Candle = None

try:
    from infrastructure.indicators import (
        StochasticCalculator,
        StochasticRSICalculator,
        SuperTrendCalculator,
        ADXCalculator,
        VWAPCalculator,
        IchimokuCalculator,
        OBVCalculator,
        Candle,
    )
    MODULAR_INDICATORS_AVAILABLE = True
except ImportError as e:
    pass

logger = structlog.get_logger(__name__)


@dataclass
class StrategyState:
    """Runtime state for an active strategy"""
    strategy_id: str
    symbols: List[str]
    timeframe: str
    bot_id: Optional[str]

    # Indicator types configured for this strategy
    indicator_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Candle buffers per symbol (last N candles for indicator calculation)
    candle_buffers: Dict[str, List[Dict]] = field(default_factory=lambda: defaultdict(list))

    # Latest indicator values per symbol
    latest_indicators: Dict[str, Dict[str, Any]] = field(default_factory=lambda: defaultdict(dict))

    # Last signal time per symbol (to prevent rapid re-signaling)
    last_signal_time: Dict[str, datetime] = field(default_factory=dict)

    # Conditions (loaded from strategy)
    conditions: Dict[ConditionType, List[Dict]] = field(default_factory=dict)
    condition_operators: Dict[ConditionType, LogicOperator] = field(default_factory=dict)

    # Buffer settings
    max_candles: int = 500
    min_candles_for_signal: int = 50
    signal_cooldown_minutes: int = 5


class StrategyEngineService:
    """
    Strategy Engine Service

    Responsibilities:
    - Load and monitor active strategies
    - Fetch market data periodically (polling)
    - Calculate indicators using IndicatorAlertMonitor methods (NO DUPLICATION)
    - Evaluate entry/exit conditions
    - Generate and forward signals to bot_broadcast_service

    Usage:
        engine = StrategyEngineService(db_pool)
        await engine.start()

        # Engine runs in background, monitoring active strategies
        # Call reload to pick up new/modified strategies
        await engine.reload_strategies()

        await engine.stop()
    """

    # Supported indicator types
    # - Calculados via IndicatorAlertMonitor: nadaraya_watson, rsi, macd, bollinger, ema_cross, tpo
    # - Calculados via modular indicators: stochastic, stochastic_rsi, supertrend, adx, vwap, ichimoku, obv
    SUPPORTED_INDICATORS = [
        # Via IndicatorAlertMonitor
        'nadaraya_watson', 'rsi', 'macd', 'bollinger', 'ema_cross', 'tpo',
        # Via Modular Indicators
        'stochastic', 'stochastic_rsi', 'supertrend', 'adx', 'vwap', 'ichimoku', 'obv'
    ]

    def __init__(self, db_pool):
        self.db = db_pool
        self._running = False

        # Active strategy states
        self._strategies: Dict[str, StrategyState] = {}

        # Broadcast service for sending signals
        self._broadcast_service: Optional[BotBroadcastService] = None

        # Repositories
        self._strategy_repo: Optional[StrategyRepositorySQL] = None
        self._signal_repo: Optional[StrategySignalRepositorySQL] = None

        # Indicator calculator - REUSES IndicatorAlertMonitor methods
        self._indicator_monitor: Optional[IndicatorAlertMonitor] = None

        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None

        logger.info("StrategyEngineService initialized")

    async def start(self) -> None:
        """Start the strategy engine"""
        if self._running:
            logger.warning("Strategy engine already running")
            return

        if not NUMPY_AVAILABLE:
            logger.warning("Cannot start Strategy Engine - NumPy is not installed")
            return

        logger.info("Starting Strategy Engine Service...")

        self._running = True

        # Initialize components
        self._broadcast_service = BotBroadcastService(self.db)
        self._strategy_repo = StrategyRepositorySQL(self.db)
        self._signal_repo = StrategySignalRepositorySQL(self.db)

        # Initialize IndicatorAlertMonitor for indicator calculations
        # We use this instance ONLY for its calculation methods, not for its monitoring loop
        self._indicator_monitor = IndicatorAlertMonitor(self.db)

        # Load active strategies
        await self.reload_strategies()

        # Start monitoring task (polls candles periodically)
        self._monitor_task = asyncio.create_task(self._monitoring_loop())

        logger.info("Strategy Engine Service started")

    async def stop(self) -> None:
        """Stop the strategy engine"""
        logger.info("Stopping Strategy Engine Service...")

        self._running = False

        # Cancel monitor task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Clear state
        self._strategies.clear()

        logger.info("Strategy Engine Service stopped")

    async def reload_strategies(self) -> None:
        """Load or reload active strategies from database"""
        logger.info("Reloading active strategies...")

        # Get active strategies from database
        active_strategies = await self._strategy_repo.get_active_strategies()

        # Track which strategies to add/remove
        current_ids = set(self._strategies.keys())
        new_ids = {str(s.id) for s in active_strategies}

        # Remove deactivated strategies
        for strategy_id in current_ids - new_ids:
            await self._deactivate_strategy(strategy_id)

        # Add/update active strategies
        for strategy in active_strategies:
            strategy_id = str(strategy["id"])

            if strategy_id not in current_ids:
                await self._activate_strategy(strategy)
            else:
                # Update existing strategy
                await self._update_strategy(strategy)

        logger.info(
            f"Strategy reload complete",
            active_count=len(self._strategies)
        )

    async def _activate_strategy(self, strategy: Strategy) -> None:
        """Activate a strategy and start monitoring"""
        strategy_id = str(strategy["id"])

        logger.info(f"Activating strategy: {strategy["name"]} ({strategy_id})")

        # Load strategy with relations
        full_strategy = await self._strategy_repo.get_with_relations(strategy["id"])
        if not full_strategy:
            logger.error(f"Could not load strategy relations: {strategy_id}")
            return

        # Create state object
        state = StrategyState(
            strategy_id=strategy_id,
            symbols=(full_strategy.get("symbols") if isinstance(full_strategy.get("symbols"), list) else __import__("json").loads(full_strategy.get("symbols") or "[]")),
            timeframe=full_strategy["timeframe"],
            bot_id=str(full_strategy.get("bot_id")) if full_strategy.get("bot_id") else None
        )

        # Store indicator configs
        for indicator in full_strategy.get("indicators", []):
            ind_type = indicator["indicator_type"]
            if ind_type in self.SUPPORTED_INDICATORS:
                params = indicator.get("parameters", {})
                # Handle case where parameters is a JSON string (from asyncpg)
                if isinstance(params, str):
                    import json as json_module
                    try:
                        params = json_module.loads(params)
                    except json_module.JSONDecodeError:
                        params = {}
                state.indicator_configs[ind_type] = params or {}
                logger.info(
                    f"Configured indicator: {ind_type}",
                    strategy_id=strategy_id
                )

        # Load conditions
        for condition in full_strategy.get("conditions", []):
            cond_type = condition["condition_type"]
            cond_list = condition.get("conditions", [])
            # Handle case where conditions is a JSON string (from asyncpg)
            if isinstance(cond_list, str):
                import json as json_module
                try:
                    cond_list = json_module.loads(cond_list)
                except json_module.JSONDecodeError:
                    cond_list = []
            state.conditions[cond_type] = cond_list
            state.condition_operators[cond_type] = condition.get("logic_operator", "AND")

        # Store state
        self._strategies[strategy_id] = state

        # Load historical candles for each symbol
        for symbol in state.symbols:
            await self._load_historical_candles(state, symbol)

        logger.info(
            f"Strategy activated: {strategy["name"]}",
            symbols=state.symbols,
            timeframe=state.timeframe
        )

    async def _deactivate_strategy(self, strategy_id: str) -> None:
        """Deactivate a strategy and stop monitoring"""
        logger.info(f"Deactivating strategy: {strategy_id}")
        self._strategies.pop(strategy_id, None)

    async def _update_strategy(self, strategy: Strategy) -> None:
        """Update an existing strategy (reload config)"""
        await self._deactivate_strategy(str(strategy["id"]))
        await self._activate_strategy(strategy)

    async def _load_historical_candles(
        self,
        state: StrategyState,
        symbol: str
    ) -> None:
        """Load historical candles for indicator warmup"""
        try:
            import aiohttp

            url = "https://fapi.binance.com/fapi/v1/klines"
            params = {
                "symbol": symbol.upper(),
                "interval": state.timeframe,
                "limit": state.max_candles
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        klines = await resp.json()
                    else:
                        logger.error(f"Failed to fetch klines: {resp.status}")
                        return

            # Convert to dict format (compatible with IndicatorAlertMonitor)
            candles = []
            for k in klines:
                candle = {
                    'time': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                }
                candles.append(candle)

            state.candle_buffers[symbol] = candles

            # Calculate initial indicators
            await self._calculate_indicators(state, symbol)

            logger.info(
                f"Loaded {len(candles)} historical candles",
                symbol=symbol,
                strategy_id=state.strategy_id
            )

        except Exception as e:
            logger.error(f"Error loading historical candles: {e}", symbol=symbol)

    async def _calculate_indicators(
        self,
        state: StrategyState,
        symbol: str
    ) -> None:
        """
        Calculate all indicators for a symbol.

        USES IndicatorAlertMonitor methods directly - NO CODE DUPLICATION!
        The IndicatorAlertMonitor has all the indicator calculation logic.
        """
        candles = state.candle_buffers.get(symbol, [])

        if len(candles) < state.min_candles_for_signal:
            return

        if not NUMPY_AVAILABLE or not self._indicator_monitor:
            return

        # Extract arrays for calculations (same format as IndicatorAlertMonitor expects)
        closes = np.array([c['close'] for c in candles])
        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        times = [c['time'] for c in candles]

        for ind_type, params in state.indicator_configs.items():
            try:
                result = None

                # REUSE IndicatorAlertMonitor calculation methods!
                # These methods return signal dicts with 'type', 'price', 'indicator_value', etc.
                if ind_type == 'nadaraya_watson':
                    signal = self._indicator_monitor._calc_nadaraya_watson_signal(closes, times, params)
                    if signal:
                        result = {
                            'value': signal.get('indicator_value'),
                            'upper': signal.get('band_value') if signal.get('type') == 'sell' else None,
                            'lower': signal.get('band_value') if signal.get('type') == 'buy' else None,
                            'signal': signal.get('type')
                        }
                    else:
                        # Calculate values even without signal for condition evaluation
                        result = self._get_nadaraya_watson_values(closes, params)

                elif ind_type == 'rsi':
                    signal = self._indicator_monitor._calc_rsi_signal(closes, times, params)
                    if signal:
                        result = {
                            'value': signal.get('indicator_value'),
                            'signal': signal.get('type')
                        }
                    else:
                        result = self._get_rsi_values(closes, params)

                elif ind_type == 'macd':
                    signal = self._indicator_monitor._calc_macd_signal(closes, times, params)
                    if signal:
                        result = {
                            'macd': signal.get('indicator_value'),
                            'signal': signal.get('type')
                        }
                    else:
                        result = self._get_macd_values(closes, params)

                elif ind_type == 'bollinger':
                    signal = self._indicator_monitor._calc_bollinger_signal(closes, times, params)
                    if signal:
                        result = {
                            'middle': signal.get('indicator_value'),
                            'upper': signal.get('band_value') if signal.get('type') == 'sell' else None,
                            'lower': signal.get('band_value') if signal.get('type') == 'buy' else None,
                            'signal': signal.get('type')
                        }
                    else:
                        result = self._get_bollinger_values(closes, params)

                elif ind_type == 'ema_cross':
                    signal = self._indicator_monitor._calc_ema_cross_signal(closes, times, params)
                    if signal:
                        result = {
                            'value': signal.get('indicator_value'),
                            'signal': signal.get('type')
                        }
                    else:
                        result = self._get_ema_cross_values(closes, params)

                # ========== MODULAR INDICATORS ==========
                elif ind_type == 'stochastic' and MODULAR_INDICATORS_AVAILABLE:
                    try:
                        candle_list = [
                            Candle(
                                timestamp=candles[i]['time'] if isinstance(candles[i]['time'], datetime) else datetime.fromtimestamp(candles[i]['time'] / 1000),
                                open=candles[i].get('open', candles[i]['close']),
                                high=candles[i]['high'],
                                low=candles[i]['low'],
                                close=candles[i]['close'],
                                volume=candles[i].get('volume', 0)
                            )
                            for i in range(len(candles))
                        ]
                        calc = StochasticCalculator(params)
                        ind_result = calc.calculate(candle_list)
                        result = {
                            'k': float(ind_result.values.get('k', 0)),
                            'd': float(ind_result.values.get('d', 0)),
                            'signal': 'buy' if int(ind_result.values.get('signal', 0)) == 1 else ('sell' if int(ind_result.values.get('signal', 0)) == -1 else None)
                        }
                    except Exception as calc_err:
                        logger.debug(f"Stochastic calc error: {calc_err}")

                elif ind_type == 'stochastic_rsi' and MODULAR_INDICATORS_AVAILABLE:
                    try:
                        candle_list = [
                            Candle(
                                timestamp=candles[i]['time'] if isinstance(candles[i]['time'], datetime) else datetime.fromtimestamp(candles[i]['time'] / 1000),
                                open=candles[i].get('open', candles[i]['close']),
                                high=candles[i]['high'],
                                low=candles[i]['low'],
                                close=candles[i]['close'],
                                volume=candles[i].get('volume', 0)
                            )
                            for i in range(len(candles))
                        ]
                        calc = StochasticRSICalculator(params)
                        ind_result = calc.calculate(candle_list)
                        result = {
                            'k': float(ind_result.values.get('k', 0)),
                            'd': float(ind_result.values.get('d', 0)),
                            'rsi': float(ind_result.values.get('rsi', 0)),
                            'signal': 'buy' if int(ind_result.values.get('signal', 0)) == 1 else ('sell' if int(ind_result.values.get('signal', 0)) == -1 else None)
                        }
                    except Exception as calc_err:
                        logger.debug(f"StochasticRSI calc error: {calc_err}")

                elif ind_type == 'supertrend' and MODULAR_INDICATORS_AVAILABLE:
                    try:
                        candle_list = [
                            Candle(
                                timestamp=candles[i]['time'] if isinstance(candles[i]['time'], datetime) else datetime.fromtimestamp(candles[i]['time'] / 1000),
                                open=candles[i].get('open', candles[i]['close']),
                                high=candles[i]['high'],
                                low=candles[i]['low'],
                                close=candles[i]['close'],
                                volume=candles[i].get('volume', 0)
                            )
                            for i in range(len(candles))
                        ]
                        calc = SuperTrendCalculator(params)
                        ind_result = calc.calculate(candle_list)
                        trend_val = int(ind_result.values.get('trend', 0))
                        result = {
                            'value': float(ind_result.values.get('value', 0)),
                            'trend': trend_val,
                            'upper': float(ind_result.values.get('upper', 0)),
                            'lower': float(ind_result.values.get('lower', 0)),
                            'signal': 'buy' if trend_val == 1 else ('sell' if trend_val == -1 else None)
                        }
                    except Exception as calc_err:
                        logger.debug(f"SuperTrend calc error: {calc_err}")

                elif ind_type == 'adx' and MODULAR_INDICATORS_AVAILABLE:
                    try:
                        candle_list = [
                            Candle(
                                timestamp=candles[i]['time'] if isinstance(candles[i]['time'], datetime) else datetime.fromtimestamp(candles[i]['time'] / 1000),
                                open=candles[i].get('open', candles[i]['close']),
                                high=candles[i]['high'],
                                low=candles[i]['low'],
                                close=candles[i]['close'],
                                volume=candles[i].get('volume', 0)
                            )
                            for i in range(len(candles))
                        ]
                        calc = ADXCalculator(params)
                        ind_result = calc.calculate(candle_list)
                        result = {
                            'adx': float(ind_result.values.get('adx', 0)),
                            'plus_di': float(ind_result.values.get('plus_di', 0)),
                            'minus_di': float(ind_result.values.get('minus_di', 0)),
                            'trend_strength': int(ind_result.values.get('trend_strength', 0)),
                            'signal': 'buy' if int(ind_result.values.get('signal', 0)) == 1 else ('sell' if int(ind_result.values.get('signal', 0)) == -1 else None)
                        }
                    except Exception as calc_err:
                        logger.debug(f"ADX calc error: {calc_err}")

                elif ind_type == 'vwap' and MODULAR_INDICATORS_AVAILABLE:
                    try:
                        candle_list = [
                            Candle(
                                timestamp=candles[i]['time'] if isinstance(candles[i]['time'], datetime) else datetime.fromtimestamp(candles[i]['time'] / 1000),
                                open=candles[i].get('open', candles[i]['close']),
                                high=candles[i]['high'],
                                low=candles[i]['low'],
                                close=candles[i]['close'],
                                volume=candles[i].get('volume', 1)
                            )
                            for i in range(len(candles))
                        ]
                        calc = VWAPCalculator(params)
                        ind_result = calc.calculate(candle_list)
                        result = {
                            'vwap': float(ind_result.values.get('vwap', 0)),
                            'upper_band': float(ind_result.values.get('upper_band', 0)),
                            'lower_band': float(ind_result.values.get('lower_band', 0)),
                            'deviation': float(ind_result.values.get('deviation', 0)),
                            'signal': 'buy' if int(ind_result.values.get('signal', 0)) == 1 else ('sell' if int(ind_result.values.get('signal', 0)) == -1 else None)
                        }
                    except Exception as calc_err:
                        logger.debug(f"VWAP calc error: {calc_err}")

                elif ind_type == 'ichimoku' and MODULAR_INDICATORS_AVAILABLE:
                    try:
                        candle_list = [
                            Candle(
                                timestamp=candles[i]['time'] if isinstance(candles[i]['time'], datetime) else datetime.fromtimestamp(candles[i]['time'] / 1000),
                                open=candles[i].get('open', candles[i]['close']),
                                high=candles[i]['high'],
                                low=candles[i]['low'],
                                close=candles[i]['close'],
                                volume=candles[i].get('volume', 0)
                            )
                            for i in range(len(candles))
                        ]
                        calc = IchimokuCalculator(params)
                        ind_result = calc.calculate(candle_list)
                        trend_val = int(ind_result.values.get('trend', 0))
                        result = {
                            'tenkan': float(ind_result.values.get('tenkan', 0)),
                            'kijun': float(ind_result.values.get('kijun', 0)),
                            'senkou_a': float(ind_result.values.get('senkou_a', 0)),
                            'senkou_b': float(ind_result.values.get('senkou_b', 0)),
                            'cloud_top': float(ind_result.values.get('cloud_top', 0)),
                            'cloud_bottom': float(ind_result.values.get('cloud_bottom', 0)),
                            'trend': trend_val,
                            'signal': 'buy' if int(ind_result.values.get('signal', 0)) == 1 else ('sell' if int(ind_result.values.get('signal', 0)) == -1 else None)
                        }
                    except Exception as calc_err:
                        logger.debug(f"Ichimoku calc error: {calc_err}")

                elif ind_type == 'obv' and MODULAR_INDICATORS_AVAILABLE:
                    try:
                        candle_list = [
                            Candle(
                                timestamp=candles[i]['time'] if isinstance(candles[i]['time'], datetime) else datetime.fromtimestamp(candles[i]['time'] / 1000),
                                open=candles[i].get('open', candles[i]['close']),
                                high=candles[i]['high'],
                                low=candles[i]['low'],
                                close=candles[i]['close'],
                                volume=candles[i].get('volume', 1)
                            )
                            for i in range(len(candles))
                        ]
                        calc = OBVCalculator(params)
                        ind_result = calc.calculate(candle_list)
                        trend_val = int(ind_result.values.get('trend', 0))
                        result = {
                            'obv': float(ind_result.values.get('obv', 0)),
                            'obv_sma': float(ind_result.values.get('obv_sma', 0)),
                            'obv_normalized': float(ind_result.values.get('obv_normalized', 50)),
                            'trend': trend_val,
                            'divergence': int(ind_result.values.get('divergence', 0)),
                            'signal': 'buy' if int(ind_result.values.get('signal', 0)) == 1 else ('sell' if int(ind_result.values.get('signal', 0)) == -1 else None)
                        }
                    except Exception as calc_err:
                        logger.debug(f"OBV calc error: {calc_err}")

                if result:
                    state.latest_indicators[symbol][ind_type] = result
                    logger.debug(f"Calculated {ind_type}", symbol=symbol, result=result)

            except Exception as e:
                logger.error(f"Error calculating {ind_type}: {e}", symbol=symbol)

    def _get_nadaraya_watson_values(self, closes, params) -> Optional[Dict]:
        """Get Nadaraya-Watson values for condition evaluation (when no signal)"""
        bandwidth = params.get('bandwidth', 8)
        mult = params.get('mult', 3.0)

        n = len(closes)
        if n < bandwidth * 2:
            return None

        # Gaussian Kernel Regression (same logic as IndicatorAlertMonitor)
        y_hat = np.zeros(n)
        for i in range(n):
            sum_weights = 0.0
            sum_weighted = 0.0
            for j in range(n):
                distance = (i - j) / bandwidth
                weight = np.exp(-0.5 * distance * distance)
                sum_weights += weight
                sum_weighted += weight * closes[j]
            y_hat[i] = sum_weighted / sum_weights if sum_weights > 0 else closes[i]

        mae = np.mean(np.abs(closes - y_hat))
        upper = y_hat + mult * mae
        lower = y_hat - mult * mae

        idx = -1
        return {
            'value': float(y_hat[idx]),
            'upper': float(upper[idx]),
            'lower': float(lower[idx])
        }

    def _get_rsi_values(self, closes, params) -> Optional[Dict]:
        """Get RSI value for condition evaluation (when no signal)"""
        period = params.get('period', 14)
        if len(closes) < period + 1:
            return None

        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.zeros(len(deltas))
        avg_loss = np.zeros(len(deltas))
        avg_gain[period-1] = np.mean(gains[:period])
        avg_loss[period-1] = np.mean(losses[:period])

        for i in range(period, len(deltas)):
            avg_gain[i] = (avg_gain[i-1] * (period-1) + gains[i]) / period
            avg_loss[i] = (avg_loss[i-1] * (period-1) + losses[i]) / period

        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
        rsi = 100 - (100 / (1 + rs))

        return {'value': float(rsi[-1])}

    def _get_macd_values(self, closes, params) -> Optional[Dict]:
        """Get MACD values for condition evaluation (when no signal)"""
        fast = params.get('fast', 12)
        slow = params.get('slow', 26)
        signal_period = params.get('signal', 9)

        if len(closes) < slow + signal_period:
            return None

        def ema(data, period):
            alpha = 2 / (period + 1)
            result = np.zeros(len(data))
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
            return result

        ema_fast = ema(closes, fast)
        ema_slow = ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = ema(macd_line, signal_period)

        return {
            'macd': float(macd_line[-1]),
            'signal_line': float(signal_line[-1]),
            'histogram': float(macd_line[-1] - signal_line[-1])
        }

    def _get_bollinger_values(self, closes, params) -> Optional[Dict]:
        """Get Bollinger Bands values for condition evaluation (when no signal)"""
        period = params.get('period', 20)
        stddev = params.get('stddev', 2.0)

        if len(closes) < period:
            return None

        window = closes[-period:]
        sma = np.mean(window)
        std = np.std(window)
        upper = sma + stddev * std
        lower = sma - stddev * std

        # Calculate bandwidth (percentage of middle band)
        bandwidth = ((upper - lower) / sma) * 100 if sma > 0 else 0

        # Calculate %B (where price is within the bands)
        percent_b = (closes[-1] - lower) / (upper - lower) if (upper - lower) > 0 else 0.5

        return {
            'middle': float(sma),
            'upper': float(upper),
            'lower': float(lower),
            'bandwidth': float(bandwidth),
            'percent_b': float(percent_b)
        }

    def _get_ema_cross_values(self, closes, params) -> Optional[Dict]:
        """Get EMA Cross values for condition evaluation"""
        fast_period = params.get('fast_period', 9)
        slow_period = params.get('slow_period', 21)

        if len(closes) < slow_period:
            return None

        def ema(data, period):
            alpha = 2 / (period + 1)
            result = np.zeros(len(data))
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
            return result

        fast_ema = ema(closes, fast_period)
        slow_ema = ema(closes, slow_period)

        # Determine trend: 1 = bullish (fast > slow), -1 = bearish
        trend = 1 if fast_ema[-1] > slow_ema[-1] else -1

        return {
            'fast_ema': float(fast_ema[-1]),
            'slow_ema': float(slow_ema[-1]),
            'trend': trend
        }

    async def _evaluate_conditions(
        self,
        state: StrategyState,
        symbol: str
    ) -> None:
        """Evaluate entry/exit conditions and generate signals"""
        # Check cooldown
        last_signal = state.last_signal_time.get(symbol)
        if last_signal:
            cooldown = timedelta(minutes=state.signal_cooldown_minutes)
            if datetime.utcnow() - last_signal < cooldown:
                return

        # Get current price
        candles = state.candle_buffers.get(symbol, [])
        if not candles:
            return
        last_candle = candles[-1]
        current_close = float(last_candle['close'])

        # Get indicator values
        indicators = state.latest_indicators.get(symbol, {})
        if not indicators:
            return

        # Prepare context for condition evaluation
        context = {
            "close": current_close,
            "open": float(last_candle['open']),
            "high": float(last_candle['high']),
            "low": float(last_candle['low']),
            "volume": float(last_candle['volume']),
        }

        # Add indicator values to context
        for name, result in indicators.items():
            if isinstance(result, dict):
                for key, value in result.items():
                    if value is not None:
                        context[f"{name}.{key}"] = float(value) if not isinstance(value, str) else value

        # Check entry conditions
        for condition_type in [ConditionType.ENTRY_LONG, ConditionType.ENTRY_SHORT]:
            conditions = state.conditions.get(condition_type, [])
            operator = state.condition_operators.get(condition_type, LogicOperator.AND)

            if conditions and self._evaluate_condition_set(conditions, operator, context):
                signal_type = SignalType.LONG if condition_type == ConditionType.ENTRY_LONG else SignalType.SHORT
                action = "buy" if signal_type == SignalType.LONG else "sell"

                await self._generate_signal(
                    state=state,
                    symbol=symbol,
                    signal_type=signal_type,
                    action=action,
                    entry_price=Decimal(str(current_close)),
                    indicator_values=context
                )

                # Update last signal time
                state.last_signal_time[symbol] = datetime.utcnow()
                break  # Only one signal per evaluation

    def _evaluate_condition_set(
        self,
        conditions: List[Dict],
        operator: LogicOperator,
        context: Dict[str, float]
    ) -> bool:
        """Evaluate a set of conditions with AND/OR logic"""
        results = []

        for cond in conditions:
            left_key = cond.get("left", "")
            right_key = cond.get("right", "")
            op = cond.get("operator", "")

            # Get values from context
            left_val = self._get_context_value(left_key, context)
            right_val = self._get_context_value(right_key, context)

            if left_val is None or right_val is None:
                continue

            # Evaluate operator
            result = self._compare(left_val, op, right_val)
            results.append(result)

        if not results:
            return False

        if operator == LogicOperator.AND:
            return all(results)
        else:  # OR
            return any(results)

    def _get_context_value(self, key: str, context: Dict[str, float]) -> Optional[float]:
        """Get a value from context, handling nested keys like 'ndy.lower'"""
        if key in context:
            return context[key]

        # Try to parse as number
        try:
            return float(key)
        except ValueError:
            pass

        # Map common aliases
        aliases = {
            "ndy.lower": "nadaraya_watson.lower",
            "ndy.upper": "nadaraya_watson.upper",
            "ndy.value": "nadaraya_watson.value",
            "tpo.val": "tpo.val",
            "tpo.vah": "tpo.vah",
            "tpo.poc": "tpo.poc",
        }

        if key in aliases:
            return context.get(aliases[key])

        return None

    def _compare(self, left: float, op: str, right: float) -> bool:
        """Compare two values with given operator"""
        ops = {
            "<": lambda a, b: a < b,
            ">": lambda a, b: a > b,
            "<=": lambda a, b: a <= b,
            ">=": lambda a, b: a >= b,
            "==": lambda a, b: abs(a - b) < 0.0001,
            "!=": lambda a, b: abs(a - b) >= 0.0001,
            "crosses_above": lambda a, b: a > b,
            "crosses_below": lambda a, b: a < b,
        }
        return ops.get(op, lambda a, b: False)(left, right)

    async def _generate_signal(
        self,
        state: StrategyState,
        symbol: str,
        signal_type: SignalType,
        action: str,
        entry_price: Decimal,
        indicator_values: Dict[str, float]
    ) -> None:
        """Generate and record a trading signal"""
        logger.info(
            f"Signal generated!",
            strategy_id=state.strategy_id,
            symbol=symbol,
            signal_type=signal_type.value,
            action=action,
            entry_price=float(entry_price)
        )

        # Record signal in database
        # Create signal via SQL repository
        created_signal = await self._signal_repo.create(
            strategy_id=state.strategy_id,
            symbol=symbol,
            signal_type=signal_type.value,
            entry_price=float(entry_price),
            indicator_values=indicator_values
        )

        # Forward to bot_broadcast_service if bot is linked
        if state.bot_id:
            try:
                result = await self._broadcast_service.broadcast_signal(
                    bot_id=UUID(state.bot_id),
                    ticker=symbol,
                    action=action,
                    source_ip="strategy_engine",
                    payload={
                        "strategy_signal_id": str(created_signal["id"]),
                        "strategy_id": state.strategy_id,
                        "indicator_values": indicator_values
                    }
                )

                if result.get("success") and result.get("signal_id"):
                    # Check if at least one execution was successful
                    successful_executions = result.get("successful", 0)
                    if successful_executions > 0:
                        await self._signal_repo.mark_executed(
                            created_signal["id"],
                            result.get("signal_id", "")
                        )
                        logger.info(
                            f"Signal executed successfully",
                            bot_id=state.bot_id,
                            successful=successful_executions,
                            failed=result.get("failed", 0)
                        )
                    else:
                        # Broadcast completed but all executions failed
                        await self._signal_repo.mark_failed(created_signal["id"])
                        logger.warning(
                            f"Signal broadcast completed but all executions failed",
                            bot_id=state.bot_id,
                            total_subscribers=result.get("total_subscribers", 0),
                            failed=result.get("failed", 0)
                        )
                else:
                    await self._signal_repo.mark_failed(created_signal["id"])
                    logger.warning(
                        f"Signal broadcast failed",
                        bot_id=state.bot_id,
                        error=result.get("message")
                    )

            except Exception as e:
                await self._signal_repo.mark_failed(created_signal["id"])
                logger.error(f"Error broadcasting signal: {e}")
        else:
            logger.warning(
                f"No bot linked to strategy, signal not broadcast",
                strategy_id=state.strategy_id
            )

    async def _monitoring_loop(self) -> None:
        """Background task for periodic monitoring, polling candles and evaluating conditions"""
        while self._running:
            try:
                # Poll interval (30 seconds)
                await asyncio.sleep(30)

                # For each active strategy, fetch latest candles and evaluate
                for strategy_id, state in self._strategies.items():
                    for symbol in state.symbols:
                        try:
                            # Fetch latest candles
                            await self._refresh_candles(state, symbol)

                            # Calculate indicators using IndicatorAlertMonitor methods
                            await self._calculate_indicators(state, symbol)

                            # Evaluate conditions
                            await self._evaluate_conditions(state, symbol)

                        except Exception as e:
                            logger.error(f"Error processing {symbol}: {e}", strategy_id=strategy_id)

                logger.debug(
                    "Strategy Engine status",
                    active_strategies=len(self._strategies)
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

    async def _refresh_candles(self, state: StrategyState, symbol: str) -> None:
        """Fetch latest candles and update buffer"""
        try:
            import aiohttp

            url = "https://fapi.binance.com/fapi/v1/klines"
            params = {
                "symbol": symbol.upper(),
                "interval": state.timeframe,
                "limit": 10
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return
                    klines = await resp.json()

            buffer = state.candle_buffers.get(symbol, [])

            for k in klines:
                candle = {
                    'time': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                }

                existing_idx = None
                for i, c in enumerate(buffer):
                    if c['time'] == candle['time']:
                        existing_idx = i
                        break

                if existing_idx is not None:
                    buffer[existing_idx] = candle
                else:
                    buffer.append(candle)

            if len(buffer) > state.max_candles:
                buffer = buffer[-state.max_candles:]

            state.candle_buffers[symbol] = buffer

        except Exception as e:
            logger.error(f"Error refreshing candles: {e}", symbol=symbol)

    def get_status(self) -> Dict[str, Any]:
        """Get current engine status"""
        return {
            "running": self._running,
            "active_strategies": len(self._strategies),
            "strategies": [
                {
                    "id": s.strategy_id,
                    "symbols": s.symbols,
                    "timeframe": s.timeframe,
                    "indicators": list(s.indicator_configs.keys()),
                    "candle_counts": {sym: len(buf) for sym, buf in s.candle_buffers.items()}
                }
                for s in self._strategies.values()
            ]
        }


# Singleton instance
_engine_instance: Optional[StrategyEngineService] = None


def get_strategy_engine(db_pool) -> StrategyEngineService:
    """Get or create singleton engine instance"""
    global _engine_instance

    if _engine_instance is None:
        _engine_instance = StrategyEngineService(db_pool)

    return _engine_instance


async def start_strategy_engine(db_pool) -> StrategyEngineService:
    """Start and return the strategy engine"""
    engine = get_strategy_engine(db_pool)
    await engine.start()
    return engine
