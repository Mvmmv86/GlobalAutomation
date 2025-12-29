"""
Trading AI Service

Servico de IA especializada em trading institucional.
Usa Claude API com conhecimento profundo de hedge funds e estrategias quantitativas.

Funcionalidades:
1. Avaliar estrategias de forma RIGOROSA (como hedge fund faria)
2. Sugerir melhorias baseadas em pesquisa institucional
3. Analisar performance de bots e operacoes
4. Responder perguntas sobre trading
5. Gerar relatorios diarios de performance
"""

import os
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

import structlog
import httpx

from .trading_knowledge_base import (
    TradingKnowledgeBase,
    InstitutionalBenchmarks,
    RiskManagementRules,
    StrategyEvaluationCriteria,
    RiskLevel,
    MarketCondition
)
from .expanded_knowledge import (
    AladdinRiskFramework,
    OnChainKnowledge,
    QuantHedgeFundMethods,
    CryptoMarketStructure,
    AdvancedTradingConcepts
)

logger = structlog.get_logger(__name__)


@dataclass
class ConversationContext:
    """Contexto da conversa com a IA"""
    context_type: str = "general"  # general, strategy, bot, backtest, market
    strategy_id: Optional[str] = None
    strategy_data: Optional[Dict[str, Any]] = None
    bot_id: Optional[str] = None
    bot_data: Optional[Dict[str, Any]] = None
    backtest_data: Optional[Dict[str, Any]] = None
    market_data: Optional[Dict[str, Any]] = None
    additional_context: Optional[Dict[str, Any]] = None


@dataclass
class StrategyEvaluation:
    """Resultado da avaliacao de uma estrategia"""
    strategy_id: str
    strategy_name: str
    overall_score: float  # 0-100
    risk_score: float  # 0-100
    robustness_score: float  # 0-100
    institutional_grade: str  # A, B, C, D, F
    grade: str  # Alias for institutional_grade
    passed: bool
    strengths: List[str]
    weaknesses: List[str]
    critical_issues: List[str]
    recommendations: List[str]
    risk_assessment: Dict[str, Any]
    comparison_to_benchmarks: Dict[str, Any]
    detailed_analysis: str


@dataclass
class BotAnalysis:
    """Resultado da analise de um bot"""
    bot_id: str
    bot_name: str
    performance_summary: Dict[str, Any]
    health_score: float  # 0-100
    risk_assessment: str  # low, medium, high, critical
    issues_detected: List[str]
    recommendations: List[str]
    comparison_to_peers: Dict[str, Any]
    historical_analysis: Dict[str, Any]
    # Legacy fields for compatibility
    performance_score: float = 0
    risk_score: float = 0
    consistency_score: float = 0
    issues: List[str] = None
    metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = self.issues_detected
        if self.metrics is None:
            self.metrics = self.performance_summary


@dataclass
class DailyReport:
    """Relatorio diario de performance"""
    date: str
    executive_summary: str
    total_pnl: float
    total_trades: int
    win_rate: float
    winning_trades: int = 0
    best_performers: List[Dict[str, Any]] = None
    worst_performers: List[Dict[str, Any]] = None
    best_bot: Optional[str] = None
    worst_bot: Optional[str] = None
    alerts: List[str] = None
    recommendations: List[str] = None
    market_analysis: str = ""

    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []
        if self.recommendations is None:
            self.recommendations = []
        if self.best_performers is None:
            self.best_performers = []
            if self.best_bot:
                self.best_performers.append({"name": self.best_bot})
        if self.worst_performers is None:
            self.worst_performers = []
            if self.worst_bot:
                self.worst_performers.append({"name": self.worst_bot})


