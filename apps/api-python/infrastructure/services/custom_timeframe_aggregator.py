"""
Custom Timeframe Aggregator

Aggregates 1-minute candles into custom timeframes (like 12 minutes)
that are not natively supported by Binance.

This is essential for strategies that require non-standard timeframes
like TPO + Nadaraya-Watson which operates on 12-minute candles.

How it works:
1. Subscribe to 1-minute WebSocket stream
2. Buffer 1-minute candles
3. Aggregate N candles into 1 custom timeframe candle
4. Emit aggregated candle when complete

Reference: https://atekihcan.com/blog/codeortrading/changing-timeframe-of-ohlc-candlestick-data-in-pandas/
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Set
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AggregatedCandle:
    """Represents an aggregated candle from multiple 1-minute candles"""
    symbol: str
    interval: str  # Custom interval like "12m"
    start_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    candle_count: int  # How many 1m candles were aggregated
    is_closed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format compatible with indicators"""
        return {
            'time': int(self.start_time.timestamp() * 1000),
            'open': float(self.open),
            'high': float(self.high),
            'low': float(self.low),
            'close': float(self.close),
            'volume': float(self.volume)
        }


@dataclass
class CandleBuffer:
    """Buffer for aggregating 1-minute candles into custom timeframe"""
    target_minutes: int  # e.g., 12 for 12-minute candles
    symbol: str

    # Current aggregation state
    current_candle: Optional[AggregatedCandle] = None
    one_minute_candles: List[Dict] = field(default_factory=list)

    # Completed candles history (for indicator calculation)
    completed_candles: List[Dict] = field(default_factory=list)
    max_history: int = 500  # Keep last 500 aggregated candles

    def get_period_start(self, timestamp: datetime) -> datetime:
        """
        Calculate the start of the current period.
        For 12-minute candles, periods start at 00:00, 00:12, 00:24, etc.
        """
        total_minutes = timestamp.hour * 60 + timestamp.minute
        period_start_minutes = (total_minutes // self.target_minutes) * self.target_minutes

        return timestamp.replace(
            hour=period_start_minutes // 60,
            minute=period_start_minutes % 60,
            second=0,
            microsecond=0
        )

    def add_one_minute_candle(self, candle: Dict) -> Optional[AggregatedCandle]:
        """
        Add a 1-minute candle and return aggregated candle if period completed.

        Args:
            candle: Dict with keys: time, open, high, low, close, volume

        Returns:
            AggregatedCandle if period just completed, None otherwise
        """
        # Parse timestamp
        candle_time = candle.get('time')
        if isinstance(candle_time, (int, float)):
            timestamp = datetime.fromtimestamp(candle_time / 1000)
        else:
            timestamp = candle_time

        period_start = self.get_period_start(timestamp)

        # Check if this is a new period
        if self.current_candle is None or period_start != self.current_candle.start_time:
            # Complete current candle if exists
            completed = None
            if self.current_candle is not None and self.one_minute_candles:
                completed = self._finalize_current_candle()

            # Start new aggregation period
            self.current_candle = AggregatedCandle(
                symbol=self.symbol,
                interval=f"{self.target_minutes}m",
                start_time=period_start,
                open=Decimal(str(candle['open'])),
                high=Decimal(str(candle['high'])),
                low=Decimal(str(candle['low'])),
                close=Decimal(str(candle['close'])),
                volume=Decimal(str(candle['volume'])),
                candle_count=1,
                is_closed=False
            )
            self.one_minute_candles = [candle]

            return completed
        else:
            # Update current aggregation
            self.one_minute_candles.append(candle)
            self.current_candle.high = max(self.current_candle.high, Decimal(str(candle['high'])))
            self.current_candle.low = min(self.current_candle.low, Decimal(str(candle['low'])))
            self.current_candle.close = Decimal(str(candle['close']))
            self.current_candle.volume += Decimal(str(candle['volume']))
            self.current_candle.candle_count = len(self.one_minute_candles)

            # Check if period is complete (have all N minutes)
            if len(self.one_minute_candles) >= self.target_minutes:
                return self._finalize_current_candle()

            return None

    def _finalize_current_candle(self) -> AggregatedCandle:
        """Finalize and return the current aggregated candle"""
        if self.current_candle is None:
            return None

        self.current_candle.is_closed = True
        completed = self.current_candle

        # Add to history
        self.completed_candles.append(completed.to_dict())

        # Trim history if needed
        if len(self.completed_candles) > self.max_history:
            self.completed_candles = self.completed_candles[-self.max_history:]

        logger.info(
            f"Aggregated candle completed",
            symbol=self.symbol,
            interval=f"{self.target_minutes}m",
            open=float(completed.open),
            high=float(completed.high),
            low=float(completed.low),
            close=float(completed.close),
            volume=float(completed.volume),
            candle_count=completed.candle_count
        )

        # Reset for next period
        self.current_candle = None
        self.one_minute_candles = []

        return completed

    def get_current_candle(self) -> Optional[AggregatedCandle]:
        """Get the current in-progress candle"""
        return self.current_candle

    def get_all_candles(self) -> List[Dict]:
        """Get all completed candles + current (for indicator calculation)"""
        candles = list(self.completed_candles)
        if self.current_candle:
            candles.append(self.current_candle.to_dict())
        return candles


class CustomTimeframeAggregator:
    """
    Manages custom timeframe aggregation for multiple symbols.

    Usage:
        aggregator = CustomTimeframeAggregator()

        # Register a callback for when 12-minute candles complete
        aggregator.register_callback("BTCUSDT", 12, my_callback)

        # Feed 1-minute candles
        aggregator.process_one_minute_candle("BTCUSDT", candle_data)
    """

    # Standard Binance timeframes (in minutes) - these don't need aggregation
    NATIVE_TIMEFRAMES = {1, 3, 5, 15, 30, 60, 120, 240, 360, 480, 720, 1440}

    def __init__(self):
        # Buffers per symbol per target timeframe
        # Key: (symbol, target_minutes) -> CandleBuffer
        self._buffers: Dict[tuple, CandleBuffer] = {}

        # Callbacks per symbol per target timeframe
        # Key: (symbol, target_minutes) -> List[Callable]
        self._callbacks: Dict[tuple, List[Callable]] = defaultdict(list)

        # Track active subscriptions
        self._active_symbols: Set[str] = set()

        logger.info("CustomTimeframeAggregator initialized")

    @staticmethod
    def parse_timeframe(timeframe: str) -> int:
        """
        Parse timeframe string to minutes.

        Examples:
            "12m" -> 12
            "1h" -> 60
            "4h" -> 240
            "1d" -> 1440
        """
        timeframe = timeframe.lower().strip()

        if timeframe.endswith('m'):
            return int(timeframe[:-1])
        elif timeframe.endswith('h'):
            return int(timeframe[:-1]) * 60
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 1440
        elif timeframe.endswith('w'):
            return int(timeframe[:-1]) * 1440 * 7
        else:
            # Assume minutes if no suffix
            return int(timeframe)

    @staticmethod
    def is_custom_timeframe(timeframe: str) -> bool:
        """Check if timeframe requires custom aggregation"""
        minutes = CustomTimeframeAggregator.parse_timeframe(timeframe)
        return minutes not in CustomTimeframeAggregator.NATIVE_TIMEFRAMES

    def register_callback(
        self,
        symbol: str,
        target_minutes: int,
        callback: Callable[[AggregatedCandle], None]
    ) -> None:
        """
        Register a callback for when aggregated candles complete.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            target_minutes: Target timeframe in minutes (e.g., 12)
            callback: Function to call with completed AggregatedCandle
        """
        key = (symbol.upper(), target_minutes)

        # Create buffer if doesn't exist
        if key not in self._buffers:
            self._buffers[key] = CandleBuffer(
                target_minutes=target_minutes,
                symbol=symbol.upper()
            )
            logger.info(
                f"Created aggregation buffer",
                symbol=symbol,
                target_minutes=target_minutes
            )

        # Register callback
        self._callbacks[key].append(callback)
        self._active_symbols.add(symbol.upper())

        logger.info(
            f"Registered callback for custom timeframe",
            symbol=symbol,
            target_minutes=target_minutes,
            total_callbacks=len(self._callbacks[key])
        )

    def unregister_callbacks(self, symbol: str, target_minutes: int) -> None:
        """Remove all callbacks for a symbol/timeframe"""
        key = (symbol.upper(), target_minutes)
        if key in self._callbacks:
            del self._callbacks[key]
        if key in self._buffers:
            del self._buffers[key]

    def process_one_minute_candle(self, symbol: str, candle: Dict) -> List[AggregatedCandle]:
        """
        Process a 1-minute candle and aggregate into custom timeframes.

        Args:
            symbol: Trading symbol
            candle: Dict with keys: time, open, high, low, close, volume

        Returns:
            List of completed aggregated candles (may be empty)
        """
        symbol = symbol.upper()
        completed_candles = []

        # Find all buffers for this symbol
        for (buf_symbol, target_minutes), buffer in self._buffers.items():
            if buf_symbol != symbol:
                continue

            # Add candle to buffer
            completed = buffer.add_one_minute_candle(candle)

            if completed:
                completed_candles.append(completed)

                # Fire callbacks
                key = (symbol, target_minutes)
                for callback in self._callbacks.get(key, []):
                    try:
                        # Support both sync and async callbacks
                        if asyncio.iscoroutinefunction(callback):
                            asyncio.create_task(callback(completed))
                        else:
                            callback(completed)
                    except Exception as e:
                        logger.error(f"Callback error: {e}", symbol=symbol)

        return completed_candles

    def get_buffer(self, symbol: str, target_minutes: int) -> Optional[CandleBuffer]:
        """Get the buffer for a symbol/timeframe"""
        return self._buffers.get((symbol.upper(), target_minutes))

    def get_candles(self, symbol: str, target_minutes: int) -> List[Dict]:
        """Get all aggregated candles (completed + current) for indicator calculation"""
        buffer = self.get_buffer(symbol, target_minutes)
        if buffer:
            return buffer.get_all_candles()
        return []

    def get_active_symbols(self) -> Set[str]:
        """Get all symbols with active aggregation"""
        return self._active_symbols.copy()

    def get_status(self) -> Dict[str, Any]:
        """Get aggregator status"""
        return {
            "active_symbols": list(self._active_symbols),
            "buffers": [
                {
                    "symbol": sym,
                    "target_minutes": mins,
                    "completed_candles": len(buf.completed_candles),
                    "current_candle_count": buf.current_candle.candle_count if buf.current_candle else 0
                }
                for (sym, mins), buf in self._buffers.items()
            ]
        }


# Singleton instance
_aggregator_instance: Optional[CustomTimeframeAggregator] = None


def get_custom_timeframe_aggregator() -> CustomTimeframeAggregator:
    """Get or create singleton aggregator instance"""
    global _aggregator_instance

    if _aggregator_instance is None:
        _aggregator_instance = CustomTimeframeAggregator()

    return _aggregator_instance
