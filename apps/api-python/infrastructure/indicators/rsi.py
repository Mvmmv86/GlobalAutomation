"""RSI (Relative Strength Index) Calculator"""

from decimal import Decimal
from typing import Dict, List, Any

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class RSICalculator(BaseIndicatorCalculator):
    """
    RSI (Relative Strength Index) Calculator

    Measures momentum by comparing recent gains to recent losses.
    Values range from 0-100:
    - Above 70: Overbought
    - Below 30: Oversold

    Parameters:
        period: RSI period (default: 14)
        overbought: Overbought threshold (default: 70)
        oversold: Oversold threshold (default: 30)
    """

    name = "rsi"
    required_candles = 20  # Need extra candles for warm-up

    def _validate_parameters(self) -> None:
        """Validate RSI parameters"""
        period = self.get_parameter("period", 14)
        if period < 2:
            raise ValueError("RSI period must be >= 2")

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """Calculate RSI value"""
        period = self.get_parameter("period", 14)
        overbought = self.get_parameter("overbought", 70)
        oversold = self.get_parameter("oversold", 30)

        if len(candles) < period + 1:
            raise ValueError(f"Need at least {period + 1} candles for RSI")

        # Calculate price changes
        closes = [float(c.close) for c in candles]
        changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]

        # Separate gains and losses
        gains = [max(0, c) for c in changes]
        losses = [abs(min(0, c)) for c in changes]

        # Calculate initial average (SMA)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Calculate smoothed averages (EMA-like)
        for i in range(period, len(changes)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        # Calculate RSI
        if avg_loss == 0:
            rsi_value = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_value = 100 - (100 / (1 + rs))

        # Determine signal
        # 1 = oversold (buy signal), -1 = overbought (sell signal), 0 = neutral
        if rsi_value <= oversold:
            signal = 1
        elif rsi_value >= overbought:
            signal = -1
        else:
            signal = 0

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "value": Decimal(str(round(rsi_value, 2))),
                "overbought": Decimal(str(overbought)),
                "oversold": Decimal(str(oversold)),
                "signal": Decimal(str(signal))
            }
        )
