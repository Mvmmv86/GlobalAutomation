"""
Strategy WebSocket Monitor

Real-time strategy signal detection using Binance WebSocket.
Instead of polling every 30 seconds, this monitor receives candle updates
in real-time (< 1 second latency) and evaluates strategy conditions immediately.

Flow:
1. Load active strategies from database
2. Subscribe to WebSocket kline streams for all strategy symbols/timeframes
3. On each candle update:
   - Update candle buffer
   - Calculate indicators using IndicatorAlertMonitor methods (NO DUPLICATION)
   - Evaluate entry/exit conditions
   - Generate signals and forward to bot_broadcast_service
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

import structlog

from infrastructure.exchanges.binance_websocket import (
    BinanceWebSocketManager,
    KlineData,
    get_binance_ws_manager,
)
from infrastructure.database.models.strategy import (
    ConditionType,
    LogicOperator,
    SignalStatus,
    SignalType,
    Strategy,
)
from infrastructure.database.repositories.strategy import (
    StrategyRepository,
    StrategySignalRepository,
)
from infrastructure.services.bot_broadcast_service import BotBroadcastService
from infrastructure.services.indicator_alert_monitor import IndicatorAlertMonitor

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

logger = structlog.get_logger(__name__)


@dataclass
class StrategyRuntimeState:
    """Runtime state for an active strategy being monitored via WebSocket"""
    strategy_id: str
    strategy_name: str
    symbols: List[str]
    timeframe: str
    bot_id: Optional[str]

    # Indicator configurations
    indicator_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Candle buffers per symbol
    candle_buffers: Dict[str, List[Dict]] = field(default_factory=lambda: defaultdict(list))

    # Latest indicator values per symbol
    latest_indicators: Dict[str, Dict[str, Any]] = field(default_factory=lambda: defaultdict(dict))

    # Conditions (loaded from strategy)
    conditions: Dict[ConditionType, List[Dict]] = field(default_factory=dict)
    condition_operators: Dict[ConditionType, LogicOperator] = field(default_factory=dict)

    # Last signal time per symbol (cooldown)
    last_signal_time: Dict[str, datetime] = field(default_factory=dict)

    # Configuration
    max_candles: int = 500
    min_candles_for_signal: int = 50
    signal_cooldown_minutes: int = 5

    # WebSocket stream IDs for cleanup
    stream_ids: List[str] = field(default_factory=list)


class StrategyWebSocketMonitor:
    """
    Strategy WebSocket Monitor

    Real-time strategy signal detection with < 1 second latency.
    Uses Binance WebSocket for live candle data instead of HTTP polling.

    Key differences from StrategyEngineService (polling version):
    - Real-time: Receives candle updates via WebSocket (< 1s latency)
    - Event-driven: Evaluates conditions on each candle close, not periodically
    - Efficient: Only processes when new data arrives

    Usage:
        monitor = StrategyWebSocketMonitor(db_pool)
        await monitor.start()

        # Monitor runs in background, watching active strategies
        await monitor.reload_strategies()

        await monitor.stop()
    """

    SUPPORTED_INDICATORS = [
        'nadaraya_watson', 'rsi', 'macd', 'bollinger', 'ema_cross', 'tpo'
    ]

    def __init__(self, db_pool):
        self.db = db_pool
        self._running = False

        # Active strategy states
        self._strategies: Dict[str, StrategyRuntimeState] = {}

        # WebSocket manager
        self._ws_manager: Optional[BinanceWebSocketManager] = None

        # Services
        self._broadcast_service: Optional[BotBroadcastService] = None
        self._strategy_repo: Optional[StrategyRepository] = None
        self._signal_repo: Optional[StrategySignalRepository] = None
        self._indicator_monitor: Optional[IndicatorAlertMonitor] = None

        # Track subscriptions by symbol+timeframe
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)  # stream_id -> strategy_ids

        # Background reload task
        self._reload_task: Optional[asyncio.Task] = None

        logger.info("StrategyWebSocketMonitor initialized")

    async def start(self) -> None:
        """Start the WebSocket monitor"""
        if self._running:
            logger.warning("StrategyWebSocketMonitor already running")
            return

        if not NUMPY_AVAILABLE:
            logger.warning("Cannot start StrategyWebSocketMonitor - NumPy not installed")
            return

        logger.info("Starting StrategyWebSocketMonitor...")

        self._running = True

        # Initialize components
        self._broadcast_service = BotBroadcastService(self.db)
        self._strategy_repo = StrategyRepository(self.db)
        self._signal_repo = StrategySignalRepository(self.db)
        self._indicator_monitor = IndicatorAlertMonitor(self.db)

        # Get WebSocket manager (singleton)
        self._ws_manager = get_binance_ws_manager(use_futures=True)
        await self._ws_manager.start()

        # Load active strategies
        await self.reload_strategies()

        # Start periodic reload task (check for new/modified strategies every 60s)
        self._reload_task = asyncio.create_task(self._periodic_reload())

        logger.info("StrategyWebSocketMonitor started")

    async def stop(self) -> None:
        """Stop the WebSocket monitor"""
        logger.info("Stopping StrategyWebSocketMonitor...")

        self._running = False

        # Cancel reload task
        if self._reload_task:
            self._reload_task.cancel()
            try:
                await self._reload_task
            except asyncio.CancelledError:
                pass

        # Unsubscribe from all streams
        for strategy_id in list(self._strategies.keys()):
            await self._deactivate_strategy(strategy_id)

        # Stop WebSocket manager
        if self._ws_manager:
            await self._ws_manager.stop()

        logger.info("StrategyWebSocketMonitor stopped")

    async def reload_strategies(self) -> None:
        """Load or reload active strategies"""
        logger.info("Reloading active strategies for WebSocket monitoring...")

        active_strategies = await self._strategy_repo.get_active_strategies()

        current_ids = set(self._strategies.keys())
        new_ids = {str(s.id) for s in active_strategies}

        # Remove deactivated strategies
        for strategy_id in current_ids - new_ids:
            await self._deactivate_strategy(strategy_id)

        # Add/update active strategies
        for strategy in active_strategies:
            strategy_id = str(strategy.id)

            if strategy_id not in current_ids:
                await self._activate_strategy(strategy)

        logger.info(
            f"Strategy reload complete",
            active_count=len(self._strategies),
            subscribed_streams=len(self._subscriptions)
        )

    async def _activate_strategy(self, strategy: Strategy) -> None:
        """Activate a strategy and subscribe to WebSocket streams"""
        strategy_id = str(strategy.id)

        logger.info(f"Activating strategy for WebSocket: {strategy.name} ({strategy_id})")

        # Load full strategy with relations
        full_strategy = await self._strategy_repo.get_with_relations(strategy.id)
        if not full_strategy:
            logger.error(f"Could not load strategy relations: {strategy_id}")
            return

        # Create runtime state
        state = StrategyRuntimeState(
            strategy_id=strategy_id,
            strategy_name=strategy.name,
            symbols=full_strategy.get_symbols_list(),
            timeframe=full_strategy.timeframe,
            bot_id=str(full_strategy.bot_id) if full_strategy.bot_id else None
        )

        # Load indicator configs
        for indicator in full_strategy.indicators:
            ind_type = indicator.indicator_type.value if hasattr(indicator.indicator_type, 'value') else str(indicator.indicator_type)
            if ind_type in self.SUPPORTED_INDICATORS:
                state.indicator_configs[ind_type] = indicator.parameters or {}

        # Load conditions
        for condition in full_strategy.conditions:
            state.conditions[condition.condition_type] = condition.get_conditions_list()
            state.condition_operators[condition.condition_type] = condition.logic_operator

        # Store state
        self._strategies[strategy_id] = state

        # Subscribe to WebSocket streams for each symbol
        for symbol in state.symbols:
            # Load historical candles first
            await self._load_historical_candles(state, symbol)

            # Subscribe to real-time kline stream
            stream_id = await self._subscribe_kline(symbol, state.timeframe, strategy_id)
            state.stream_ids.append(stream_id)

        logger.info(
            f"Strategy activated for WebSocket monitoring: {strategy.name}",
            symbols=state.symbols,
            timeframe=state.timeframe,
            indicators=list(state.indicator_configs.keys())
        )

    async def _deactivate_strategy(self, strategy_id: str) -> None:
        """Deactivate a strategy and unsubscribe from streams"""
        state = self._strategies.pop(strategy_id, None)
        if not state:
            return

        logger.info(f"Deactivating strategy: {strategy_id}")

        # Remove from subscription tracking
        for stream_id in state.stream_ids:
            if stream_id in self._subscriptions:
                self._subscriptions[stream_id].discard(strategy_id)

                # If no more strategies using this stream, unsubscribe
                if not self._subscriptions[stream_id]:
                    await self._ws_manager.unsubscribe(stream_id)
                    del self._subscriptions[stream_id]

    async def _subscribe_kline(self, symbol: str, timeframe: str, strategy_id: str) -> str:
        """Subscribe to kline stream and track subscription"""
        stream_id = f"{symbol.lower()}@kline_{timeframe}"

        # Track which strategies use this stream
        self._subscriptions[stream_id].add(strategy_id)

        # Only subscribe if first strategy using this stream
        if len(self._subscriptions[stream_id]) == 1:
            await self._ws_manager.subscribe_kline(
                symbol=symbol,
                interval=timeframe,
                callback=lambda kline: asyncio.create_task(self._on_kline_update(kline))
            )

        return stream_id

    async def _on_kline_update(self, kline: KlineData) -> None:
        """
        Callback for WebSocket kline updates.
        This is the real-time entry point - called on every candle update!
        """
        if not self._running:
            return

        symbol = kline.symbol.upper()
        timeframe = kline.interval

        # Find all strategies monitoring this symbol/timeframe
        for strategy_id, state in self._strategies.items():
            if symbol not in state.symbols:
                continue
            if state.timeframe != timeframe:
                continue

            try:
                # Update candle buffer
                self._update_candle_buffer(state, symbol, kline)

                # Only evaluate on candle close (most important moment)
                if kline.is_closed:
                    logger.debug(
                        f"Candle closed - evaluating strategy",
                        strategy=state.strategy_name,
                        symbol=symbol,
                        close=float(kline.close)
                    )

                    # Calculate indicators using IndicatorAlertMonitor methods
                    await self._calculate_indicators(state, symbol)

                    # Evaluate conditions
                    await self._evaluate_conditions(state, symbol)

            except Exception as e:
                logger.error(
                    f"Error processing kline update: {e}",
                    strategy_id=strategy_id,
                    symbol=symbol
                )

    def _update_candle_buffer(self, state: StrategyRuntimeState, symbol: str, kline: KlineData) -> None:
        """Update candle buffer with new/updated kline data"""
        buffer = state.candle_buffers[symbol]

        candle = kline.to_dict()

        # Check if we're updating existing candle or adding new
        if buffer:
            last_candle = buffer[-1]
            if last_candle['time'] == candle['time']:
                # Update current candle
                buffer[-1] = candle
            else:
                # Add new candle
                buffer.append(candle)
        else:
            buffer.append(candle)

        # Trim buffer if too large
        if len(buffer) > state.max_candles:
            state.candle_buffers[symbol] = buffer[-state.max_candles:]

    async def _load_historical_candles(self, state: StrategyRuntimeState, symbol: str) -> None:
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
                    if resp.status != 200:
                        logger.error(f"Failed to fetch historical klines: {resp.status}")
                        return
                    klines = await resp.json()

            # Convert to candle format
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
                strategy=state.strategy_name
            )

        except Exception as e:
            logger.error(f"Error loading historical candles: {e}", symbol=symbol)

    async def _calculate_indicators(self, state: StrategyRuntimeState, symbol: str) -> None:
        """
        Calculate all configured indicators for a symbol.
        USES IndicatorAlertMonitor methods - NO CODE DUPLICATION!
        """
        candles = state.candle_buffers.get(symbol, [])

        if len(candles) < state.min_candles_for_signal:
            return

        if not NUMPY_AVAILABLE or not self._indicator_monitor:
            return

        # Extract arrays
        closes = np.array([c['close'] for c in candles])
        times = [c['time'] for c in candles]

        for ind_type, params in state.indicator_configs.items():
            try:
                result = None

                # REUSE IndicatorAlertMonitor calculation methods!
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

                if result:
                    state.latest_indicators[symbol][ind_type] = result

            except Exception as e:
                logger.error(f"Error calculating {ind_type}: {e}", symbol=symbol)

    def _get_nadaraya_watson_values(self, closes, params) -> Optional[Dict]:
        """Get NDY values for condition evaluation when no signal"""
        bandwidth = params.get('bandwidth', 8)
        mult = params.get('mult', 3.0)

        n = len(closes)
        if n < bandwidth * 2:
            return None

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

        return {
            'value': float(y_hat[-1]),
            'upper': float(upper[-1]),
            'lower': float(lower[-1])
        }

    def _get_rsi_values(self, closes, params) -> Optional[Dict]:
        """Get RSI value for condition evaluation"""
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
        """Get MACD values for condition evaluation"""
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
        """Get Bollinger values for condition evaluation"""
        period = params.get('period', 20)
        stddev = params.get('stddev', 2.0)

        if len(closes) < period:
            return None

        window = closes[-period:]
        sma = np.mean(window)
        std = np.std(window)

        return {
            'middle': float(sma),
            'upper': float(sma + stddev * std),
            'lower': float(sma - stddev * std)
        }

    async def _evaluate_conditions(self, state: StrategyRuntimeState, symbol: str) -> None:
        """Evaluate entry/exit conditions and generate signals"""
        # Check cooldown
        last_signal = state.last_signal_time.get(symbol)
        if last_signal:
            cooldown = timedelta(minutes=state.signal_cooldown_minutes)
            if datetime.utcnow() - last_signal < cooldown:
                return

        candles = state.candle_buffers.get(symbol, [])
        if not candles:
            return

        last_candle = candles[-1]
        current_close = float(last_candle['close'])

        indicators = state.latest_indicators.get(symbol, {})
        if not indicators:
            return

        # Build context for condition evaluation
        context = {
            "close": current_close,
            "open": float(last_candle['open']),
            "high": float(last_candle['high']),
            "low": float(last_candle['low']),
            "volume": float(last_candle['volume']),
        }

        # Add indicator values
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

                state.last_signal_time[symbol] = datetime.utcnow()
                break

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

            left_val = self._get_context_value(left_key, context)
            right_val = self._get_context_value(right_key, context)

            if left_val is None or right_val is None:
                continue

            result = self._compare(left_val, op, right_val)
            results.append(result)

        if not results:
            return False

        if operator == LogicOperator.AND:
            return all(results)
        else:
            return any(results)

    def _get_context_value(self, key: str, context: Dict[str, float]) -> Optional[float]:
        """Get value from context, handling nested keys"""
        if key in context:
            return context[key]

        try:
            return float(key)
        except ValueError:
            pass

        aliases = {
            "ndy.lower": "nadaraya_watson.lower",
            "ndy.upper": "nadaraya_watson.upper",
            "ndy.value": "nadaraya_watson.value",
        }

        if key in aliases:
            return context.get(aliases[key])

        return None

    def _compare(self, left: float, op: str, right: float) -> bool:
        """Compare two values"""
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
        state: StrategyRuntimeState,
        symbol: str,
        signal_type: SignalType,
        action: str,
        entry_price: Decimal,
        indicator_values: Dict[str, float]
    ) -> None:
        """Generate and record a trading signal"""
        logger.info(
            f"SIGNAL GENERATED (WebSocket)",
            strategy=state.strategy_name,
            strategy_id=state.strategy_id,
            symbol=symbol,
            signal_type=signal_type.value,
            action=action,
            entry_price=float(entry_price)
        )

        # Record in database
        from infrastructure.database.models.strategy import StrategySignal

        signal = StrategySignal(
            strategy_id=state.strategy_id,
            symbol=symbol,
            signal_type=signal_type,
            entry_price=entry_price,
            indicator_values=indicator_values,
            status=SignalStatus.PENDING
        )

        created_signal = await self._signal_repo.create(signal)

        # Forward to bot_broadcast_service
        if state.bot_id:
            try:
                result = await self._broadcast_service.broadcast_signal(
                    bot_id=UUID(state.bot_id),
                    ticker=symbol,
                    action=action,
                    source_ip="strategy_websocket_monitor",
                    payload={
                        "strategy_signal_id": str(created_signal.id),
                        "strategy_id": state.strategy_id,
                        "strategy_name": state.strategy_name,
                        "indicator_values": indicator_values,
                        "realtime": True  # Mark as real-time signal
                    }
                )

                if result.get("success"):
                    if result.get("signal_id"):
                        await self._signal_repo.update(
                            created_signal.id,
                            status=SignalStatus.EXECUTED,
                            bot_signal_id=result.get("signal_id")
                        )
                    logger.info(
                        f"Signal forwarded to bot via WebSocket monitor",
                        bot_id=state.bot_id,
                        result=result
                    )
                else:
                    await self._signal_repo.update(
                        created_signal.id,
                        status=SignalStatus.FAILED
                    )
                    logger.warning(
                        f"Signal broadcast failed",
                        bot_id=state.bot_id,
                        error=result.get("message")
                    )

            except Exception as e:
                await self._signal_repo.update(
                    created_signal.id,
                    status=SignalStatus.FAILED
                )
                logger.error(f"Error broadcasting signal: {e}")
        else:
            logger.warning(
                f"No bot linked - signal not broadcast",
                strategy_id=state.strategy_id
            )

    async def _periodic_reload(self) -> None:
        """Periodically check for new/modified strategies"""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every 60 seconds
                await self.reload_strategies()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic reload: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current monitor status"""
        return {
            "running": self._running,
            "ws_connected": self._ws_manager.is_connected() if self._ws_manager else False,
            "active_strategies": len(self._strategies),
            "subscribed_streams": len(self._subscriptions),
            "strategies": [
                {
                    "id": s.strategy_id,
                    "name": s.strategy_name,
                    "symbols": s.symbols,
                    "timeframe": s.timeframe,
                    "indicators": list(s.indicator_configs.keys()),
                    "candle_counts": {sym: len(buf) for sym, buf in s.candle_buffers.items()},
                    "bot_linked": s.bot_id is not None
                }
                for s in self._strategies.values()
            ]
        }


# Singleton
_monitor_instance: Optional[StrategyWebSocketMonitor] = None


def get_strategy_ws_monitor(db_pool) -> StrategyWebSocketMonitor:
    """Get or create singleton monitor instance"""
    global _monitor_instance

    if _monitor_instance is None:
        _monitor_instance = StrategyWebSocketMonitor(db_pool)

    return _monitor_instance


async def start_strategy_ws_monitor(db_pool) -> StrategyWebSocketMonitor:
    """Start and return the WebSocket monitor"""
    monitor = get_strategy_ws_monitor(db_pool)
    await monitor.start()
    return monitor
