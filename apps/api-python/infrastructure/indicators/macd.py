"""MACD (Moving Average Convergence Divergence) Calculator"""

from decimal import Decimal
from typing import Dict, List, Any

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class MACDCalculator(BaseIndicatorCalculator):
    """
    MACD (Moving Average Convergence Divergence) Calculator

    Trend-following momentum indicator showing relationship between two EMAs.

    Components:
    - MACD Line: Fast EMA - Slow EMA
    - Signal Line: EMA of MACD Line
    - Histogram: MACD Line - Signal Line

    Parameters:
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line period (default: 9)
    """

    name = "macd"
    required_candles = 35  # Need enough for slow EMA + signal

    def _validate_parameters(self) -> None:
        """Validate MACD parameters"""
        fast = self.get_parameter("fast", 12)
        slow = self.get_parameter("slow", 26)
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
        """Calculate MACD values"""
        fast_period = self.get_parameter("fast", 12)
        slow_period = self.get_parameter("slow", 26)
        signal_period = self.get_parameter("signal", 9)

        min_candles = slow_period + signal_period
        if len(candles) < min_candles:
            raise ValueError(f"Need at least {min_candles} candles for MACD")

        closes = [float(c.close) for c in candles]

        # Calculate EMAs
        fast_ema = self._calculate_ema(closes, fast_period)
        slow_ema = self._calculate_ema(closes, slow_period)

        # Align EMAs (slow EMA starts later)
        offset = slow_period - fast_period
        aligned_fast = fast_ema[offset:]

        # Calculate MACD line
        macd_line = [f - s for f, s in zip(aligned_fast, slow_ema)]

        # Calculate Signal line (EMA of MACD)
        if len(macd_line) < signal_period:
            raise ValueError("Not enough data for signal line")

        signal_line = self._calculate_ema(macd_line, signal_period)

        # Current values
        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        current_histogram = current_macd - current_signal

        # Previous values for crossover detection
        if len(macd_line) >= 2 and len(signal_line) >= 2:
            prev_macd = macd_line[-2]
            prev_signal = signal_line[-2]

            # Detect crossover
            # 1 = bullish crossover (MACD crosses above signal)
            # -1 = bearish crossover (MACD crosses below signal)
            # 0 = no crossover
            if prev_macd <= prev_signal and current_macd > current_signal:
                crossover = 1
            elif prev_macd >= prev_signal and current_macd < current_signal:
                crossover = -1
            else:
                crossover = 0
        else:
            crossover = 0

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "macd": Decimal(str(round(current_macd, 8))),
                "signal_line": Decimal(str(round(current_signal, 8))),
                "histogram": Decimal(str(round(current_histogram, 8))),
                "crossover": Decimal(str(crossover))
            }
        )
