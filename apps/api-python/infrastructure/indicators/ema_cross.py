"""EMA Cross Calculator"""

from decimal import Decimal
from typing import Dict, List, Any

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class EMACrossCalculator(BaseIndicatorCalculator):
    """
    EMA Cross Calculator

    Trend-following indicator based on two EMA crossovers.

    Signals:
    - Fast EMA crosses above Slow EMA = Bullish (trend = 1)
    - Fast EMA crosses below Slow EMA = Bearish (trend = -1)

    Parameters:
        fast_period: Fast EMA period (default: 9)
        slow_period: Slow EMA period (default: 21)
    """

    name = "ema_cross"
    required_candles = 30

    def _validate_parameters(self) -> None:
        """Validate EMA Cross parameters"""
        fast = self.get_parameter("fast_period", 9)
        slow = self.get_parameter("slow_period", 21)
        if fast >= slow:
            raise ValueError("Fast period must be less than slow period")

    def _calculate_ema(self, values: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(values) < period:
            return []

        multiplier = 2 / (period + 1)
        ema = [sum(values[:period]) / period]  # Start with SMA

        for i in range(period, len(values)):
            ema.append((values[i] - ema[-1]) * multiplier + ema[-1])

        return ema

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """Calculate EMA Cross values"""
        fast_period = self.get_parameter("fast_period", 9)
        slow_period = self.get_parameter("slow_period", 21)

        if len(candles) < slow_period + 2:
            raise ValueError(f"Need at least {slow_period + 2} candles for EMA Cross")

        closes = [float(c.close) for c in candles]

        # Calculate EMAs
        fast_ema_series = self._calculate_ema(closes, fast_period)
        slow_ema_series = self._calculate_ema(closes, slow_period)

        # Get the last values (aligned)
        # Fast EMA has more values, need to align with slow EMA
        offset = slow_period - fast_period

        if len(slow_ema_series) < 2:
            raise ValueError("Not enough data for crossover detection")

        # Current values
        current_fast = fast_ema_series[-1]
        current_slow = slow_ema_series[-1]

        # Previous values for crossover detection
        prev_fast = fast_ema_series[-2]
        prev_slow = slow_ema_series[-2]

        # Determine trend
        # 1 = bullish (fast > slow)
        # -1 = bearish (fast < slow)
        if current_fast > current_slow:
            trend = 1
        elif current_fast < current_slow:
            trend = -1
        else:
            trend = 0

        # Detect crossover
        # 1 = bullish crossover
        # -1 = bearish crossover
        # 0 = no crossover
        if prev_fast <= prev_slow and current_fast > current_slow:
            crossover = 1
        elif prev_fast >= prev_slow and current_fast < current_slow:
            crossover = -1
        else:
            crossover = 0

        # Calculate distance between EMAs (as percentage)
        distance = ((current_fast - current_slow) / current_slow) * 100 if current_slow > 0 else 0

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "fast_ema": Decimal(str(round(current_fast, 8))),
                "slow_ema": Decimal(str(round(current_slow, 8))),
                "trend": Decimal(str(trend)),
                "crossover": Decimal(str(crossover)),
                "distance": Decimal(str(round(distance, 4)))
            }
        )
