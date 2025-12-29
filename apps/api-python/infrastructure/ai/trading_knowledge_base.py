"""
Trading AI Knowledge Base

Base de conhecimento especializada em trading institucional, hedge funds,
e estrategias quantitativas para criptomoedas.

Fontes:
- BlackRock Aladdin risk management framework
- Renaissance Technologies / Medallion Fund strategies
- Two Sigma AI/ML approaches
- PwC Global Crypto Hedge Fund Report 2024
- Institutional crypto risk management frameworks

Este conhecimento e usado pela IA para avaliar estrategias, sugerir melhorias,
e fornecer analises profissionais de nivel institucional.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from enum import Enum


class RiskLevel(str, Enum):
    """Niveis de risco para avaliacao"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    EXTREME = "extreme"


class MarketCondition(str, Enum):
    """Condicoes de mercado"""
    STRONG_BULL = "strong_bull"
    BULL = "bull"
    SIDEWAYS = "sideways"
    BEAR = "bear"
    STRONG_BEAR = "strong_bear"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class InstitutionalBenchmarks:
    """
    Benchmarks institucionais baseados em pesquisa de hedge funds
    Fonte: PwC Global Crypto Hedge Fund Report 2024, QuantifiedStrategies
    """
    # Medallion Fund benchmarks (best in class)
    medallion_annual_return: float = 66.0  # % anual bruto
    medallion_sharpe: float = 2.5
    medallion_max_drawdown: float = 10.0  # %
    medallion_win_rate: float = 51.0  # % (ligeiramente acima de 50%)

    # Crypto hedge funds 2024 benchmarks
    crypto_hf_avg_return: float = 25.0  # % anual
    crypto_hf_avg_sharpe: float = 1.2
    crypto_hf_avg_max_dd: float = 35.0  # %
    crypto_hf_avg_win_rate: float = 55.0  # %

    # Minimum acceptable thresholds
    min_acceptable_sharpe: float = 0.5
    min_acceptable_win_rate: float = 40.0
    max_acceptable_drawdown: float = 50.0
    min_acceptable_profit_factor: float = 1.2

    # Risk-adjusted targets
    excellent_sharpe: float = 2.0
    good_sharpe: float = 1.5
    acceptable_sharpe: float = 1.0

    # Position sizing (Kelly Criterion based)
    max_position_size_pct: float = 5.0  # % do capital por trade
    optimal_leverage_range: tuple = (1, 10)  # Range de alavancagem
    max_leverage_high_vol: int = 5
    max_leverage_low_vol: int = 20


@dataclass
class RiskManagementRules:
    """
    Regras de gestao de risco baseadas em frameworks institucionais
    Fonte: BlackRock Aladdin, Basel Committee, EY C-RAM Framework
    """
    # Stop Loss Rules
    max_stop_loss_pct: float = 5.0  # Nunca mais que 5%
    recommended_stop_loss_range: tuple = (1.0, 3.0)
    dynamic_stop_based_on_atr: bool = True
    atr_multiplier_for_stop: float = 2.0

    # Position Sizing
    max_single_position_pct: float = 5.0
    max_correlated_positions_pct: float = 15.0
    max_total_exposure_pct: float = 100.0

    # Drawdown Rules
    daily_loss_limit_pct: float = 5.0
    weekly_loss_limit_pct: float = 10.0
    monthly_loss_limit_pct: float = 20.0
    pause_trading_drawdown_pct: float = 25.0
    stop_trading_drawdown_pct: float = 35.0

    # Leverage Rules by Market Condition
    leverage_rules: Dict[str, int] = field(default_factory=lambda: {
        "strong_bull": 10,
        "bull": 8,
        "sideways": 5,
        "bear": 3,
        "strong_bear": 2,
        "high_volatility": 3,
        "low_volatility": 15
    })

    # Correlation Rules
    max_correlation_between_positions: float = 0.7
    diversification_min_assets: int = 3


@dataclass
class StrategyEvaluationCriteria:
    """
    Criterios para avaliacao RIGOROSA de estrategias
    Baseado em metodologia de hedge funds institucionais
    """
    # Minimum data requirements
    min_backtest_trades: int = 100
    min_backtest_period_days: int = 365
    min_out_of_sample_period_days: int = 90

    # Performance thresholds for PASS
    min_sharpe_ratio: float = 1.0
    min_sortino_ratio: float = 1.2
    min_profit_factor: float = 1.3
    min_win_rate: float = 45.0
    max_drawdown: float = 30.0

    # Walk-forward validation
    max_is_oos_degradation_pct: float = 30.0  # Max 30% degradation

    # Statistical significance
    min_t_statistic: float = 2.0
    max_p_value: float = 0.05

    # Robustness checks
    must_survive_stress_tests: bool = True
    must_pass_monte_carlo: bool = True
    min_monte_carlo_confidence: float = 0.95

    # Red flags that FAIL a strategy
    red_flags: List[str] = field(default_factory=lambda: [
        "Sharpe < 0.5",
        "Max Drawdown > 50%",
        "Win Rate < 35%",
        "Profit Factor < 1.0",
        "Less than 50 trades in backtest",
        "Only tested on 1 asset",
        "No stress test survival",
        "Walk-forward degradation > 50%",
        "Curve fitting suspected (too good to be true)",
        "No stop loss defined",
        "Leverage > 50x",
    ])


