"""ATR (Average True Range) Calculator"""

from decimal import Decimal
from typing import Dict, List, Any

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class ATRCalculator(BaseIndicatorCalculator):
    """
    ATR (Average True Range) Calculator

    Volatility indicator measuring average range of price movement.

    True Range = max(high - low, |high - prev_close|, |low - prev_close|)
    ATR = Smoothed average of True Range

    Parameters:
        period: ATR period (default: 14)
    """

    name = "atr"
    required_candles = 20

    def _validate_parameters(self) -> None:
        """Validate ATR parameters"""
        period = self.get_parameter("period", 14)
        if period < 2:
            raise ValueError("ATR period must be >= 2")

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """Calculate ATR value"""
        period = self.get_parameter("period", 14)

        if len(candles) < period + 1:
            raise ValueError(f"Need at least {period + 1} candles for ATR")

        # Calculate True Ranges
        true_ranges = []
        for i in range(1, len(candles)):
            high = float(candles[i].high)
            low = float(candles[i].low)
            prev_close = float(candles[i-1].close)

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)

        # Calculate initial ATR (SMA of first N true ranges)
        atr = sum(true_ranges[:period]) / period

        # Apply smoothing (Wilder's method)
        for i in range(period, len(true_ranges)):
            atr = (atr * (period - 1) + true_ranges[i]) / period

        # Calculate ATR as percentage of current close
        current_close = float(candles[-1].close)
        atr_percent = (atr / current_close) * 100 if current_close > 0 else 0

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "value": Decimal(str(round(atr, 8))),
                "percent": Decimal(str(round(atr_percent, 4)))
            }
        )
