"""TPO (Time Price Opportunity) / Market Profile Calculator

Implementation of Market Profile analysis showing price distribution
over time with POC (Point of Control), Value Area High/Low.

Based on the TradingView TPO Market Profile indicator.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class TPOCalculator(BaseIndicatorCalculator):
    """
    TPO (Time Price Opportunity) Market Profile Calculator

    Calculates the distribution of price over time periods and identifies
    key levels: POC (Point of Control), VAH (Value Area High), VAL (Value Area Low).

    Parameters:
        period (int): Number of candles to analyze (default: 24)
        tick_size (float): Price tick size for grouping (default: auto-calculated)
        value_area_percent (float): Value Area percentage (default: 70%)
        row_size (int): Number of price rows/bins (default: 24)

    Output values:
        - poc: Point of Control (price level with most time spent)
        - vah: Value Area High
        - val: Value Area Low
        - signal: 1 (price below VAL), -1 (price above VAH), 0 (within VA)
    """

    name = "tpo"
    required_candles = 24

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters)

        self.period = int(self.get_parameter("period", 24))
        self.tick_size = self.get_parameter("tick_size", None)  # Auto-calculate if None
        self.value_area_percent = float(self.get_parameter("value_area_percent", 70.0))
        self.row_size = int(self.get_parameter("row_size", 24))

        self.required_candles = max(self.period, 24)

    def _validate_parameters(self) -> None:
        """Validate parameters"""
        if self.get_parameter("period") is not None:
            period = int(self.get_parameter("period"))
            if period < 5 or period > 500:
                raise ValueError("period must be between 5 and 500")

        if self.get_parameter("value_area_percent") is not None:
            va_percent = float(self.get_parameter("value_area_percent"))
            if va_percent < 50 or va_percent > 95:
                raise ValueError("value_area_percent must be between 50 and 95")

    def _calculate_tick_size(self, candles: List[Candle]) -> float:
        """Auto-calculate appropriate tick size based on price range"""
        prices = [float(c.close) for c in candles]
        price_range = max(prices) - min(prices)

        if price_range == 0:
            return float(prices[0]) * 0.001

        tick_size = price_range / self.row_size

        magnitude = 10 ** (len(str(int(tick_size))) - 1)
        tick_size = round(tick_size / magnitude) * magnitude

        return max(tick_size, 0.00000001)

    def _build_tpo_profile(self, candles: List[Candle], tick_size: float) -> Dict[float, int]:
        """Build TPO profile - count time at each price level"""
        profile: Dict[float, int] = defaultdict(int)

        for candle in candles:
            low = float(candle.low)
            high = float(candle.high)

            price_level = (low // tick_size) * tick_size

            while price_level <= high:
                profile[round(price_level, 8)] += 1
                price_level += tick_size

        return dict(profile)

    def _find_poc(self, profile: Dict[float, int]) -> float:
        """Find Point of Control (price with maximum TPO count)"""
        if not profile:
            return 0.0

        max_count = max(profile.values())
        poc_levels = [price for price, count in profile.items() if count == max_count]

        return sum(poc_levels) / len(poc_levels)

    def _calculate_value_area(
        self,
        profile: Dict[float, int],
        poc: float,
        tick_size: float
    ) -> Tuple[float, float]:
        """Calculate Value Area High and Low

        The Value Area contains X% of all TPO counts, centered on POC.
        """
        if not profile:
            return 0.0, 0.0

        total_tpo = sum(profile.values())
        target_tpo = int(total_tpo * (self.value_area_percent / 100))

        sorted_prices = sorted(profile.keys())
        if not sorted_prices:
            return poc, poc

        poc_index = min(range(len(sorted_prices)),
                       key=lambda i: abs(sorted_prices[i] - poc))

        va_low_idx = poc_index
        va_high_idx = poc_index
        current_tpo = profile.get(sorted_prices[poc_index], 0)

        while current_tpo < target_tpo and (va_low_idx > 0 or va_high_idx < len(sorted_prices) - 1):
            expand_up = False
            expand_down = False

            if va_low_idx > 0 and va_high_idx < len(sorted_prices) - 1:
                up_tpo = profile.get(sorted_prices[va_high_idx + 1], 0)
                down_tpo = profile.get(sorted_prices[va_low_idx - 1], 0)

                if up_tpo >= down_tpo:
                    expand_up = True
                else:
                    expand_down = True
            elif va_high_idx < len(sorted_prices) - 1:
                expand_up = True
            elif va_low_idx > 0:
                expand_down = True
            else:
                break

            if expand_up:
                va_high_idx += 1
                current_tpo += profile.get(sorted_prices[va_high_idx], 0)
            elif expand_down:
                va_low_idx -= 1
                current_tpo += profile.get(sorted_prices[va_low_idx], 0)

        val = sorted_prices[va_low_idx]
        vah = sorted_prices[va_high_idx]

        return vah, val

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """Calculate TPO Market Profile values

        Args:
            candles: List of OHLCV candles (oldest first)

        Returns:
            IndicatorResult with 'poc', 'vah', 'val', 'signal'
        """
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles, got {len(candles)}")

        analysis_candles = candles[-self.period:]

        tick_size = self.tick_size
        if tick_size is None:
            tick_size = self._calculate_tick_size(analysis_candles)

        profile = self._build_tpo_profile(analysis_candles, tick_size)

        poc = self._find_poc(profile)
        vah, val = self._calculate_value_area(profile, poc, tick_size)

        current_close = float(candles[-1].close)
        if current_close > vah:
            signal = -1  # Bearish - price above Value Area
        elif current_close < val:
            signal = 1   # Bullish - price below Value Area
        else:
            signal = 0   # Neutral - within Value Area

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "poc": Decimal(str(round(poc, 8))),
                "vah": Decimal(str(round(vah, 8))),
                "val": Decimal(str(round(val, 8))),
                "signal": Decimal(str(signal)),
                "tick_size": Decimal(str(tick_size))
            }
        )

    def calculate_with_profile(self, candles: List[Candle]) -> Tuple[IndicatorResult, Dict[float, int]]:
        """Calculate TPO values and return the full profile for visualization

        Args:
            candles: List of OHLCV candles (oldest first)

        Returns:
            Tuple of (IndicatorResult, profile dictionary)
        """
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles, got {len(candles)}")

        analysis_candles = candles[-self.period:]

        tick_size = self.tick_size
        if tick_size is None:
            tick_size = self._calculate_tick_size(analysis_candles)

        profile = self._build_tpo_profile(analysis_candles, tick_size)

        poc = self._find_poc(profile)
        vah, val = self._calculate_value_area(profile, poc, tick_size)

        current_close = float(candles[-1].close)
        if current_close > vah:
            signal = -1
        elif current_close < val:
            signal = 1
        else:
            signal = 0

        result = IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "poc": Decimal(str(round(poc, 8))),
                "vah": Decimal(str(round(vah, 8))),
                "val": Decimal(str(round(val, 8))),
                "signal": Decimal(str(signal)),
                "tick_size": Decimal(str(tick_size))
            }
        )

        return result, profile
