"""
On-Balance Volume (OBV) Indicator Implementation

O OBV e um indicador de momentum que usa fluxo de volume para prever
mudancas no preco. Desenvolvido por Joseph Granville nos anos 1960.

Formula:
- Se close > close anterior: OBV = OBV anterior + Volume
- Se close < close anterior: OBV = OBV anterior - Volume
- Se close = close anterior: OBV = OBV anterior

Logica:
- Volume precede o preco
- OBV subindo = acumulacao (compra)
- OBV caindo = distribuicao (venda)
- Divergencia OBV/Preco = possivel reversao

Sinais:
- OBV acima da SMA(OBV) = bullish
- OBV abaixo da SMA(OBV) = bearish
- Divergencia bullish: Preco faz novas minimas, OBV nao
- Divergencia bearish: Preco faz novas maximas, OBV nao

Parametros:
- sma_period: Periodo da SMA do OBV (default: 20)
- signal_period: Periodo para detectar divergencias (default: 14)

Uso em Estrategias:
- Confirmacao de tendencia: OBV confirmando direcao do preco
- Deteccao de reversao: Divergencias OBV/Preco
- Breakout: OBV rompendo maximas/minimas antes do preco

Fonte: https://www.investopedia.com/terms/o/onbalancevolume.asp
Fonte: https://school.stockcharts.com/doku.php?id=technical_indicators:on_balance_volume_obv
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
import numpy as np

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class OBVCalculator(BaseIndicatorCalculator):
    """
    On-Balance Volume (OBV) Indicator Calculator

    Calcula o OBV e sua media movel para identificar
    acumulacao/distribuicao e confirmar tendencias.

    Uso recomendado:
    - Confirmacao de breakouts
    - Deteccao de divergencias
    - Filtro de volume para outras estrategias
    """

    name = "obv"
    required_candles = 50

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters)
        self.sma_period = int(self.parameters.get("sma_period", 20))
        self.signal_period = int(self.parameters.get("signal_period", 14))

    def _validate_parameters(self) -> None:
        """Validate parameters"""
        if self.parameters.get("sma_period", 20) < 1:
            raise ValueError("sma_period must be >= 1")
        if self.parameters.get("signal_period", 14) < 1:
            raise ValueError("signal_period must be >= 1")

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """
        Calculate OBV value and signals

        Returns:
            IndicatorResult with keys:
            - obv: Current OBV value
            - obv_sma: SMA of OBV
            - obv_normalized: OBV normalized (0-100 scale over signal_period)
            - trend: 1 (OBV > SMA = bullish), -1 (OBV < SMA = bearish)
            - divergence: 1 (bullish divergence), -1 (bearish divergence), 0 (none)
            - signal: 1 (buy), -1 (sell), 0 (neutral)
        """
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles, got {len(candles)}")

        # Convert to numpy arrays
        closes = np.array([float(c.close) for c in candles])
        volumes = np.array([float(c.volume) for c in candles])

        n = len(closes)

        # Calculate OBV
        obv = np.zeros(n)
        obv[0] = volumes[0]

        for i in range(1, n):
            if closes[i] > closes[i - 1]:
                obv[i] = obv[i - 1] + volumes[i]
            elif closes[i] < closes[i - 1]:
                obv[i] = obv[i - 1] - volumes[i]
            else:
                obv[i] = obv[i - 1]

        # Calculate SMA of OBV
        obv_sma = np.zeros(n)
        for i in range(self.sma_period - 1, n):
            obv_sma[i] = np.mean(obv[i - self.sma_period + 1:i + 1])

        # Normalize OBV to 0-100 scale over signal period
        obv_normalized = 50.0  # Default neutral
        if n >= self.signal_period:
            recent_obv = obv[-self.signal_period:]
            obv_min = np.min(recent_obv)
            obv_max = np.max(recent_obv)
            if obv_max != obv_min:
                obv_normalized = 100 * (obv[-1] - obv_min) / (obv_max - obv_min)

        # Current values
        current_obv = obv[-1]
        current_sma = obv_sma[-1]

        # Determine trend
        trend = 1 if current_obv > current_sma else -1

        # Detect divergence
        divergence = self._detect_divergence(closes, obv)

        # OBV rate of change (momentum)
        obv_roc = 0.0
        if n >= 5 and obv[-5] != 0:
            obv_roc = ((obv[-1] - obv[-5]) / abs(obv[-5])) * 100

        # Generate signal
        signal = 0

        # Strong signal: trend + divergence
        if trend == 1 and divergence == 1:
            signal = 1  # Strong buy
        elif trend == -1 and divergence == -1:
            signal = -1  # Strong sell
        # Medium signal: OBV crossing SMA
        elif len(obv_sma) >= 2:
            prev_obv = obv[-2]
            prev_sma = obv_sma[-2]
            # Bullish cross
            if prev_obv <= prev_sma and current_obv > current_sma:
                signal = 1
            # Bearish cross
            elif prev_obv >= prev_sma and current_obv < current_sma:
                signal = -1

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "obv": Decimal(str(round(current_obv, 2))),
                "obv_sma": Decimal(str(round(current_sma, 2))),
                "obv_normalized": Decimal(str(round(obv_normalized, 2))),
                "obv_roc": Decimal(str(round(obv_roc, 4))),
                "trend": Decimal(str(int(trend))),
                "divergence": Decimal(str(int(divergence))),
                "signal": Decimal(str(signal)),
            }
        )

    def _detect_divergence(self, closes: np.ndarray, obv: np.ndarray) -> int:
        """
        Detect bullish or bearish divergence

        Returns:
            1 = bullish divergence (price lower low, OBV higher low)
            -1 = bearish divergence (price higher high, OBV lower high)
            0 = no divergence
        """
        period = self.signal_period

        if len(closes) < period * 2:
            return 0

        # Recent and previous periods
        recent_closes = closes[-period:]
        prev_closes = closes[-period * 2:-period]
        recent_obv = obv[-period:]
        prev_obv = obv[-period * 2:-period]

        # Find lows and highs
        recent_close_low = np.min(recent_closes)
        prev_close_low = np.min(prev_closes)
        recent_obv_low = np.min(recent_obv)
        prev_obv_low = np.min(prev_obv)

        recent_close_high = np.max(recent_closes)
        prev_close_high = np.max(prev_closes)
        recent_obv_high = np.max(recent_obv)
        prev_obv_high = np.max(prev_obv)

        # Bullish divergence: Price makes lower low, OBV makes higher low
        if recent_close_low < prev_close_low and recent_obv_low > prev_obv_low:
            return 1

        # Bearish divergence: Price makes higher high, OBV makes lower high
        if recent_close_high > prev_close_high and recent_obv_high < prev_obv_high:
            return -1

        return 0

    def calculate_series(self, candles: List[Candle]) -> List[IndicatorResult]:
        """Calculate OBV for entire series"""
        results = []

        for i in range(self.required_candles, len(candles) + 1):
            try:
                result = self.calculate(candles[:i])
                results.append(result)
            except (ValueError, IndexError):
                continue

        return results
