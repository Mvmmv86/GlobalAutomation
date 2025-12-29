"""EMA (Exponential Moving Average) Calculator"""

from decimal import Decimal
from typing import Dict, List, Any

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class EMACalculator(BaseIndicatorCalculator):
    """
    EMA (Exponential Moving Average) Calculator

    Simple EMA indicator for trend identification.

    Parameters:
        period: EMA period (default: 20)
    """

    name = "ema"
    required_candles = 25

    def _validate_parameters(self) -> None:
        """Validate EMA parameters"""
        period = self.get_parameter("period", 20)
        if period < 2:
            raise ValueError("EMA period must be >= 2")

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """Calculate EMA value"""
        period = self.get_parameter("period", 20)

        if len(candles) < period:
            raise ValueError(f"Need at least {period} candles for EMA")

        closes = [float(c.close) for c in candles]
        current_close = closes[-1]

        # Calculate EMA
        multiplier = 2 / (period + 1)
        ema = sum(closes[:period]) / period  # Start with SMA

        for i in range(period, len(closes)):
            ema = (closes[i] - ema) * multiplier + ema

        # Determine trend
        # 1 = price above EMA (bullish)
        # -1 = price below EMA (bearish)
        if current_close > ema:
            trend = 1
        elif current_close < ema:
            trend = -1
        else:
            trend = 0

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "value": Decimal(str(round(ema, 8))),
                "trend": Decimal(str(trend))
            }
        )
