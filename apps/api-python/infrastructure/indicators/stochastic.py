"""
Stochastic Oscillator Implementation

O Stochastic Oscillator e um indicador de momentum que compara o preco de
fechamento de um ativo com sua faixa de preco durante um determinado periodo.

Formula:
%K = (Close - Lowest Low) / (Highest High - Lowest Low) x 100
%D = SMA(%K, d_period)

Sinais:
- Sobrecompra: %K > 80
- Sobrevenda: %K < 20
- Bullish Cross: %K cruza acima de %D em zona de sobrevenda
- Bearish Cross: %K cruza abaixo de %D em zona de sobrecompra

Parametros:
- k_period: Periodo do %K (default: 14)
- d_period: Periodo do %D (default: 3)
- smooth: Suavizacao do %K (default: 3)
- overbought: Nivel de sobrecompra (default: 80)
- oversold: Nivel de sobrevenda (default: 20)

Uso em estrategias:
- Reversao: Comprar quando %K < 20 e cruza acima de %D
- Reversao: Vender quando %K > 80 e cruza abaixo de %D
- Confirmar tendencia com outros indicadores (RSI, MACD)

Fonte: https://www.quantifiedstrategies.com/stochastic-oscillator/
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
import numpy as np

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class StochasticCalculator(BaseIndicatorCalculator):
    """
    Stochastic Oscillator Calculator

    Calcula %K e %D lines para identificar condicoes de
    sobrecompra/sobrevenda e sinais de reversao.
    """

    name = "stochastic"
    required_candles = 50

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters)
        self.k_period = int(self.parameters.get("k_period", 14))
        self.d_period = int(self.parameters.get("d_period", 3))
        self.smooth = int(self.parameters.get("smooth", 3))
        self.overbought = float(self.parameters.get("overbought", 80))
        self.oversold = float(self.parameters.get("oversold", 20))

    def _validate_parameters(self) -> None:
        """Validate parameters"""
        if self.parameters.get("k_period", 14) < 1:
            raise ValueError("k_period must be >= 1")
        if self.parameters.get("d_period", 3) < 1:
            raise ValueError("d_period must be >= 1")

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """
        Calculate Stochastic %K and %D values

        Returns:
            IndicatorResult with keys:
            - k: Current %K value (0-100)
            - d: Current %D value (0-100)
            - signal: 1 (buy), -1 (sell), 0 (neutral)
            - zone: 1 (overbought), -1 (oversold), 0 (neutral)
        """
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles, got {len(candles)}")

        # Convert to numpy arrays for efficiency
        highs = np.array([float(c.high) for c in candles])
        lows = np.array([float(c.low) for c in candles])
        closes = np.array([float(c.close) for c in candles])

        # Calculate raw %K values
        raw_k = []
        for i in range(self.k_period - 1, len(closes)):
            window_high = highs[i - self.k_period + 1:i + 1]
            window_low = lows[i - self.k_period + 1:i + 1]

            highest = np.max(window_high)
            lowest = np.min(window_low)

            if highest - lowest > 0:
                k = ((closes[i] - lowest) / (highest - lowest)) * 100
            else:
                k = 50.0  # Neutral when range is 0
            raw_k.append(k)

        # Smooth %K
        k_smooth = self._sma(raw_k, self.smooth) if self.smooth > 1 else raw_k

        # Calculate %D (SMA of smoothed %K)
        d_values = self._sma(k_smooth, self.d_period)

        if not k_smooth or not d_values:
            raise ValueError("Not enough data to calculate Stochastic")

        # Get current and previous values for crossover detection
        k = k_smooth[-1]
        d = d_values[-1]

        prev_k = k_smooth[-2] if len(k_smooth) > 1 else k
        prev_d = d_values[-2] if len(d_values) > 1 else d

        # Determine zone
        zone = 0
        if k > self.overbought:
            zone = 1  # Overbought
        elif k < self.oversold:
            zone = -1  # Oversold

        # Generate signal based on crossovers
        signal = 0

        # Bullish cross from oversold zone
        if prev_k <= prev_d and k > d and k < self.oversold + 15:
            signal = 1  # Buy signal

        # Bearish cross from overbought zone
        elif prev_k >= prev_d and k < d and k > self.overbought - 15:
            signal = -1  # Sell signal

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "k": Decimal(str(round(k, 2))),
                "d": Decimal(str(round(d, 2))),
                "signal": Decimal(str(signal)),
                "zone": Decimal(str(zone)),
            }
        )

    def _sma(self, data: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average"""
        if len(data) < period:
            return []

        result = []
        for i in range(period - 1, len(data)):
            window = data[i - period + 1:i + 1]
            result.append(np.mean(window))
        return result

    def calculate_series(self, candles: List[Candle]) -> List[IndicatorResult]:
        """Calculate Stochastic for entire series"""
        results = []

        for i in range(self.required_candles, len(candles) + 1):
            try:
                result = self.calculate(candles[:i])
                results.append(result)
            except (ValueError, IndexError):
                continue

        return results