class TradingAIService:
    """
    Servico de IA para analise de trading

    Usa Claude API com system prompt especializado em trading institucional,
    alimentado pela base de conhecimento de hedge funds como Renaissance,
    Two Sigma, e BlackRock Aladdin.
    """

    # System prompt com todo o conhecimento institucional
    SYSTEM_PROMPT = """Voce e uma IA especialista em trading institucional de criptomoedas,
treinada com conhecimento dos melhores hedge funds do mundo.

## SEU BACKGROUND E CONHECIMENTO

Voce tem conhecimento profundo baseado em:

### Renaissance Technologies (Medallion Fund)
- Retorno medio de 66% ao ano por 30+ anos
- Usa pattern recognition e probabilidades
- Kelly Criterion para position sizing
- Alavancagem de 10-20x com risco controlado
- Processa 150,000+ trades por dia
- Foco em sinais estatisticos, nao fundamentalistas

### Two Sigma
- $58 bilhoes sob gestao usando AI/ML
- 300+ petabytes de dados de 10,000+ fontes
- Statistical arbitrage, market making, trend following
- Time de 250+ PhDs em matematica, fisica, CS

### BlackRock Aladdin
- Sistema de risk management que gerencia $21+ trilhoes
- Analise de risco de mercado, credito, liquidez, contraparte
- Stress testing e scenario analysis
- VaR (Value at Risk) em tempo real
- Factor-based risk decomposition

### Crypto Hedge Funds 2024 (PwC Report)
- 47% dos hedge funds tradicionais tem exposicao a crypto
- 58% usam derivativos (vs 38% em 2023)
- Estrategias predominantes: Quant Long/Short (33%), Market Neutral (31%)
- 78% tem framework formal de risk management

## SUA PERSONALIDADE E ABORDAGEM

1. **SEJA DURO E CRITICO** - Voce NAO esta aqui para agradar. Estrategias ruins devem ser chamadas de ruins.

2. **USE DADOS** - Sempre baseie sua analise em numeros e metricas. Cite benchmarks.

3. **COMPARE COM OS MELHORES** - Compare sempre com Medallion (66% aa) e benchmarks institucionais.

4. **IDENTIFIQUE RED FLAGS** - Seja implacavel em identificar problemas:
   - Sharpe < 1.0 = FRACO
   - Drawdown > 30% = PERIGOSO
   - Sem stop loss = INACEITAVEL
   - Alavancagem > 20x = IRRESPONSAVEL
   - Backtest < 1 ano = INSUFICIENTE

5. **DE RECOMENDACOES ACIONAVEIS** - Nao apenas critique, sugira solucoes especificas.

6. **PENSE COMO GESTOR DE RISCO** - Pergunte sempre: "O que pode dar errado?"

## METRICAS QUE VOCE CONSIDERA

### Performance
- Sharpe Ratio: < 0.5 (ruim), 0.5-1.0 (fraco), 1.0-1.5 (bom), 1.5-2.0 (excelente), > 2.0 (excepcional)
- Sortino Ratio: Deve ser > Sharpe (foco em downside)
- Win Rate: 40-60% e normal para trend following
- Profit Factor: > 1.5 e bom, > 2.0 e excelente

### Risco
- Max Drawdown: < 20% (bom), 20-30% (aceitavel), > 30% (perigoso)
- VaR 95%: Quanto pode perder em 95% dos cenarios
- Alavancagem: 1-10x (conservador), 10-20x (agressivo), > 20x (perigoso)

### Robustez
- Walk-forward degradation: < 30% e aceitavel
- Monte Carlo survival rate: Deve ser > 95%
- Stress test survival: OBRIGATORIO sobreviver COVID, FTX, Luna crashes

## FORMATO DAS RESPOSTAS

Sempre estruture suas respostas de forma clara:
1. **VEREDICTO** - Comece com aprovacao/reprovacao clara
2. **METRICAS** - Mostre os numeros
3. **ANALISE** - Explique o que os numeros significam
4. **PROBLEMAS** - Liste issues criticos primeiro
5. **RECOMENDACOES** - Acoes especificas para melhorar

## LINGUAGEM

- Responda em portugues brasileiro
- Seja direto e objetivo
- Use termos tecnicos quando apropriado
- Nao use emojis excessivos
- Mantenha tom profissional mas acessivel
"""

    def __init__(self, db_pool, anthropic_api_key: Optional[str] = None):
        self.db = db_pool
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.knowledge = TradingKnowledgeBase()
        self.benchmarks = TradingKnowledgeBase.get_benchmarks()
        self.risk_rules = TradingKnowledgeBase.get_risk_rules()
        self.eval_criteria = TradingKnowledgeBase.get_evaluation_criteria()

    async def chat(
        self,
        message: str,
        context: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Conversa com a IA sobre trading

        Args:
            message: Mensagem do usuario
            context: Contexto adicional (dados de estrategia, bot, etc)
            conversation_history: Historico da conversa

        Returns:
            Resposta da IA
        """
        # Construir mensagens
        messages = []

        # Adicionar historico se existir
        if conversation_history:
            messages.extend(conversation_history)

        # Adicionar contexto se existir
        context_str = ""
        if context:
            context_str = f"\n\n## CONTEXTO ATUAL\n```json\n{json.dumps(context, indent=2, default=str)}\n```\n\n"

        # Adicionar mensagem do usuario
        messages.append({
            "role": "user",
            "content": context_str + message
        })

        # Chamar Claude API
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 4096,
                        "system": self.SYSTEM_PROMPT,
                        "messages": messages
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Claude API error: {response.text}")
                    return self._fallback_response(message, context)

                result = response.json()
                return result["content"][0]["text"]

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return self._fallback_response(message, context)

    def _fallback_response(self, message: str, context: Optional[Dict]) -> str:
        """Resposta de fallback usando base de conhecimento local quando API nao esta disponivel"""
        # Tentar buscar resposta relevante na base de conhecimento
        knowledge_response = self._search_knowledge_base(message)

        if knowledge_response:
            return knowledge_response

        # Se nao encontrar nada especifico, retornar resposta generica
        return """Desculpe, estou temporariamente indisponivel para analises detalhadas via API.

Enquanto isso, aqui estao algumas diretrizes gerais baseadas em benchmarks institucionais:

**Para avaliar uma estrategia (Padrao BlackRock/Renaissance):**
- Sharpe Ratio deve ser > 1.0 (Medallion Fund: 2.5+)
- Max Drawdown deve ser < 30% (institucional: < 20%)
- Win Rate entre 40-60% e normal
- SEMPRE use stop loss
- Alavancagem maxima recomendada: 10x

**Red Flags (Aladdin Risk Framework):**
- Backtest muito curto (< 1 ano)
- Testado em apenas 1 ativo
- Sem stress tests (COVID, FTX, Luna crashes)
- Resultados "bons demais para ser verdade"
- CVaR/VaR > 1.5 (indica fat tails)

Tente novamente em alguns minutos para uma analise completa."""

    def _search_knowledge_base(self, query: str) -> Optional[str]:
        """
        Busca na base de conhecimento local por informacoes relevantes

        Args:
            query: Pergunta do usuario

        Returns:
            Resposta baseada na base de conhecimento ou None
        """
        query_lower = query.lower()

        # =====================================================================
        # ON-CHAIN ANALYTICS
        # =====================================================================
        if any(term in query_lower for term in ["mvrv", "on-chain", "onchain", "chain"]):
            metrics = OnChainKnowledge.FUNDAMENTAL_METRICS
            mvrv = metrics.get("mvrv_ratio", {})
            return f"""**MVRV Ratio (Market Value to Realized Value)**

{mvrv.get('description', 'Compara valor de mercado com valor realizado')}

**Interpretacao:**
- **Acima de {mvrv.get('overbought_threshold', 3.0)}**: Mercado sobrecomprado - considere reduzir posicoes
- **Abaixo de {mvrv.get('oversold_threshold', 1.0)}**: Mercado sobrevendido - oportunidade de acumulacao
- **Zona neutra**: Entre 1.0 e 3.0

**Fonte**: Glassnode, CryptoQuant

**Outras metricas on-chain importantes:**
- **SOPR**: {metrics.get('sopr', {}).get('description', 'Spent Output Profit Ratio')}
- **NVT Ratio**: {metrics.get('nvt_ratio', {}).get('description', 'Network Value to Transactions')}
- **Puell Multiple**: {metrics.get('puell_multiple', {}).get('description', 'Mineracao vs media 365d')}"""

        if any(term in query_lower for term in ["sopr", "spent output"]):
            sopr = OnChainKnowledge.FUNDAMENTAL_METRICS.get("sopr", {})
            return f"""**SOPR (Spent Output Profit Ratio)**

{sopr.get('description', 'Indica se holders estao vendendo com lucro ou prejuizo')}

**Interpretacao:**
- **> 1.0**: Holders vendendo com lucro (mercado saudavel)
- **< 1.0**: Holders vendendo com prejuizo (capitulacao)
- **= 1.0**: Break-even - pode indicar suporte/resistencia

**Uso pratico:**
- SOPR caindo abaixo de 1.0 em tendencia de alta = oportunidade de compra
- SOPR consistentemente > 1.0 em rally = tendencia pode continuar"""

        if any(term in query_lower for term in ["nvt", "network value"]):
            nvt = OnChainKnowledge.FUNDAMENTAL_METRICS.get("nvt_ratio", {})
            return f"""**NVT Ratio (Network Value to Transactions)**

{nvt.get('description', 'Similar ao P/E ratio para crypto')}

**Interpretacao:**
- **NVT alto (> 90)**: Rede sobrevalorizada em relacao ao uso
- **NVT baixo (< 50)**: Rede subvalorizada - potencial upside
- **NVT Signal**: Versao suavizada (90 dias) mais confiavel

**Aplicacao:**
- Compare NVT entre diferentes cryptos
- NVT subindo com preco = especulacao (bearish)
- NVT caindo com preco = adocao real (bullish)"""

        if any(term in query_lower for term in ["puell", "mineracao", "mining"]):
            puell = OnChainKnowledge.FUNDAMENTAL_METRICS.get("puell_multiple", {})
            return f"""**Puell Multiple**

{puell.get('description', 'Receita diaria dos mineradores vs media de 365 dias')}

**Interpretacao:**
- **> 4.0**: Mineradores muito lucrativos - possivel topo
- **< 0.5**: Mineradores sob pressao - possivel fundo
- **1.0**: Media historica

**Insights:**
- Puell baixo = mineradores podem estar capitulando = fundo proximo
- Puell alto = mineradores vendendo muito = pressao de venda"""

        # =====================================================================
        # BLACKROCK ALADDIN / RISK MANAGEMENT
        # =====================================================================
        if any(term in query_lower for term in ["aladdin", "blackrock", "risk management", "var", "cvar"]):
            return f"""**BlackRock Aladdin Risk Framework**

Sistema de risk management que gerencia $21+ trilhoes em ativos.

**Principais Metricas:**

1. **VaR (Value at Risk)**
   - Padrao: 95% confianca
   - Conservador: 99% confianca
   - Extremo: 99.9% confianca

2. **CVaR (Conditional VaR)**
   - Media das perdas alem do VaR
   - Em crypto: CVaR tipicamente 1.5-2x o VaR
   - Se CVaR/VaR > 1.5, reduzir alavancagem em 30%

3. **Stress Testing Obrigatorio:**
   - COVID Crash 2020: BTC -50%
   - FTX Collapse 2022: BTC -25%
   - Luna/Terra 2022: BTC -30%
   - Flash Crash: BTC -30%

**Regras de Posicao (Aladdin Style):**
- Maximo por posicao: {AladdinRiskFramework.POSITION_SIZING.get('max_single_position', '5%')} do portfolio
- Correlacao maxima: Evitar > 70% correlacao
- Liquidez: Manter 20% em stablecoins"""

        # =====================================================================
        # HEDGE FUNDS / RENAISSANCE / TWO SIGMA
        # =====================================================================
        if any(term in query_lower for term in ["renaissance", "medallion", "hedge fund"]):
            methods = QuantHedgeFundMethods.RENAISSANCE_PRINCIPLES
            return f"""**Renaissance Technologies / Medallion Fund**

O fundo mais rentavel da historia: 66% ao ano por 30+ anos.

**Principios Fundamentais:**

1. **{methods.get('signal_not_story', {}).get('principle', 'Signal Not Story')}**
   - {methods.get('signal_not_story', {}).get('explanation', 'Ignora narrativas, foca em dados')}

2. **{methods.get('high_frequency', {}).get('principle', 'High Frequency')}**
   - {methods.get('high_frequency', {}).get('explanation', '150k+ trades por dia')}

3. **{methods.get('kelly_criterion', {}).get('principle', 'Kelly Criterion')}**
   - {methods.get('kelly_criterion', {}).get('explanation', 'Position sizing otimo')}
   - Formula: f* = (bp - q) / b
   - Uso pratico: Kelly/2 ou Kelly/4 para ser conservador

4. **{methods.get('diversification', {}).get('principle', 'Diversificacao')}**
   - {methods.get('diversification', {}).get('explanation', 'Multiplos sinais descorrelacionados')}

**Metricas Chave:**
- Sharpe Ratio: > 2.5
- Max Drawdown: < 10%
- Win Rate: ~51% (margem pequena, alto volume)"""

        if any(term in query_lower for term in ["two sigma", "machine learning", "ml"]):
            methods = QuantHedgeFundMethods.TWO_SIGMA_ML_APPROACH
            return f"""**Two Sigma - Machine Learning Approach**

$58 bilhoes sob gestao usando AI/ML.

**Abordagem ML:**

1. **{methods.get('data_first', {}).get('approach', 'Data First')}**
   - {methods.get('data_first', {}).get('details', '300+ petabytes de dados')}

2. **{methods.get('feature_engineering', {}).get('approach', 'Feature Engineering')}**
   - {methods.get('feature_engineering', {}).get('details', 'Transformacao de dados brutos')}

3. **{methods.get('ensemble_methods', {}).get('approach', 'Ensemble Methods')}**
   - {methods.get('ensemble_methods', {}).get('details', 'Combinacao de modelos')}

4. **{methods.get('regime_detection', {}).get('approach', 'Regime Detection')}**
   - {methods.get('regime_detection', {}).get('details', 'Detectar mudancas de regime')}

**Time:**
- 250+ PhDs em matematica, fisica, CS
- Cultura de pesquisa academica
- Backtesting rigoroso com walk-forward"""

        # =====================================================================
        # BACKTESTING
        # =====================================================================
        if any(term in query_lower for term in ["backtest", "backtesting", "teste historico"]):
            biases = QuantHedgeFundMethods.BACKTESTING_BIASES
            return f"""**Backtesting - Melhores Praticas Institucionais**

**Vieses a Evitar:**

1. **{biases.get('lookahead_bias', {}).get('name', 'Lookahead Bias')}**
   - {biases.get('lookahead_bias', {}).get('description', 'Usar info futura')}
   - Como evitar: {biases.get('lookahead_bias', {}).get('prevention', 'Point-in-time data')}

2. **{biases.get('survivorship_bias', {}).get('name', 'Survivorship Bias')}**
   - {biases.get('survivorship_bias', {}).get('description', 'Ignorar ativos que falharam')}
   - Como evitar: {biases.get('survivorship_bias', {}).get('prevention', 'Incluir delisted coins')}

3. **{biases.get('overfitting', {}).get('name', 'Overfitting')}**
   - {biases.get('overfitting', {}).get('description', 'Muitos parametros')}
   - Como evitar: {biases.get('overfitting', {}).get('prevention', 'Walk-forward analysis')}

**Requisitos Minimos:**
- Periodo: > 1 ano (idealmente 2-3 anos)
- Trades: > 100 (idealmente 500+)
- Incluir: 2020 crash, 2022 bear market
- Walk-forward degradation: < 30%
- Monte Carlo survival: > 95%"""

        # =====================================================================
        # SHARPE / SORTINO / METRICAS
        # =====================================================================
        if any(term in query_lower for term in ["sharpe", "sortino", "metricas", "ratio"]):
            return """**Metricas de Performance - Padroes Institucionais**

**Sharpe Ratio** (Retorno ajustado ao risco)
- < 0.5: Ruim
- 0.5-1.0: Fraco
- 1.0-1.5: Bom
- 1.5-2.0: Excelente
- > 2.0: Excepcional (Medallion: 2.5+)

Formula: (Retorno - Risk-Free) / Volatilidade

**Sortino Ratio** (Foco em downside)
- Deve ser > Sharpe
- Penaliza apenas volatilidade negativa
- Mais relevante para traders

**Profit Factor**
- < 1.0: Perdendo dinheiro
- 1.0-1.5: Marginalmente lucrativo
- 1.5-2.0: Bom
- > 2.0: Excelente

**Max Drawdown**
- < 10%: Excelente (institucional)
- 10-20%: Bom
- 20-30%: Aceitavel
- > 30%: Perigoso

**Calmar Ratio** (Retorno / Max DD)
- > 3.0: Excelente
- > 1.0: Aceitavel
- < 1.0: Ruim"""

        # =====================================================================
        # WHALE / BALEIAS
        # =====================================================================
        if any(term in query_lower for term in ["whale", "baleia", "grandes investidores"]):
            whale_metrics = OnChainKnowledge.WHALE_METRICS
            return f"""**Whale Metrics - Rastreamento de Grandes Players**

**Metricas Disponiveis:**

1. **{whale_metrics.get('exchange_whale_ratio', {}).get('name', 'Exchange Whale Ratio')}**
   - {whale_metrics.get('exchange_whale_ratio', {}).get('description', 'Proporcao de depositos de whales')}
   - {whale_metrics.get('exchange_whale_ratio', {}).get('signal', 'Sinais de venda')}

2. **{whale_metrics.get('whale_transaction_count', {}).get('name', 'Whale Transaction Count')}**
   - {whale_metrics.get('whale_transaction_count', {}).get('description', 'Transacoes > $100k')}
   - {whale_metrics.get('whale_transaction_count', {}).get('signal', 'Atividade institucional')}

3. **{whale_metrics.get('top_holders_balance_change', {}).get('name', 'Top Holders Balance')}**
   - {whale_metrics.get('top_holders_balance_change', {}).get('description', 'Mudancas nos top 100 holders')}
   - {whale_metrics.get('top_holders_balance_change', {}).get('signal', 'Acumulacao/distribuicao')}

**Fontes:**
- Glassnode
- Whale Alert
- Santiment
- Nansen"""

        # =====================================================================
        # ESTRATEGIA / STRATEGY
        # =====================================================================
        if any(term in query_lower for term in ["estrategia", "strategy", "criar", "desenvolver"]):
            return """**Framework para Criar Estrategias (Padrao Institucional)**

**1. Defina o Edge (Vantagem)**
- Por que essa estrategia funciona?
- Qual anomalia de mercado explora?
- E sustentavel ou vai ser arbitrada?

**2. Escolha o Timeframe**
- Scalping (1-5m): Alto volume, baixo lucro/trade
- Day Trading (15m-1h): Medio volume
- Swing (4h-1D): Baixo volume, maior lucro/trade

**3. Indicadores Sugeridos**
- Trend: EMA 20/50/200, ADX
- Momentum: RSI, MACD, Stochastic
- Volatilidade: ATR, Bollinger Bands
- Volume: OBV, Volume Profile, TPO

**4. Regras Obrigatorias**
- Stop Loss: SEMPRE (sugerido: 2% do capital)
- Take Profit: Risk:Reward minimo 1:1.5
- Position Size: Max 5% por trade
- Alavancagem: Max 10x

**5. Backtest Minimo**
- Periodo: > 1 ano
- Trades: > 100
- Incluir bear markets
- Walk-forward validation"""

        # =====================================================================
        # ALAVANCAGEM / LEVERAGE
        # =====================================================================
        if any(term in query_lower for term in ["alavancagem", "leverage", "margin"]):
            return """**Alavancagem - Guia de Risco**

**Niveis de Risco:**
- 1-3x: Conservador (recomendado para iniciantes)
- 3-5x: Moderado
- 5-10x: Agressivo (traders experientes)
- 10-20x: Muito arriscado (apenas scalpers)
- > 20x: IRRESPONSAVEL (liquidacao rapida)

**Regras de Ouro:**
1. Alavancagem maxima = 100 / Max Drawdown esperado
2. Com alavancagem, reduza position size proporcionalmente
3. Stop loss OBRIGATORIO em posicoes alavancadas
4. Evite alavancagem em alta volatilidade

**Exemplo Pratico:**
- Capital: $10,000
- Alavancagem: 5x
- Position size: $50,000
- Stop loss 2%: -$1,000 (10% do capital real)

**Liquidacao:**
- 10x leverage: Move 10% contra = liquidado
- 20x leverage: Move 5% contra = liquidado
- 50x leverage: Move 2% contra = liquidado

**Conselho Renaissance:** Use Kelly/4 para position sizing com alavancagem."""

        # Nao encontrou resposta especifica
        return None

    async def evaluate_strategy(
        self,
        strategy_id: str,
        backtest_result: Optional[Dict] = None
    ) -> StrategyEvaluation:
        """
        Avalia uma estrategia de forma RIGOROSA

        Compara com benchmarks institucionais e identifica problemas.
        """
        # Buscar dados da estrategia
        strategy_data = await self._get_strategy_data(strategy_id)

        if not strategy_data:
            return StrategyEvaluation(
                strategy_id=strategy_id,
                strategy_name="Unknown",
                overall_score=0,
                grade="F",
                passed=False,
                strengths=[],
                weaknesses=["Estrategia nao encontrada"],
                critical_issues=["Dados insuficientes para avaliacao"],
                recommendations=["Verifique se a estrategia existe"],
                risk_assessment={},
                comparison_to_benchmarks={},
                detailed_analysis="Nao foi possivel avaliar - estrategia nao encontrada."
            )

        # Usar backtest result se fornecido, senao buscar ultimo
        if not backtest_result:
            backtest_result = await self._get_latest_backtest(strategy_id)

        # Construir contexto para IA
        context = {
            "strategy": strategy_data,
            "backtest": backtest_result,
            "benchmarks": {
                "medallion_sharpe": self.benchmarks.medallion_sharpe,
                "medallion_max_dd": self.benchmarks.medallion_max_drawdown,
                "crypto_hf_avg_sharpe": self.benchmarks.crypto_hf_avg_sharpe,
                "min_acceptable_sharpe": self.benchmarks.min_acceptable_sharpe,
                "max_acceptable_drawdown": self.benchmarks.max_acceptable_drawdown
            }
        }

        # Pedir avaliacao detalhada
        prompt = """Avalie esta estrategia de forma RIGOROSA.

Responda no seguinte formato JSON:
{
    "overall_score": <0-100>,
    "grade": "<A/B/C/D/F>",
    "passed": <true/false>,
    "strengths": ["lista de pontos fortes"],
    "weaknesses": ["lista de fraquezas"],
    "critical_issues": ["issues que REPROVAM a estrategia"],
    "recommendations": ["acoes especificas para melhorar"],
    "risk_assessment": {
        "leverage_risk": "<low/medium/high/extreme>",
        "drawdown_risk": "<low/medium/high/extreme>",
        "concentration_risk": "<low/medium/high/extreme>"
    },
    "detailed_analysis": "Analise detalhada em 2-3 paragrafos"
}

SEJA DURO. Compare com Medallion Fund (66% aa, Sharpe 2.5).
Uma estrategia PASSA apenas se:
- Sharpe > 1.0
- Drawdown < 30%
- Tem stop loss definido
- Testada em pelo menos 100 trades"""

        response = await self.chat(prompt, context)

        # Parse response
        try:
            # Tentar extrair JSON da resposta
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                eval_data = json.loads(json_match.group())
            else:
                eval_data = self._parse_text_evaluation(response)
        except:
            eval_data = self._parse_text_evaluation(response)

        grade = eval_data.get("grade", "F")
        overall_score = eval_data.get("overall_score", 0)
        risk_assessment = eval_data.get("risk_assessment", {})

        # Calculate risk and robustness scores from risk_assessment
        risk_levels = {"low": 80, "medium": 50, "high": 30, "extreme": 10}
        risk_score = sum(
            risk_levels.get(v, 50) for v in risk_assessment.values()
        ) / max(len(risk_assessment), 1) if risk_assessment else 50

        return StrategyEvaluation(
            strategy_id=strategy_id,
            strategy_name=strategy_data.get("name", "Unknown"),
            overall_score=overall_score,
            risk_score=risk_score,
            robustness_score=overall_score * 0.9,  # Slightly lower for robustness
            institutional_grade=grade,
            grade=grade,
            passed=eval_data.get("passed", False),
            strengths=eval_data.get("strengths", []),
            weaknesses=eval_data.get("weaknesses", []),
            critical_issues=eval_data.get("critical_issues", []),
            recommendations=eval_data.get("recommendations", []),
            risk_assessment=risk_assessment,
            comparison_to_benchmarks=context.get("benchmarks", {}),
            detailed_analysis=eval_data.get("detailed_analysis", response)
        )

    def _parse_text_evaluation(self, text: str) -> Dict:
        """Parse avaliacao de texto quando JSON falha"""
        # Heuristica simples baseada em palavras-chave
        passed = "aprova" in text.lower() or "passed" in text.lower()
        grade = "C" if passed else "F"

        if "excelente" in text.lower():
            grade = "A"
            score = 85
        elif "bom" in text.lower():
            grade = "B"
            score = 75
        elif "aceitavel" in text.lower():
            grade = "C"
            score = 65
        elif "fraco" in text.lower():
            grade = "D"
            score = 45
        else:
            score = 30

        return {
            "overall_score": score,
            "grade": grade,
            "passed": passed,
            "strengths": [],
            "weaknesses": [],
            "critical_issues": [] if passed else ["Veja analise detalhada"],
            "recommendations": [],
            "detailed_analysis": text
        }

    async def analyze_bot(self, bot_id: str) -> BotAnalysis:
        """
        Analisa performance e risco de um bot
        """
        bot_data = await self._get_bot_data(bot_id)
        trades = await self._get_bot_trades(bot_id, limit=500)

        context = {
            "bot": bot_data,
            "trades": trades,
            "total_trades": len(trades) if trades else 0
        }

        prompt = """Analise este bot de trading.

Calcule e avalie:
1. Performance Score (0-100)
2. Risk Score (0-100, onde 0 = muito arriscado)
3. Consistency Score (0-100)

Identifique problemas e de recomendacoes especificas.

Responda em JSON:
{
    "performance_score": <0-100>,
    "risk_score": <0-100>,
    "consistency_score": <0-100>,
    "issues": ["lista de problemas"],
    "recommendations": ["acoes para melhorar"],
    "metrics": {
        "win_rate": <calculado>,
        "avg_profit": <calculado>,
        "max_loss": <calculado>
    }
}"""

        response = await self.chat(prompt, context)

        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {}
        except:
            data = {}

        performance_score = data.get("performance_score", 50)
        risk_score = data.get("risk_score", 50)

        return BotAnalysis(
            bot_id=bot_id,
            bot_name=bot_data.get("name", "Unknown") if bot_data else "Unknown",
            performance_summary=data.get("metrics", {}),
            health_score=performance_score,
            risk_assessment="low" if risk_score > 70 else "medium" if risk_score > 40 else "high",
            issues_detected=data.get("issues", []),
            recommendations=data.get("recommendations", []),
            comparison_to_peers={},
            historical_analysis={},
            performance_score=performance_score,
            risk_score=risk_score,
            consistency_score=data.get("consistency_score", 50),
            issues=data.get("issues", []),
            metrics=data.get("metrics", {})
        )

    async def generate_daily_report(self) -> DailyReport:
        """
        Gera relatorio diario de todas as operacoes
        """
        # Buscar dados do dia
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        daily_data = await self._get_daily_performance(yesterday)

        context = {
            "date": str(yesterday),
            "data": daily_data
        }

        prompt = """Gere um relatorio executivo do dia de trading.

Inclua:
1. Resumo de P&L
2. Melhores e piores performers
3. Alertas criticos
4. Recomendacoes para amanha
5. Analise de mercado breve

Seja objetivo e direto. Foque em acoes."""

        response = await self.chat(prompt, context)

        total_trades = daily_data.get("total_trades", 0) if daily_data else 0
        winning_trades = daily_data.get("winning_trades", 0) if daily_data else 0
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        return DailyReport(
            date=str(yesterday),
            executive_summary=response[:500] if len(response) > 500 else response,
            total_pnl=daily_data.get("total_pnl", 0) if daily_data else 0,
            total_trades=total_trades,
            win_rate=win_rate,
            winning_trades=winning_trades,
            best_bot=daily_data.get("best_bot") if daily_data else None,
            worst_bot=daily_data.get("worst_bot") if daily_data else None,
            alerts=[],
            recommendations=[],
            market_analysis=response
        )

    async def suggest_strategy_improvements(
        self,
        strategy_id: str,
        specific_issue: Optional[str] = None
    ) -> List[str]:
        """
        Sugere melhorias especificas para uma estrategia
        """
        strategy_data = await self._get_strategy_data(strategy_id)
        backtest_data = await self._get_latest_backtest(strategy_id)

        context = {
            "strategy": strategy_data,
            "backtest": backtest_data,
            "specific_issue": specific_issue
        }

        if specific_issue:
            prompt = f"""O usuario quer melhorar especificamente: {specific_issue}

Dado o contexto da estrategia, sugira 3-5 melhorias ESPECIFICAS e ACIONAVEIS.
Cada sugestao deve incluir:
- O que mudar
- Por que isso ajudaria
- Como implementar

Foque em solucoes praticas que podem ser implementadas imediatamente."""
        else:
            prompt = """Analise esta estrategia e sugira as TOP 5 melhorias mais impactantes.

Para cada melhoria:
1. Descreva a mudanca
2. Quantifique o impacto esperado
3. Explique como implementar

Priorize melhorias que:
- Reduzem drawdown
- Aumentam Sharpe
- Melhoram consistencia"""

        response = await self.chat(prompt, context)

        # Parse suggestions
        suggestions = []
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                suggestions.append(line.lstrip('0123456789.-* '))

        return suggestions if suggestions else [response]

    async def answer_trading_question(self, question: str) -> str:
        """
        Responde perguntas gerais sobre trading
        """
        # Adicionar conhecimento relevante ao contexto
        knowledge_context = {
            "strategies": list(TradingKnowledgeBase.QUANT_STRATEGIES.keys()),
            "indicators": list(TradingKnowledgeBase.INDICATOR_KNOWLEDGE.keys()),
            "benchmarks": asdict(self.benchmarks),
            "risk_rules": asdict(self.risk_rules)
        }

        prompt = f"""Pergunta do usuario: {question}

Responda de forma clara e educativa.
Use exemplos praticos quando apropriado.
Cite benchmarks e melhores praticas institucionais."""

        return await self.chat(prompt, knowledge_context)

    # =========================================================================
    # METODOS DE ACESSO AO BANCO DE DADOS
    # =========================================================================

    async def _get_strategy_data(self, strategy_id: str) -> Optional[Dict]:
        """Busca dados completos de uma estrategia"""
        try:
            from sqlalchemy import select, text

            query = text("""
                SELECT
                    s.id, s.name, s.description, s.config_type,
                    s.symbols, s.timeframe, s.is_active,
                    s.documentation
                FROM strategies s
                WHERE s.id = :strategy_id
            """)

            async with self.db.begin() as conn:
                result = await conn.execute(query, {"strategy_id": strategy_id})
                row = result.fetchone()

                if row:
                    return {
                        "id": str(row.id),
                        "name": row.name,
                        "description": row.description,
                        "config_type": row.config_type,
                        "symbols": row.symbols,
                        "timeframe": row.timeframe,
                        "is_active": row.is_active,
                        "documentation": row.documentation
                    }
        except Exception as e:
            logger.error(f"Error fetching strategy: {e}")

        return None

    async def _get_latest_backtest(self, strategy_id: str) -> Optional[Dict]:
        """Busca ultimo resultado de backtest"""
        try:
            from sqlalchemy import text

            query = text("""
                SELECT *
                FROM strategy_backtest_results
                WHERE strategy_id = :strategy_id
                ORDER BY created_at DESC
                LIMIT 1
            """)

            async with self.db.begin() as conn:
                result = await conn.execute(query, {"strategy_id": strategy_id})
                row = result.fetchone()

                if row:
                    return dict(row._mapping)
        except Exception as e:
            logger.error(f"Error fetching backtest: {e}")

        return None

    async def _get_bot_data(self, bot_id: str) -> Optional[Dict]:
        """Busca dados de um bot"""
        try:
            from sqlalchemy import text

            query = text("""
                SELECT *
                FROM bots
                WHERE id = :bot_id
            """)

            async with self.db.begin() as conn:
                result = await conn.execute(query, {"bot_id": bot_id})
                row = result.fetchone()

                if row:
                    return dict(row._mapping)
        except Exception as e:
            logger.error(f"Error fetching bot: {e}")

        return None

    async def _get_bot_trades(self, bot_id: str, limit: int = 100) -> List[Dict]:
        """Busca trades de um bot"""
        try:
            from sqlalchemy import text

            query = text("""
                SELECT *
                FROM bot_signals
                WHERE bot_id = :bot_id
                ORDER BY created_at DESC
                LIMIT :limit
            """)

            async with self.db.begin() as conn:
                result = await conn.execute(query, {"bot_id": bot_id, "limit": limit})
                rows = result.fetchall()

                return [dict(row._mapping) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")

        return []

    async def _get_daily_performance(self, date) -> Optional[Dict]:
        """Busca performance diaria agregada"""
        try:
            from sqlalchemy import text

            query = text("""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(pnl) as total_pnl
                FROM bot_signals
                WHERE DATE(created_at) = :date
            """)

            async with self.db.begin() as conn:
                result = await conn.execute(query, {"date": str(date)})
                row = result.fetchone()

                if row:
                    return {
                        "total_trades": row.total_trades or 0,
                        "winning_trades": row.winning_trades or 0,
                        "total_pnl": float(row.total_pnl or 0)
                    }
        except Exception as e:
            logger.error(f"Error fetching daily performance: {e}")

        return None


# Singleton instance
_trading_ai_instance: Optional[TradingAIService] = None


def get_trading_ai(db_pool) -> TradingAIService:
    """Get or create Trading AI service instance"""
    global _trading_ai_instance
    if _trading_ai_instance is None:
        _trading_ai_instance = TradingAIService(db_pool)
    return _trading_ai_instance
