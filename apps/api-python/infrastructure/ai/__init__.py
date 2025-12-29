"""
Trading AI Module

Módulo completo de IA para trading com:
- Base de conhecimento institucional (BlackRock, Renaissance, Two Sigma)
- Serviço de IA para chat e avaliação de estratégias
- Coletor de dados para aprendizado contínuo
"""

from .trading_knowledge_base import (
    TradingKnowledgeBase,
    InstitutionalBenchmarks,
    RiskManagementRules,
    StrategyEvaluationCriteria,
)
from .trading_ai_service import (
    TradingAIService,
    StrategyEvaluation,
    BotAnalysis,
    DailyReport,
    ConversationContext,
    get_trading_ai,
)
from .data_collector import (
    TradingDataCollector,
    DailySnapshot,
    BotSnapshot,
    StrategySnapshot,
)

__all__ = [
    # Knowledge Base
    "TradingKnowledgeBase",
    "InstitutionalBenchmarks",
    "RiskManagementRules",
    "StrategyEvaluationCriteria",
    # AI Service
    "TradingAIService",
    "StrategyEvaluation",
    "BotAnalysis",
    "DailyReport",
    "ConversationContext",
    "get_trading_ai",
    # Data Collector
    "TradingDataCollector",
    "DailySnapshot",
    "BotSnapshot",
    "StrategySnapshot",
]
