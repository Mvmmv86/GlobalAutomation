"""
Stochastic RSI Implementation

O Stochastic RSI combina dois indicadores poderosos:
1. RSI (Relative Strength Index) - mede velocidade e mudanca de movimentos de preco
2. Stochastic Oscillator - aplicado aos valores do RSI

Isso cria um indicador mais sensivel que o RSI padrao, util para
identificar reversoes em condicoes de sobrecompra/sobrevenda.

Formula:
1. Calcular RSI
2. Aplicar formula Stochastic aos valores RSI:
   StochRSI = (RSI - Lowest RSI) / (Highest RSI - Lowest RSI) x 100

Parametros:
- rsi_period: Periodo do RSI (default: 14)
- stoch_period: Periodo do Stochastic aplicado ao RSI (default: 14)
- k_period: Suavizacao %K (default: 3)
- d_period: Suavizacao %D (default: 3)
- overbought: Nivel de sobrecompra (default: 80)
- oversold: Nivel de sobrevenda (default: 20)

Win Rate Documentado: 78%
Fonte: https://www.quantifiedstrategies.com/stochastic-rsi/

Sinais:
- Compra: %K cruza acima de %D saindo de sobrevenda (< 20)
- Venda: %K cruza abaixo de %D saindo de sobrecompra (> 80)
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
import numpy as np

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class StochasticRSICalculator(BaseIndicatorCalculator):
    """
    Stochastic RSI Calculator

    Combina RSI com Stochastic para sinais mais sensiveis de reversao.
    Win Rate esperado: 70-78% quando usado com filtros de tendencia.
    """

    name = "stochastic_rsi"
    required_candles = 100

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters)
        self.rsi_period = int(self.parameters.get("rsi_period", 14))
        self.stoch_period = int(self.parameters.get("stoch_period", 14))
        self.k_period = int(self.parameters.get("k_period", 3))
        self.d_period = int(self.parameters.get("d_period", 3))
        self.overbought = float(self.parameters.get("overbought", 80))
        self.oversold = float(self.parameters.get("oversold", 20))

    def _validate_parameters(self) -> None:
        """Validate parameters"""
        if self.parameters.get("rsi_period", 14) < 2:
            raise ValueError("rsi_period must be >= 2")
        if self.parameters.get("stoch_period", 14) < 2:
            raise ValueError("stoch_period must be >= 2")

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """
        Calculate Stochastic RSI values

        Returns:
            IndicatorResult with keys:
            - k: Current %K value (0-100)
            - d: Current %D value (0-100)
            - rsi: Underlying RSI value
            - signal: 1 (buy), -1 (sell), 0 (neutral)
            - zone: 1 (overbought), -1 (oversold), 0 (neutral)
        """
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles, got {len(candles)}")

        closes = np.array([float(c.close) for c in candles])

        # Step 1: Calculate RSI series
        rsi_values = self._calculate_rsi(closes)

        if len(rsi_values) < self.stoch_period:
            raise ValueError("Not enough RSI values for Stochastic calculation")

        # Step 2: Apply Stochastic formula to RSI values
        stoch_rsi = []
        for i in range(self.stoch_period - 1, len(rsi_values)):
            window = rsi_values[i - self.stoch_period + 1:i + 1]
            min_rsi = np.min(window)
            max_rsi = np.max(window)

            if max_rsi - min_rsi > 0:
                sr = ((rsi_values[i] - min_rsi) / (max_rsi - min_rsi)) * 100
            else:
                sr = 50.0  # Neutral
            stoch_rsi.append(sr)

        if len(stoch_rsi) < self.k_period:
            raise ValueError("Not enough data for %K smoothing")

        # Step 3: Smooth to get %K
        k_values = self._sma(stoch_rsi, self.k_period)

        if len(k_values) < self.d_period:
            raise ValueError("Not enough data for %D calculation")

        # Step 4: Calculate %D (SMA of %K)
        d_values = self._sma(k_values, self.d_period)

        if not k_values or not d_values:
            raise ValueError("Not enough data to calculate Stochastic RSI")

        # Get current and previous values
        k = k_values[-1]
        d = d_values[-1]
        rsi = rsi_values[-1]

        prev_k = k_values[-2] if len(k_values) > 1 else k
        prev_d = d_values[-2] if len(d_values) > 1 else d

        # Determine zone
        zone = 0
        if k > self.overbought:
            zone = 1  # Overbought
        elif k < self.oversold:
            zone = -1  # Oversold

        # Generate signal based on crossovers in extreme zones
        signal = 0

        # Bullish cross: %K crosses above %D, coming from oversold
        # More reliable when recently in oversold zone
        if prev_k <= prev_d and k > d:
            if k < self.oversold + 15 or prev_k < self.oversold:
                signal = 1  # Strong buy signal

        # Bearish cross: %K crosses below %D, coming from overbought
        elif prev_k >= prev_d and k < d:
            if k > self.overbought - 15 or prev_k > self.overbought:
                signal = -1  # Strong sell signal

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "k": Decimal(str(round(k, 2))),
                "d": Decimal(str(round(d, 2))),
                "rsi": Decimal(str(round(rsi, 2))),
                "signal": Decimal(str(signal)),
                "zone": Decimal(str(zone)),
            }
        )

    def _calculate_rsi(self, closes: np.ndarray) -> List[float]:
        """
        Calculate RSI values using Wilder's smoothing method

        This is the standard RSI calculation:
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
        """
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # Initialize arrays
        avg_gain = np.zeros(len(deltas))
        avg_loss = np.zeros(len(deltas))

        # First average is simple average
        if self.rsi_period <= len(gains):
            avg_gain[self.rsi_period - 1] = np.mean(gains[:self.rsi_period])
            avg_loss[self.rsi_period - 1] = np.mean(losses[:self.rsi_period])

        # Subsequent values use Wilder's smoothing (EMA-like)
        for i in range(self.rsi_period, len(deltas)):
            avg_gain[i] = (avg_gain[i-1] * (self.rsi_period - 1) + gains[i]) / self.rsi_period
            avg_loss[i] = (avg_loss[i-1] * (self.rsi_period - 1) + losses[i]) / self.rsi_period

        # Calculate RS and RSI
        # Avoid division by zero
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
        rsi = 100 - (100 / (1 + rs))

        # Return only valid values (after warmup period)
        return list(rsi[self.rsi_period - 1:])

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
        """Calculate Stochastic RSI for entire series"""
        results = []

        for i in range(self.required_candles, len(candles) + 1):
            try:
                result = self.calculate(candles[:i])
                results.append(result)
            except (ValueError, IndexError):
                continue

        return results