class TradingKnowledgeBase:
    """
    Base de conhecimento completa para IA de trading
    Compilado de fontes institucionais e pesquisa academica
    """

    # =========================================================================
    # ESTRATEGIAS QUANTITATIVAS (Baseado em Renaissance, Two Sigma)
    # =========================================================================

    QUANT_STRATEGIES = {
        "statistical_arbitrage": {
            "description": "Explora discrepancias de preco entre ativos correlacionados",
            "best_for": ["sideways", "low_volatility"],
            "avoid_in": ["strong_trend", "high_volatility"],
            "typical_sharpe": 1.5,
            "typical_win_rate": 55,
            "key_indicators": ["correlation", "z-score", "cointegration"],
            "risk_level": "medium",
            "complexity": "high",
            "capital_requirement": "high"
        },
        "trend_following": {
            "description": "Segue tendencias de mercado usando indicadores tecnicos",
            "best_for": ["strong_bull", "strong_bear", "trending"],
            "avoid_in": ["sideways", "choppy"],
            "typical_sharpe": 1.0,
            "typical_win_rate": 40,
            "key_indicators": ["moving_averages", "supertrend", "adx"],
            "risk_level": "medium",
            "complexity": "low",
            "capital_requirement": "medium"
        },
        "mean_reversion": {
            "description": "Aposta no retorno do preco a media",
            "best_for": ["sideways", "ranging"],
            "avoid_in": ["strong_trend"],
            "typical_sharpe": 1.3,
            "typical_win_rate": 60,
            "key_indicators": ["bollinger", "rsi", "stochastic"],
            "risk_level": "medium",
            "complexity": "medium",
            "capital_requirement": "medium"
        },
        "momentum": {
            "description": "Compra ativos com momentum positivo, vende com negativo",
            "best_for": ["bull", "strong_bull"],
            "avoid_in": ["bear", "reversals"],
            "typical_sharpe": 1.2,
            "typical_win_rate": 50,
            "key_indicators": ["macd", "rsi", "rate_of_change"],
            "risk_level": "high",
            "complexity": "low",
            "capital_requirement": "low"
        },
        "breakout": {
            "description": "Entra em rompimentos de suporte/resistencia",
            "best_for": ["consolidation_end", "low_volatility"],
            "avoid_in": ["choppy", "fake_breakouts"],
            "typical_sharpe": 0.9,
            "typical_win_rate": 35,
            "key_indicators": ["bollinger_squeeze", "volume", "atr"],
            "risk_level": "high",
            "complexity": "medium",
            "capital_requirement": "medium"
        },
        "market_making": {
            "description": "Fornece liquidez capturando spread bid-ask",
            "best_for": ["high_volume", "stable"],
            "avoid_in": ["low_liquidity", "high_volatility"],
            "typical_sharpe": 2.0,
            "typical_win_rate": 70,
            "key_indicators": ["order_book", "spread", "volume"],
            "risk_level": "low",
            "complexity": "very_high",
            "capital_requirement": "very_high"
        }
    }

    # =========================================================================
    # INDICADORES E SEUS USOS OTIMOS
    # =========================================================================

    INDICATOR_KNOWLEDGE = {
        "rsi": {
            "name": "Relative Strength Index",
            "category": "momentum",
            "optimal_params": {"period": 14, "overbought": 70, "oversold": 30},
            "crypto_params": {"period": 14, "overbought": 65, "oversold": 35},
            "best_use": "mean_reversion, divergence detection",
            "avoid": "strong trends (will stay overbought/oversold)",
            "combine_with": ["bollinger", "macd", "volume"],
            "signal_strength": "medium",
            "lag": "low"
        },
        "macd": {
            "name": "Moving Average Convergence Divergence",
            "category": "trend",
            "optimal_params": {"fast": 12, "slow": 26, "signal": 9},
            "crypto_params": {"fast": 12, "slow": 26, "signal": 9},
            "best_use": "trend confirmation, momentum",
            "avoid": "sideways markets (many false signals)",
            "combine_with": ["rsi", "ema", "volume"],
            "signal_strength": "high",
            "lag": "high"
        },
        "bollinger": {
            "name": "Bollinger Bands",
            "category": "volatility",
            "optimal_params": {"period": 20, "stddev": 2.0},
            "crypto_params": {"period": 20, "stddev": 2.5},
            "best_use": "volatility breakouts, mean reversion",
            "avoid": "trending markets (price walks the band)",
            "combine_with": ["rsi", "volume", "adx"],
            "signal_strength": "medium",
            "lag": "medium"
        },
        "supertrend": {
            "name": "SuperTrend",
            "category": "trend",
            "optimal_params": {"period": 10, "multiplier": 3.0},
            "crypto_params": {"period": 10, "multiplier": 3.5},
            "best_use": "trend following, dynamic stop loss",
            "avoid": "sideways markets",
            "combine_with": ["adx", "volume"],
            "signal_strength": "high",
            "lag": "medium"
        },
        "adx": {
            "name": "Average Directional Index",
            "category": "trend_strength",
            "optimal_params": {"period": 14, "threshold": 25},
            "crypto_params": {"period": 14, "threshold": 20},
            "best_use": "trend strength filter, avoid false signals",
            "avoid": "using as entry signal alone",
            "combine_with": ["supertrend", "macd", "ema"],
            "signal_strength": "high",
            "lag": "medium"
        },
        "ichimoku": {
            "name": "Ichimoku Cloud",
            "category": "multi_purpose",
            "optimal_params": {"tenkan": 9, "kijun": 26, "senkou_b": 52},
            "crypto_params": {"tenkan": 20, "kijun": 60, "senkou_b": 120},
            "best_use": "trend, support/resistance, momentum - all in one",
            "avoid": "timeframes < 1h (too much noise)",
            "combine_with": ["volume", "rsi"],
            "signal_strength": "very_high",
            "lag": "high"
        },
        "obv": {
            "name": "On-Balance Volume",
            "category": "volume",
            "optimal_params": {"sma_period": 20},
            "crypto_params": {"sma_period": 20},
            "best_use": "confirm breakouts, detect divergences",
            "avoid": "low volume periods",
            "combine_with": ["price_action", "bollinger"],
            "signal_strength": "medium",
            "lag": "low"
        },
        "nadaraya_watson": {
            "name": "Nadaraya-Watson Envelope",
            "category": "regression",
            "optimal_params": {"bandwidth": 8, "mult": 3.0},
            "crypto_params": {"bandwidth": 8, "mult": 3.0},
            "best_use": "mean reversion, dynamic support/resistance",
            "avoid": "strong trends",
            "combine_with": ["rsi", "volume"],
            "signal_strength": "high",
            "lag": "variable"
        }
    }

    # =========================================================================
    # ALERTAS E WARNINGS
    # =========================================================================

    CRITICAL_WARNINGS = [
        {
            "condition": "leverage > 20",
            "severity": "critical",
            "message": "Alavancagem acima de 20x e extremamente arriscada. Hedge funds institucionais raramente usam mais de 10x. Considere reduzir."
        },
        {
            "condition": "no_stop_loss",
            "severity": "critical",
            "message": "Estrategia sem stop loss e inaceitavel. Mesmo o Medallion Fund usa stops. Adicione imediatamente."
        },
        {
            "condition": "single_asset",
            "severity": "warning",
            "message": "Testar em apenas 1 ativo nao e suficiente. Two Sigma testa em milhares de ativos. Adicione pelo menos 3-5 ativos correlacionados."
        },
        {
            "condition": "short_backtest",
            "severity": "warning",
            "message": "Backtest muito curto. Minimo recomendado e 1 ano com pelo menos 100 trades. Prefira 3-5 anos."
        },
        {
            "condition": "no_stress_test",
            "severity": "warning",
            "message": "Estrategia nao testada em cenarios de stress. BlackRock Aladdin exige stress tests. Teste em COVID crash, FTX, Luna."
        },
        {
            "condition": "high_correlation",
            "severity": "warning",
            "message": "Posicoes muito correlacionadas. Diversificacao e chave. Mantenha correlacao < 0.7 entre posicoes."
        },
        {
            "condition": "curve_fitting",
            "severity": "critical",
            "message": "Suspeita de curve fitting. Resultados muito bons no backtest geralmente nao se replicam. Faca walk-forward analysis."
        }
    ]

    # =========================================================================
    # RECOMENDACOES POR PERFIL
    # =========================================================================

    PROFILE_RECOMMENDATIONS = {
        "conservative": {
            "max_leverage": 3,
            "max_drawdown_tolerance": 15,
            "min_sharpe": 1.5,
            "preferred_strategies": ["mean_reversion", "market_making"],
            "position_size_pct": 2,
            "stop_loss_pct": 1.5
        },
        "moderate": {
            "max_leverage": 10,
            "max_drawdown_tolerance": 25,
            "min_sharpe": 1.0,
            "preferred_strategies": ["trend_following", "momentum"],
            "position_size_pct": 5,
            "stop_loss_pct": 2.5
        },
        "aggressive": {
            "max_leverage": 20,
            "max_drawdown_tolerance": 40,
            "min_sharpe": 0.8,
            "preferred_strategies": ["breakout", "momentum"],
            "position_size_pct": 10,
            "stop_loss_pct": 4.0
        }
    }

    # =========================================================================
    # MARKET REGIME DETECTION
    # =========================================================================

    MARKET_REGIMES = {
        "trending_up": {
            "indicators": ["ADX > 25", "price > 200 EMA", "higher highs"],
            "recommended_strategies": ["trend_following", "momentum"],
            "avoid_strategies": ["mean_reversion"],
            "leverage_adjustment": 1.0
        },
        "trending_down": {
            "indicators": ["ADX > 25", "price < 200 EMA", "lower lows"],
            "recommended_strategies": ["trend_following (short)", "hedging"],
            "avoid_strategies": ["momentum (long only)"],
            "leverage_adjustment": 0.7
        },
        "ranging": {
            "indicators": ["ADX < 20", "price between S/R", "BB squeeze"],
            "recommended_strategies": ["mean_reversion", "range_trading"],
            "avoid_strategies": ["trend_following", "breakout"],
            "leverage_adjustment": 0.5
        },
        "high_volatility": {
            "indicators": ["ATR > 2x average", "VIX equivalent high"],
            "recommended_strategies": ["reduce_exposure", "hedging"],
            "avoid_strategies": ["all aggressive strategies"],
            "leverage_adjustment": 0.3
        }
    }

    # =========================================================================
    # CRYPTO-SPECIFIC KNOWLEDGE
    # =========================================================================

    CRYPTO_SPECIFIC = {
        "24_7_trading": {
            "impact": "No gaps, continuous price action",
            "adjustment": "Indicators podem precisar de periodos diferentes"
        },
        "high_volatility": {
            "impact": "ATR tipicamente 3-5x maior que acoes",
            "adjustment": "Stop loss e take profit devem ser maiores"
        },
        "whale_manipulation": {
            "impact": "Grandes players podem mover mercado",
            "adjustment": "Usar on-chain analysis, monitorar grandes wallets"
        },
        "funding_rates": {
            "impact": "Custo de manter posicoes futures",
            "adjustment": "Considerar funding em estrategias de longo prazo"
        },
        "liquidation_cascades": {
            "impact": "Movimentos amplificados por liquidacoes",
            "adjustment": "Manter alavancagem conservadora, usar stops"
        },
        "regulatory_risk": {
            "impact": "Noticias regulatorias causam volatilidade",
            "adjustment": "Reduzir exposicao em periodos de incerteza"
        }
    }

    @classmethod
    def get_benchmarks(cls) -> InstitutionalBenchmarks:
        return InstitutionalBenchmarks()

    @classmethod
    def get_risk_rules(cls) -> RiskManagementRules:
        return RiskManagementRules()

    @classmethod
    def get_evaluation_criteria(cls) -> StrategyEvaluationCriteria:
        return StrategyEvaluationCriteria()

    @classmethod
    def get_strategy_info(cls, strategy_type: str) -> Dict:
        return cls.QUANT_STRATEGIES.get(strategy_type, {})

    @classmethod
    def get_indicator_info(cls, indicator: str) -> Dict:
        return cls.INDICATOR_KNOWLEDGE.get(indicator, {})

    @classmethod
    def get_all_warnings(cls) -> List[Dict]:
        return cls.CRITICAL_WARNINGS

    @classmethod
    def get_profile_recommendation(cls, profile: str) -> Dict:
        return cls.PROFILE_RECOMMENDATIONS.get(profile, cls.PROFILE_RECOMMENDATIONS["moderate"])


# =============================================================================
# IMPORT EXPANDED KNOWLEDGE
# =============================================================================

from infrastructure.ai.expanded_knowledge import (
    AladdinRiskFramework,
    OnChainKnowledge,
    QuantHedgeFundMethods,
    CryptoMarketStructure,
    AdvancedTradingConcepts,
    RESEARCH_SOURCES,
    get_expanded_knowledge
)

# Add expanded knowledge to main class
TradingKnowledgeBase.ALADDIN = AladdinRiskFramework
TradingKnowledgeBase.ONCHAIN = OnChainKnowledge
TradingKnowledgeBase.QUANT_METHODS = QuantHedgeFundMethods
TradingKnowledgeBase.MARKET_STRUCTURE = CryptoMarketStructure
TradingKnowledgeBase.ADVANCED = AdvancedTradingConcepts
TradingKnowledgeBase.SOURCES = RESEARCH_SOURCES

@classmethod
def get_full_knowledge(cls):
    """Get all knowledge including expanded"""
    return get_expanded_knowledge()

TradingKnowledgeBase.get_full_knowledge = get_full_knowledge
