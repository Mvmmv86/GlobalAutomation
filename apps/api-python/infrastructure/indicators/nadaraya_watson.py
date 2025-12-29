"""Nadaraya-Watson Envelope Calculator

Implementation of Gaussian Kernel Regression for price smoothing
with upper and lower bands based on ATR or standard deviation.

Based on the TradingView Nadaraya-Watson Envelope indicator.
"""

import math
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class NadarayaWatsonCalculator(BaseIndicatorCalculator):
    """
    Nadaraya-Watson Envelope Calculator

    Uses Gaussian Kernel Regression to create a smoothed price line
    with upper and lower bands.

    Parameters:
        bandwidth (int): Lookback period for kernel regression (default: 8)
        mult (float): Multiplier for band width (default: 3.0)
        src (str): Source price - 'close', 'hl2', 'hlc3', 'ohlc4' (default: 'close')
        use_atr (bool): Use ATR for bands instead of kernel deviation (default: True)
        atr_period (int): ATR period if use_atr is True (default: 14)

    Output values:
        - value: The smoothed Nadaraya-Watson line
        - upper: Upper band
        - lower: Lower band
        - signal: 1 (bullish), -1 (bearish), 0 (neutral)
    """

    name = "nadaraya_watson"
    required_candles = 50

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters)

        self.bandwidth = int(self.get_parameter("bandwidth", 8))
        self.mult = float(self.get_parameter("mult", 3.0))
        self.src = self.get_parameter("src", "close")
        self.use_atr = self.get_parameter("use_atr", True)
        self.atr_period = int(self.get_parameter("atr_period", 14))

    def _validate_parameters(self) -> None:
        """Validate parameters"""
        if self.get_parameter("bandwidth") is not None:
            bandwidth = int(self.get_parameter("bandwidth"))
            if bandwidth < 1 or bandwidth > 100:
                raise ValueError("bandwidth must be between 1 and 100")

        if self.get_parameter("mult") is not None:
            mult = float(self.get_parameter("mult"))
            if mult <= 0:
                raise ValueError("mult must be positive")

    def _get_source_price(self, candle: Candle) -> float:
        """Get the source price from a candle"""
        if self.src == "close":
            return float(candle.close)
        elif self.src == "hl2":
            return (float(candle.high) + float(candle.low)) / 2
        elif self.src == "hlc3":
            return (float(candle.high) + float(candle.low) + float(candle.close)) / 3
        elif self.src == "ohlc4":
            return (float(candle.open) + float(candle.high) + float(candle.low) + float(candle.close)) / 4
        else:
            return float(candle.close)

    def _gaussian_kernel(self, x: float, bandwidth: float) -> float:
        """Calculate Gaussian kernel weight"""
        return math.exp(-0.5 * (x / bandwidth) ** 2)

    def _calculate_atr(self, candles: List[Candle], period: int) -> float:
        """Calculate Average True Range"""
        if len(candles) < period + 1:
            return 0.0

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

        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0

        return sum(true_ranges[-period:]) / period

    def _calculate_kernel_regression(self, prices: List[float]) -> List[float]:
        """Calculate Nadaraya-Watson kernel regression values"""
        n = len(prices)
        nw_values = []

        for i in range(n):
            weighted_sum = 0.0
            weight_sum = 0.0

            for j in range(n):
                weight = self._gaussian_kernel(i - j, self.bandwidth)
                weighted_sum += weight * prices[j]
                weight_sum += weight

            if weight_sum > 0:
                nw_values.append(weighted_sum / weight_sum)
            else:
                nw_values.append(prices[i])

        return nw_values

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """Calculate Nadaraya-Watson Envelope values

        Args:
            candles: List of OHLCV candles (oldest first)

        Returns:
            IndicatorResult with 'value', 'upper', 'lower', 'signal'
        """
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles, got {len(candles)}")

        prices = [self._get_source_price(c) for c in candles]

        nw_values = self._calculate_kernel_regression(prices)

        current_nw = nw_values[-1]

        if self.use_atr:
            band_width = self._calculate_atr(candles, self.atr_period) * self.mult
        else:
            deviations = [abs(prices[i] - nw_values[i]) for i in range(len(prices))]
            std_dev = (sum(d**2 for d in deviations) / len(deviations)) ** 0.5
            band_width = std_dev * self.mult

        upper = current_nw + band_width
        lower = current_nw - band_width

        current_close = float(candles[-1].close)
        if current_close > upper:
            signal = -1  # Bearish - price above upper band
        elif current_close < lower:
            signal = 1   # Bullish - price below lower band
        else:
            signal = 0   # Neutral

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "value": Decimal(str(round(current_nw, 8))),
                "upper": Decimal(str(round(upper, 8))),
                "lower": Decimal(str(round(lower, 8))),
                "signal": Decimal(str(signal)),
                "band_width": Decimal(str(round(band_width, 8)))
            }
        )
