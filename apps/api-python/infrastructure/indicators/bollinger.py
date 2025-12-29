"""Bollinger Bands Calculator"""

from decimal import Decimal
from typing import Dict, List, Any
import math

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class BollingerCalculator(BaseIndicatorCalculator):
    """
    Bollinger Bands Calculator

    Volatility indicator with three lines:
    - Middle Band: SMA of close prices
    - Upper Band: Middle + (stddev * multiplier)
    - Lower Band: Middle - (stddev * multiplier)

    Additional metrics:
    - Bandwidth: (Upper - Lower) / Middle * 100 (volatility measure)
    - %B: (Close - Lower) / (Upper - Lower) (position within bands)

    Parameters:
        period: SMA period (default: 20)
        stddev: Standard deviation multiplier (default: 2.0)
    """

    name = "bollinger"
    required_candles = 25

    def _validate_parameters(self) -> None:
        """Validate Bollinger parameters"""
        period = self.get_parameter("period", 20)
        stddev = self.get_parameter("stddev", 2.0)
        if period < 2:
            raise ValueError("Bollinger period must be >= 2")
        if stddev <= 0:
            raise ValueError("Standard deviation must be > 0")

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """Calculate Bollinger Bands values"""
        period = self.get_parameter("period", 20)
        stddev_mult = self.get_parameter("stddev", 2.0)

        if len(candles) < period:
            raise ValueError(f"Need at least {period} candles for Bollinger Bands")

        closes = [float(c.close) for c in candles[-period:]]
        current_close = closes[-1]

        # Calculate SMA (middle band)
        sma = sum(closes) / period

        # Calculate standard deviation
        variance = sum((c - sma) ** 2 for c in closes) / period
        stddev = math.sqrt(variance)

        # Calculate bands
        upper = sma + (stddev * stddev_mult)
        lower = sma - (stddev * stddev_mult)

        # Calculate bandwidth (volatility indicator)
        # Low bandwidth = squeeze (low volatility, potential breakout)
        # High bandwidth = high volatility
        bandwidth = ((upper - lower) / sma) * 100 if sma > 0 else 0

        # Calculate %B (position within bands)
        # < 0: Below lower band
        # > 1: Above upper band
        # 0.5: At middle band
        band_range = upper - lower
        if band_range > 0:
            percent_b = (current_close - lower) / band_range
        else:
            percent_b = 0.5

        # Determine signal based on %B
        # 1 = near lower band (potential buy)
        # -1 = near upper band (potential sell)
        # 0 = neutral
        if percent_b < 0.2:
            signal = 1  # Oversold
        elif percent_b > 0.8:
            signal = -1  # Overbought
        else:
            signal = 0  # Neutral

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "upper": Decimal(str(round(upper, 8))),
                "middle": Decimal(str(round(sma, 8))),
                "lower": Decimal(str(round(lower, 8))),
                "bandwidth": Decimal(str(round(bandwidth, 4))),
                "percent_b": Decimal(str(round(percent_b, 4))),
                "signal": Decimal(str(signal))
            }
        )
