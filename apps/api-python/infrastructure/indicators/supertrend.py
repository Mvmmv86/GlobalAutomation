"""
SuperTrend Indicator Implementation

O SuperTrend e um indicador de tendencia que usa ATR (Average True Range)
para definir bandas dinamicas de suporte e resistencia.

Formula:
Upper Band = (High + Low) / 2 + Multiplier x ATR
Lower Band = (High + Low) / 2 - Multiplier x ATR

Logica de Tendencia:
- Bullish: Quando preco fecha acima da Upper Band anterior
- Bearish: Quando preco fecha abaixo da Lower Band anterior
- O SuperTrend "flippa" entre as bandas conforme tendencia muda

Parametros:
- period: Periodo do ATR (default: 10)
- multiplier: Multiplicador do ATR (default: 3.0)

Uso em Estrategias:
- Trend Following: Comprar quando SuperTrend vira bullish, vender quando vira bearish
- Stop Loss Dinamico: Usar valor do SuperTrend como trailing stop
- Filtro de Tendencia: Apenas operar na direcao do SuperTrend

Fonte: https://www.quantifiedstrategies.com/supertrend-indicator-trading-strategy/
Fonte: https://www.luxalgo.com/blog/how-to-use-the-supertrend-indicator-effectively/
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
import numpy as np

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class SuperTrendCalculator(BaseIndicatorCalculator):
    """
    SuperTrend Indicator Calculator

    Calcula o SuperTrend para identificar tendencia e fornecer
    niveis dinamicos de stop loss.
    """

    name = "supertrend"
    required_candles = 50

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters)
        self.period = int(self.parameters.get("period", 10))
        self.multiplier = float(self.parameters.get("multiplier", 3.0))

    def _validate_parameters(self) -> None:
        """Validate parameters"""
        if self.parameters.get("period", 10) < 1:
            raise ValueError("period must be >= 1")
        if self.parameters.get("multiplier", 3.0) <= 0:
            raise ValueError("multiplier must be > 0")

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """
        Calculate SuperTrend value and trend direction

        Returns:
            IndicatorResult with keys:
            - value: Current SuperTrend value (support/resistance level)
            - trend: 1 (bullish), -1 (bearish)
            - upper: Upper band value
            - lower: Lower band value
            - signal: 1 (buy - trend just turned bullish),
                     -1 (sell - trend just turned bearish),
                     0 (no change)
        """
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles, got {len(candles)}")

        # Convert to numpy arrays
        highs = np.array([float(c.high) for c in candles])
        lows = np.array([float(c.low) for c in candles])
        closes = np.array([float(c.close) for c in candles])

        # Calculate ATR
        atr = self._calculate_atr(highs, lows, closes)

        # Calculate HL2 (midpoint)
        hl2 = (highs + lows) / 2

        # Calculate basic bands
        upper_basic = hl2 + (self.multiplier * atr)
        lower_basic = hl2 - (self.multiplier * atr)

        # Initialize arrays for final bands and trend
        n = len(closes)
        upper_band = np.zeros(n)
        lower_band = np.zeros(n)
        supertrend = np.zeros(n)
        trend = np.zeros(n)  # 1 = bullish, -1 = bearish

        # Set initial values
        upper_band[0] = upper_basic[0]
        lower_band[0] = lower_basic[0]
        trend[0] = 1  # Start bullish

        # Calculate SuperTrend with proper band logic
        for i in range(1, n):
            # Upper band calculation
            # If new upper is lower than previous upper OR price closed above previous upper
            if upper_basic[i] < upper_band[i-1] or closes[i-1] > upper_band[i-1]:
                upper_band[i] = upper_basic[i]
            else:
                upper_band[i] = upper_band[i-1]

            # Lower band calculation
            # If new lower is higher than previous lower OR price closed below previous lower
            if lower_basic[i] > lower_band[i-1] or closes[i-1] < lower_band[i-1]:
                lower_band[i] = lower_basic[i]
            else:
                lower_band[i] = lower_band[i-1]

            # Trend direction logic
            if trend[i-1] == 1:  # Was bullish
                if closes[i] < lower_band[i]:
                    trend[i] = -1  # Flip to bearish
                    supertrend[i] = upper_band[i]
                else:
                    trend[i] = 1  # Stay bullish
                    supertrend[i] = lower_band[i]
            else:  # Was bearish
                if closes[i] > upper_band[i]:
                    trend[i] = 1  # Flip to bullish
                    supertrend[i] = lower_band[i]
                else:
                    trend[i] = -1  # Stay bearish
                    supertrend[i] = upper_band[i]

        # Detect trend change signal
        signal = 0
        if len(trend) >= 2:
            if trend[-2] == -1 and trend[-1] == 1:
                signal = 1  # Bullish reversal signal
            elif trend[-2] == 1 and trend[-1] == -1:
                signal = -1  # Bearish reversal signal

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "value": Decimal(str(round(supertrend[-1], 8))),
                "trend": Decimal(str(int(trend[-1]))),
                "upper": Decimal(str(round(upper_band[-1], 8))),
                "lower": Decimal(str(round(lower_band[-1], 8))),
                "signal": Decimal(str(signal)),
            }
        )

    def _calculate_atr(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> np.ndarray:
        """
        Calculate Average True Range (ATR)

        True Range = max of:
        - High - Low (current bar range)
        - |High - Previous Close|
        - |Low - Previous Close|
        """
        n = len(closes)
        tr = np.zeros(n)

        # First TR is just high - low
        tr[0] = highs[0] - lows[0]

        # Calculate True Range for remaining bars
        for i in range(1, n):
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )

        # Calculate ATR using Wilder's smoothing (same as EMA but different formula)
        atr = np.zeros(n)

        # Initial ATR is SMA of first 'period' TRs
        if self.period <= n:
            atr[self.period - 1] = np.mean(tr[:self.period])

        # Subsequent ATRs use Wilder's smoothing
        for i in range(self.period, n):
            atr[i] = (atr[i-1] * (self.period - 1) + tr[i]) / self.period

        return atr

    def calculate_series(self, candles: List[Candle]) -> List[IndicatorResult]:
        """Calculate SuperTrend for entire series"""
        results = []

        for i in range(self.required_candles, len(candles) + 1):
            try:
                result = self.calculate(candles[:i])
                results.append(result)
            except (ValueError, IndexError):
                continue

        return results
