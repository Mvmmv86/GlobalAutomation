"""Technical indicators calculators for automated trading strategies"""

from .base import BaseIndicatorCalculator, Candle, IndicatorResult
from .nadaraya_watson import NadarayaWatsonCalculator
from .tpo import TPOCalculator
from .stochastic import StochasticCalculator
from .stochastic_rsi import StochasticRSICalculator
from .supertrend import SuperTrendCalculator
from .adx import ADXCalculator
from .vwap import VWAPCalculator
from .ichimoku import IchimokuCalculator
from .obv import OBVCalculator
from .rsi import RSICalculator
from .macd import MACDCalculator
from .bollinger import BollingerCalculator
from .ema_cross import EMACrossCalculator
from .ema import EMACalculator
from .atr import ATRCalculator

__all__ = [
    # Base classes
    "BaseIndicatorCalculator",
    "Candle",
    "IndicatorResult",
    # Indicadores existentes
    "NadarayaWatsonCalculator",
    "TPOCalculator",
    # Novos indicadores - Fase 1
    "StochasticCalculator",
    "StochasticRSICalculator",
    "SuperTrendCalculator",
    # Novos indicadores - Fase 3
    "ADXCalculator",
    "VWAPCalculator",
    # Novos indicadores - Fase 4 (Estrategias Institucionais)
    "IchimokuCalculator",
    "OBVCalculator",
    # Indicadores classicos adicionados para backtest
    "RSICalculator",
    "MACDCalculator",
    "BollingerCalculator",
    "EMACrossCalculator",
    "EMACalculator",
    "ATRCalculator",
]
