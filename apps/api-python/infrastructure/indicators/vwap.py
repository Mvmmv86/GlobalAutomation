"""
VWAP (Volume Weighted Average Price) Implementation

VWAP e o preco medio ponderado pelo volume, usado principalmente
para trading intraday como benchmark de preco justo.

Formula:
VWAP = Cumulative(Price x Volume) / Cumulative(Volume)
Onde Price = (High + Low + Close) / 3 (Typical Price)

Bandas de Desvio (opcional):
- Upper Band = VWAP + (StdDev x Multiplier)
- Lower Band = VWAP - (StdDev x Multiplier)

Interpretacao:
- Preco acima do VWAP: Tendencia bullish intraday
- Preco abaixo do VWAP: Tendencia bearish intraday
- VWAP atua como suporte/resistencia dinamico

Uso em Estrategias:
- Mean Reversion: Comprar quando preco toca banda inferior, vender na superior
- Trend Following: Comprar acima do VWAP, vender abaixo
- Confirmacao: Usar VWAP como filtro para outros sinais

Parametros:
- use_bands: Calcular bandas de desvio (default: True)
- band_multiplier: Multiplicador do desvio padrao (default: 2.0)
- reset_daily: Resetar VWAP diariamente (default: True para intraday)

NOTA: Para crypto 24/7, o reset pode ser configurado por sessao ou desabilitado.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class VWAPCalculator(BaseIndicatorCalculator):
    """
    VWAP (Volume Weighted Average Price) Calculator

    Calcula VWAP com bandas de desvio opcionais.
    Util para trading intraday e confirmacao de tendencia.
    """

    name = "vwap"
    required_candles = 20

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        super().__init__(parameters)
        self.use_bands = bool(self.parameters.get("use_bands", True))
        self.band_multiplier = float(self.parameters.get("band_multiplier", 2.0))
        self.reset_daily = bool(self.parameters.get("reset_daily", False))

    def _validate_parameters(self) -> None:
        """Validate parameters"""
        if self.parameters.get("band_multiplier", 2.0) <= 0:
            raise ValueError("band_multiplier must be > 0")

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """
        Calculate VWAP and deviation bands

        Returns:
            IndicatorResult with keys:
            - vwap: Current VWAP value
            - upper_band: Upper deviation band (if use_bands=True)
            - lower_band: Lower deviation band (if use_bands=True)
            - deviation: Current price deviation from VWAP (%)
            - signal: 1 (below lower band), -1 (above upper band), 0 (between)
        """
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles, got {len(candles)}")

        # Determine candles to use (with optional daily reset)
        if self.reset_daily:
            candles_to_use = self._get_session_candles(candles)
        else:
            candles_to_use = candles

        if len(candles_to_use) < 2:
            candles_to_use = candles[-self.required_candles:]

        # Calculate Typical Price for each candle
        typical_prices = []
        volumes = []

        for c in candles_to_use:
            tp = (float(c.high) + float(c.low) + float(c.close)) / 3
            typical_prices.append(tp)
            volumes.append(float(c.volume))

        typical_prices = np.array(typical_prices)
        volumes = np.array(volumes)

        # Calculate VWAP
        cumulative_tp_volume = np.cumsum(typical_prices * volumes)
        cumulative_volume = np.cumsum(volumes)

        # Avoid division by zero
        cumulative_volume = np.where(cumulative_volume == 0, 1, cumulative_volume)

        vwap_values = cumulative_tp_volume / cumulative_volume

        current_vwap = vwap_values[-1]
        current_close = float(candles[-1].close)

        # Calculate bands if enabled
        if self.use_bands and len(vwap_values) > 1:
            # Calculate squared deviations from VWAP
            squared_devs = (typical_prices - vwap_values) ** 2
            cumulative_squared_devs = np.cumsum(squared_devs * volumes)

            variance = cumulative_squared_devs / cumulative_volume
            std_dev = np.sqrt(variance)

            current_std = std_dev[-1]
            upper_band = current_vwap + (current_std * self.band_multiplier)
            lower_band = current_vwap - (current_std * self.band_multiplier)
        else:
            upper_band = current_vwap
            lower_band = current_vwap
            current_std = 0

        # Calculate price deviation from VWAP
        if current_vwap > 0:
            deviation = ((current_close - current_vwap) / current_vwap) * 100
        else:
            deviation = 0

        # Generate signal
        signal = 0
        if self.use_bands:
            if current_close < lower_band:
                signal = 1  # Below lower band - potential buy (mean reversion)
            elif current_close > upper_band:
                signal = -1  # Above upper band - potential sell (mean reversion)

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "vwap": Decimal(str(round(current_vwap, 8))),
                "upper_band": Decimal(str(round(upper_band, 8))),
                "lower_band": Decimal(str(round(lower_band, 8))),
                "deviation": Decimal(str(round(deviation, 4))),
                "signal": Decimal(str(signal)),
            }
        )

    def _get_session_candles(self, candles: List[Candle]) -> List[Candle]:
        """
        Get candles from current session (for daily reset)

        For crypto, we can define "session" as:
        - UTC day (00:00 - 23:59 UTC)
        - Or based on last N candles if no clear session boundary
        """
        if not candles:
            return []

        current_date = candles[-1].timestamp.date()

        # Filter candles from current day
        session_candles = [
            c for c in candles
            if c.timestamp.date() == current_date
        ]

        # If not enough candles for current day, use recent candles
        if len(session_candles) < 10:
            return candles[-min(50, len(candles)):]

        return session_candles

    def calculate_series(self, candles: List[Candle]) -> List[IndicatorResult]:
        """Calculate VWAP for entire series"""
        results = []

        for i in range(self.required_candles, len(candles) + 1):
            try:
                result = self.calculate(candles[:i])
                results.append(result)
            except (ValueError, IndexError):
                continue

        return results
