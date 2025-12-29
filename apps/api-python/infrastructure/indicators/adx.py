"""
ADX (Average Directional Index) Implementation

O ADX mede a forca de uma tendencia, independente da direcao.
E composto por tres linhas:
- ADX: Mede a forca da tendencia (0-100)
- +DI: Movimento direcional positivo
- -DI: Movimento direcional negativo

Interpretacao:
- ADX < 20: Tendencia fraca ou lateral
- ADX 20-40: Tendencia moderada
- ADX > 40: Tendencia forte
- ADX > 60: Tendencia muito forte

Sinais:
- Bullish: +DI cruza acima de -DI com ADX > 20
- Bearish: -DI cruza acima de +DI com ADX > 20
- Trend Strength Filter: Apenas operar quando ADX > 25

Parametros:
- period: Periodo para calculo (default: 14)
- trend_threshold: Nivel minimo de ADX para considerar tendencia (default: 25)

Uso em Estrategias:
- Filtro de tendencia: Confirmar que mercado esta em tendencia antes de entrar
- Evitar whipsaws: Nao operar em mercados laterais (ADX < 20)
- Timing de entrada: Entrar quando +DI/-DI cruza com ADX crescendo

Fonte: J. Welles Wilder Jr. (criador do RSI tambem)
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
import numpy as np

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class ADXCalculator(BaseIndicatorCalculator):
    """
    ADX (Average Directional Index) Calculator

    Mede a forca da tendencia para filtrar sinais em mercados laterais.
    """

    name = "adx"
    required_candles = 50

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters)
        self.period = int(self.parameters.get("period", 14))
        self.trend_threshold = float(self.parameters.get("trend_threshold", 25))

    def _validate_parameters(self) -> None:
        """Validate parameters"""
        if self.parameters.get("period", 14) < 1:
            raise ValueError("period must be >= 1")

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """
        Calculate ADX, +DI, and -DI values

        Returns:
            IndicatorResult with keys:
            - adx: ADX value (0-100)
            - plus_di: +DI value (0-100)
            - minus_di: -DI value (0-100)
            - trend_strength: 0 (weak), 1 (moderate), 2 (strong)
            - signal: 1 (bullish cross), -1 (bearish cross), 0 (neutral)
        """
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles, got {len(candles)}")

        # Convert to numpy arrays
        highs = np.array([float(c.high) for c in candles])
        lows = np.array([float(c.low) for c in candles])
        closes = np.array([float(c.close) for c in candles])

        n = len(closes)

        # Calculate True Range
        tr = np.zeros(n)
        tr[0] = highs[0] - lows[0]
        for i in range(1, n):
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )

        # Calculate Directional Movement (+DM and -DM)
        plus_dm = np.zeros(n)
        minus_dm = np.zeros(n)

        for i in range(1, n):
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]

            if up_move > down_move and up_move > 0:
                plus_dm[i] = up_move
            else:
                plus_dm[i] = 0

            if down_move > up_move and down_move > 0:
                minus_dm[i] = down_move
            else:
                minus_dm[i] = 0

        # Smooth TR, +DM, -DM using Wilder's smoothing
        smoothed_tr = self._wilder_smooth(tr, self.period)
        smoothed_plus_dm = self._wilder_smooth(plus_dm, self.period)
        smoothed_minus_dm = self._wilder_smooth(minus_dm, self.period)

        # Calculate +DI and -DI
        plus_di = np.zeros(n)
        minus_di = np.zeros(n)

        for i in range(n):
            if smoothed_tr[i] > 0:
                plus_di[i] = (smoothed_plus_dm[i] / smoothed_tr[i]) * 100
                minus_di[i] = (smoothed_minus_dm[i] / smoothed_tr[i]) * 100

        # Calculate DX (Directional Index)
        dx = np.zeros(n)
        for i in range(n):
            di_sum = plus_di[i] + minus_di[i]
            if di_sum > 0:
                dx[i] = abs(plus_di[i] - minus_di[i]) / di_sum * 100

        # Calculate ADX (smoothed DX)
        adx = self._wilder_smooth(dx, self.period)

        # Get current values
        current_adx = adx[-1]
        current_plus_di = plus_di[-1]
        current_minus_di = minus_di[-1]

        prev_plus_di = plus_di[-2] if len(plus_di) > 1 else current_plus_di
        prev_minus_di = minus_di[-2] if len(minus_di) > 1 else current_minus_di

        # Determine trend strength
        if current_adx < 20:
            trend_strength = 0  # Weak/No trend
        elif current_adx < 40:
            trend_strength = 1  # Moderate trend
        else:
            trend_strength = 2  # Strong trend

        # Generate signal based on DI crossovers
        signal = 0

        # Bullish: +DI crosses above -DI with ADX showing trend
        if (prev_plus_di <= prev_minus_di and
            current_plus_di > current_minus_di and
            current_adx >= self.trend_threshold):
            signal = 1

        # Bearish: -DI crosses above +DI with ADX showing trend
        elif (prev_minus_di <= prev_plus_di and
              current_minus_di > current_plus_di and
              current_adx >= self.trend_threshold):
            signal = -1

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "adx": Decimal(str(round(current_adx, 2))),
                "plus_di": Decimal(str(round(current_plus_di, 2))),
                "minus_di": Decimal(str(round(current_minus_di, 2))),
                "trend_strength": Decimal(str(trend_strength)),
                "signal": Decimal(str(signal)),
            }
        )

    def _wilder_smooth(self, data: np.ndarray, period: int) -> np.ndarray:
        """
        Apply Wilder's smoothing method

        This is similar to EMA but with a different multiplier:
        Wilder Smoothing = Previous Value + (Current Value - Previous Value) / Period
        """
        result = np.zeros(len(data))

        # First value is SMA
        if period <= len(data):
            result[period - 1] = np.mean(data[:period])

        # Apply Wilder's smoothing
        for i in range(period, len(data)):
            result[i] = result[i-1] + (data[i] - result[i-1]) / period

        return result

    def calculate_series(self, candles: List[Candle]) -> List[IndicatorResult]:
        """Calculate ADX for entire series"""
        results = []

        for i in range(self.required_candles, len(candles) + 1):
            try:
                result = self.calculate(candles[:i])
                results.append(result)
            except (ValueError, IndexError):
                continue

        return results
