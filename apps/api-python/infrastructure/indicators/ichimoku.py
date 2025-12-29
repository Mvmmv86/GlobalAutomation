"""
Ichimoku Cloud Indicator Implementation

O Ichimoku Kinko Hyo ("one glance equilibrium chart") e um indicador japones
que fornece suporte/resistencia, direcao de tendencia e momentum em um unico grafico.

Componentes:
- Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
- Kijun-sen (Base Line): (26-period high + 26-period low) / 2
- Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, plotado 26 periodos a frente
- Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, plotado 26 periodos a frente
- Chikou Span (Lagging Span): Close atual, plotado 26 periodos atras

Cloud (Kumo):
- Area entre Senkou Span A e B
- Cloud verde: Span A > Span B (bullish)
- Cloud vermelha: Span A < Span B (bearish)

Sinais:
- Bullish: Preco acima do cloud, Tenkan > Kijun
- Bearish: Preco abaixo do cloud, Tenkan < Kijun
- Kumo Breakout: Preco cruzando o cloud

Parametros Crypto (24/7 market):
- tenkan_period: 20 (default: 9)
- kijun_period: 60 (default: 26)
- senkou_b_period: 120 (default: 52)
- displacement: 30 (default: 26)

Fonte: https://www.investopedia.com/terms/i/ichimoku-cloud.asp
Fonte: https://quantpedia.com/strategies/ichimoku-cloud-trading-strategy/
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
import numpy as np

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class IchimokuCalculator(BaseIndicatorCalculator):
    """
    Ichimoku Cloud Indicator Calculator

    Calcula todos os componentes do Ichimoku Cloud para identificar
    tendencia, suporte/resistencia e sinais de entrada/saida.

    Performance validada:
    - CAGR Bitcoin: 78.05% (vs Buy-Hold 59.8%)
    - Sharpe Ratio: 1.25
    - Win Rate: 40-55% (trend following)
    - Reduz drawdown em 50%+
    """

    name = "ichimoku"
    required_candles = 120  # Need enough for Senkou Span B calculation

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters)
        # Default parameters - crypto-optimized (24/7 market)
        # Traditional: 9, 26, 52, 26
        # Crypto: 20, 60, 120, 30
        self.tenkan_period = int(self.parameters.get("tenkan_period", 20))
        self.kijun_period = int(self.parameters.get("kijun_period", 60))
        self.senkou_b_period = int(self.parameters.get("senkou_b_period", 120))
        self.displacement = int(self.parameters.get("displacement", 30))

    def _validate_parameters(self) -> None:
        """Validate parameters"""
        if self.parameters.get("tenkan_period", 20) < 1:
            raise ValueError("tenkan_period must be >= 1")
        if self.parameters.get("kijun_period", 60) < 1:
            raise ValueError("kijun_period must be >= 1")
        if self.parameters.get("senkou_b_period", 120) < 1:
            raise ValueError("senkou_b_period must be >= 1")
        if self.parameters.get("displacement", 30) < 1:
            raise ValueError("displacement must be >= 1")

    def _donchian_channel(self, highs: np.ndarray, lows: np.ndarray, period: int) -> np.ndarray:
        """
        Calculate Donchian Channel midline (used for Ichimoku lines)

        Returns (period-high + period-low) / 2 for each point
        """
        n = len(highs)
        result = np.zeros(n)

        for i in range(period - 1, n):
            period_high = np.max(highs[i - period + 1:i + 1])
            period_low = np.min(lows[i - period + 1:i + 1])
            result[i] = (period_high + period_low) / 2

        return result

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """
        Calculate Ichimoku Cloud values and signals

        Returns:
            IndicatorResult with keys:
            - tenkan: Tenkan-sen (Conversion Line)
            - kijun: Kijun-sen (Base Line)
            - senkou_a: Senkou Span A (current, not displaced)
            - senkou_b: Senkou Span B (current, not displaced)
            - chikou: Chikou Span (current close)
            - cloud_top: Upper edge of cloud
            - cloud_bottom: Lower edge of cloud
            - trend: 1 (bullish - price above cloud), -1 (bearish - price below cloud), 0 (in cloud)
            - tk_cross: 1 (Tenkan crossed above Kijun), -1 (below), 0 (no cross)
            - signal: 1 (buy), -1 (sell), 0 (neutral)
        """
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles, got {len(candles)}")

        # Convert to numpy arrays
        highs = np.array([float(c.high) for c in candles])
        lows = np.array([float(c.low) for c in candles])
        closes = np.array([float(c.close) for c in candles])

        n = len(closes)

        # Calculate Tenkan-sen (Conversion Line)
        tenkan = self._donchian_channel(highs, lows, self.tenkan_period)

        # Calculate Kijun-sen (Base Line)
        kijun = self._donchian_channel(highs, lows, self.kijun_period)

        # Calculate Senkou Span A: (Tenkan + Kijun) / 2
        # In real charting, this is plotted 'displacement' periods ahead
        # For current analysis, we use the current value
        senkou_a = (tenkan + kijun) / 2

        # Calculate Senkou Span B
        senkou_b = self._donchian_channel(highs, lows, self.senkou_b_period)

        # Chikou Span is just the current close (plotted 26 periods back)
        chikou = closes[-1]

        # Get current values
        idx = -1
        current_tenkan = tenkan[idx]
        current_kijun = kijun[idx]
        current_senkou_a = senkou_a[idx]
        current_senkou_b = senkou_b[idx]
        current_close = closes[idx]

        # Cloud edges
        cloud_top = max(current_senkou_a, current_senkou_b)
        cloud_bottom = min(current_senkou_a, current_senkou_b)

        # Determine trend based on price vs cloud
        if current_close > cloud_top:
            trend = 1  # Bullish - price above cloud
        elif current_close < cloud_bottom:
            trend = -1  # Bearish - price below cloud
        else:
            trend = 0  # Neutral - price inside cloud

        # Detect Tenkan/Kijun crossover
        tk_cross = 0
        if len(tenkan) >= 2 and len(kijun) >= 2:
            prev_tenkan = tenkan[-2]
            prev_kijun = kijun[-2]

            # Bullish cross: Tenkan crosses above Kijun
            if prev_tenkan <= prev_kijun and current_tenkan > current_kijun:
                tk_cross = 1
            # Bearish cross: Tenkan crosses below Kijun
            elif prev_tenkan >= prev_kijun and current_tenkan < current_kijun:
                tk_cross = -1

        # Cloud color (future cloud direction)
        cloud_bullish = 1 if current_senkou_a > current_senkou_b else -1

        # Generate signal
        # Strong buy: Price above cloud + Tenkan > Kijun + TK bullish cross
        # Strong sell: Price below cloud + Tenkan < Kijun + TK bearish cross
        signal = 0

        if trend == 1 and current_tenkan > current_kijun:
            if tk_cross == 1:
                signal = 1  # Strong buy signal
            elif cloud_bullish == 1:
                signal = 1  # Confirming buy
        elif trend == -1 and current_tenkan < current_kijun:
            if tk_cross == -1:
                signal = -1  # Strong sell signal
            elif cloud_bullish == -1:
                signal = -1  # Confirming sell

        # Kumo breakout signal
        if len(closes) >= 2:
            prev_close = closes[-2]
            # Bullish kumo breakout
            if prev_close <= cloud_top and current_close > cloud_top:
                signal = 1
            # Bearish kumo breakout
            elif prev_close >= cloud_bottom and current_close < cloud_bottom:
                signal = -1

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "tenkan": Decimal(str(round(current_tenkan, 8))),
                "kijun": Decimal(str(round(current_kijun, 8))),
                "senkou_a": Decimal(str(round(current_senkou_a, 8))),
                "senkou_b": Decimal(str(round(current_senkou_b, 8))),
                "chikou": Decimal(str(round(chikou, 8))),
                "cloud_top": Decimal(str(round(cloud_top, 8))),
                "cloud_bottom": Decimal(str(round(cloud_bottom, 8))),
                "trend": Decimal(str(int(trend))),
                "tk_cross": Decimal(str(int(tk_cross))),
                "cloud_bullish": Decimal(str(int(cloud_bullish))),
                "signal": Decimal(str(signal)),
            }
        )

    def calculate_series(self, candles: List[Candle]) -> List[IndicatorResult]:
        """Calculate Ichimoku for entire series"""
        results = []

        for i in range(self.required_candles, len(candles) + 1):
            try:
                result = self.calculate(candles[:i])
                results.append(result)
            except (ValueError, IndexError):
                continue

        return results
