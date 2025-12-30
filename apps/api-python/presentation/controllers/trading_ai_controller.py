"""
Trading AI Controller
Handles all AI-related endpoints for strategy evaluation, bot analysis, and chat
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

import structlog

from infrastructure.database.connection import database_manager
from infrastructure.ai import (
    TradingAIService,
    TradingDataCollector,
    ConversationContext,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["trading-ai"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatMessage(BaseModel):
    """Mensagem de chat com a IA"""
    message: str = Field(..., min_length=1, max_length=10000)
    context_type: str = Field(
        default="general",
        pattern="^(general|strategy|bot|backtest|market)$"
    )
    context_id: Optional[str] = Field(
        None,
        description="ID da estratégia ou bot para contexto específico"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="ID da conversa para manter histórico"
    )


class ChatResponse(BaseModel):
    """Resposta do chat da IA"""
    response: str
    conversation_id: str
    context_used: Dict[str, Any]
    suggestions: List[str] = []
    warnings: List[str] = []


class StrategyEvaluationRequest(BaseModel):
    """Request para avaliação de estratégia"""
    strategy_id: str
    backtest_result: Optional[Dict[str, Any]] = None
    include_recommendations: bool = True


class StrategyEvaluationResponse(BaseModel):
    """Resposta da avaliação de estratégia"""
    strategy_id: str
    overall_score: float = Field(..., ge=0, le=100)
    risk_score: float = Field(..., ge=0, le=100)
    robustness_score: float = Field(..., ge=0, le=100)
    institutional_grade: str
    strengths: List[str]
    weaknesses: List[str]
    critical_issues: List[str]
    recommendations: List[str]
    comparison_to_benchmarks: Dict[str, Any]
    detailed_analysis: str


class BotAnalysisRequest(BaseModel):
    """Request para análise de bot"""
    bot_id: str
    include_history: bool = True
    days_to_analyze: int = Field(default=30, ge=1, le=365)


class BotAnalysisResponse(BaseModel):
    """Resposta da análise de bot"""
    bot_id: str
    bot_name: str
    performance_summary: Dict[str, Any]
    health_score: float = Field(..., ge=0, le=100)
    risk_assessment: str
    issues_detected: List[str]
    recommendations: List[str]
    comparison_to_peers: Dict[str, Any]
    historical_analysis: Dict[str, Any]


class DailyReportResponse(BaseModel):
    """Relatório diário gerado pela IA"""
    date: str
    executive_summary: str
    total_pnl: float
    total_trades: int
    win_rate: float
    best_performers: List[Dict[str, Any]]
    worst_performers: List[Dict[str, Any]]
    alerts: List[str]
    market_analysis: str
    recommendations: List[str]


class TradingQuestionRequest(BaseModel):
    """Pergunta sobre trading"""
    question: str = Field(..., min_length=5, max_length=5000)
    include_examples: bool = True


class ImprovementSuggestionRequest(BaseModel):
    """Request para sugestões de melhoria"""
    strategy_id: str
    specific_issue: Optional[str] = None
    focus_area: str = Field(
        default="general",
        pattern="^(general|risk|entry|exit|indicators|position_sizing)$"
    )


# ============================================================================
# Conversation Storage (In-memory for now, should be moved to DB)
# ============================================================================

conversations: Dict[str, List[Dict[str, str]]] = {}


# ============================================================================
# Service Instance
# ============================================================================

# Global AI service instance
_ai_service = None


def set_ai_db_pool(db_pool):
    """Set the database pool for AI service"""
    global _ai_service
    _ai_service = TradingAIService(db_pool)


def get_ai_service() -> TradingAIService:
    """Get or create AI service instance"""
    global _ai_service
    if _ai_service is None:
        # Fallback - create without db_pool (limited functionality)
        from infrastructure.database.connection_transaction_mode import transaction_db
        _ai_service = TradingAIService(transaction_db)
    return _ai_service


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatMessage):
    """
    Chat com a IA de Trading

    Suporta diferentes contextos:
    - general: Perguntas gerais sobre trading
    - strategy: Contexto específico de uma estratégia
    - bot: Contexto específico de um bot
    - backtest: Discussão sobre resultados de backtest
    - market: Análise de condições de mercado
    """
    try:
        ai_service = get_ai_service()

        # Build context based on context_type
        context = ConversationContext(context_type=request.context_type)

        # Load specific context if provided
        if request.context_id:
            async with database_manager.get_session() as session:
                if request.context_type == "strategy":
                    context.strategy_id = request.context_id
                    # Load strategy data
                    strategy = await session.execute(
                        "SELECT * FROM strategies WHERE id = :id",
                        {"id": request.context_id}
                    )
                    row = strategy.fetchone()
                    if row:
                        context.strategy_data = dict(row._mapping)

                elif request.context_type == "bot":
                    context.bot_id = request.context_id
                    # Load bot data
                    bot = await session.execute(
                        "SELECT * FROM bots WHERE id = :id",
                        {"id": request.context_id}
                    )
                    row = bot.fetchone()
                    if row:
                        context.bot_data = dict(row._mapping)

        # Get or create conversation history
        conv_id = request.conversation_id or f"conv_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if conv_id not in conversations:
            conversations[conv_id] = []

        # Add user message to history
        conversations[conv_id].append({
            "role": "user",
            "content": request.message
        })

        # Get AI response
        response = await ai_service.chat(
            message=request.message,
            context=context,
            conversation_history=conversations[conv_id][-10:]  # Last 10 messages
        )

        # Add AI response to history
        conversations[conv_id].append({
            "role": "assistant",
            "content": response
        })

        # Extract suggestions and warnings from response
        suggestions = []
        warnings = []

        if "SUGESTÃO:" in response or "RECOMENDAÇÃO:" in response:
            suggestions.append("Ver recomendações na resposta")
        if "ALERTA:" in response or "CUIDADO:" in response or "CRÍTICO:" in response:
            warnings.append("Ver alertas na resposta")

        return ChatResponse(
            response=response,
            conversation_id=conv_id,
            context_used={
                "type": request.context_type,
                "id": request.context_id,
                "history_length": len(conversations[conv_id])
            },
            suggestions=suggestions,
            warnings=warnings
        )

    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate-strategy", response_model=StrategyEvaluationResponse)
async def evaluate_strategy(request: StrategyEvaluationRequest):
    """
    Avaliação RIGOROSA de estratégia pela IA

    Usa benchmarks institucionais (Medallion Fund, Two Sigma, etc.)
    para avaliar a qualidade e robustez da estratégia.

    Retorna scores em várias dimensões:
    - Overall Score: Nota geral (0-100)
    - Risk Score: Avaliação de gestão de risco
    - Robustness Score: Robustez e confiabilidade
    - Institutional Grade: Classificação (A, B, C, D, F)
    """
    try:
        ai_service = get_ai_service()

        evaluation = await ai_service.evaluate_strategy(
            strategy_id=request.strategy_id,
            backtest_result=request.backtest_result
        )

        return StrategyEvaluationResponse(
            strategy_id=request.strategy_id,
            overall_score=evaluation.overall_score,
            risk_score=evaluation.risk_score,
            robustness_score=evaluation.robustness_score,
            institutional_grade=evaluation.institutional_grade,
            strengths=evaluation.strengths,
            weaknesses=evaluation.weaknesses,
            critical_issues=evaluation.critical_issues,
            recommendations=evaluation.recommendations,
            comparison_to_benchmarks=evaluation.comparison_to_benchmarks,
            detailed_analysis=evaluation.detailed_analysis
        )

    except Exception as e:
        logger.error(f"Error evaluating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-bot", response_model=BotAnalysisResponse)
async def analyze_bot(request: BotAnalysisRequest):
    """
    Análise completa de um bot pela IA

    Inclui:
    - Sumário de performance
    - Score de saúde operacional
    - Avaliação de risco
    - Problemas detectados
    - Recomendações de melhoria
    - Comparação com outros bots
    """
    try:
        ai_service = get_ai_service()

        analysis = await ai_service.analyze_bot(
            bot_id=request.bot_id,
            days=request.days_to_analyze
        )

        return BotAnalysisResponse(
            bot_id=request.bot_id,
            bot_name=analysis.bot_name,
            performance_summary=analysis.performance_summary,
            health_score=analysis.health_score,
            risk_assessment=analysis.risk_assessment,
            issues_detected=analysis.issues_detected,
            recommendations=analysis.recommendations,
            comparison_to_peers=analysis.comparison_to_peers,
            historical_analysis=analysis.historical_analysis if request.include_history else {}
        )

    except Exception as e:
        logger.error(f"Error analyzing bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-report", response_model=DailyReportResponse)
async def get_daily_report(
    date: Optional[str] = Query(None, description="Data no formato YYYY-MM-DD (default: hoje)")
):
    """
    Gera relatório diário da IA

    Inclui análise de:
    - Todas as operações do dia
    - Performance geral
    - Bots com melhor e pior performance
    - Alertas e problemas
    - Análise de mercado
    - Recomendações estratégicas
    """
    try:
        ai_service = get_ai_service()

        # generate_daily_report uses current date internally
        report = await ai_service.generate_daily_report()

        return DailyReportResponse(
            date=report.date,
            executive_summary=report.executive_summary,
            total_pnl=report.total_pnl,
            total_trades=report.total_trades,
            win_rate=report.win_rate,
            best_performers=report.best_performers,
            worst_performers=report.worst_performers,
            alerts=report.alerts,
            market_analysis=report.market_analysis,
            recommendations=report.recommendations
        )

    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggest-improvements")
async def suggest_strategy_improvements(request: ImprovementSuggestionRequest):
    """
    Sugestões de melhoria para uma estratégia

    A IA analisa a estratégia e sugere melhorias específicas
    baseadas em conhecimento institucional e análise do backtest.
    """
    try:
        ai_service = get_ai_service()

        suggestions = await ai_service.suggest_strategy_improvements(
            strategy_id=request.strategy_id,
            specific_issue=request.specific_issue,
            focus_area=request.focus_area
        )

        return {
            "strategy_id": request.strategy_id,
            "focus_area": request.focus_area,
            "suggestions": suggestions,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error suggesting improvements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask")
async def ask_trading_question(request: TradingQuestionRequest):
    """
    Pergunte qualquer coisa sobre trading

    A IA usa seu conhecimento de:
    - BlackRock Aladdin
    - Renaissance Technologies
    - Two Sigma
    - Melhores práticas institucionais
    - Análise técnica e fundamental
    - Gestão de risco

    Para responder perguntas sobre trading e investimentos.
    """
    try:
        ai_service = get_ai_service()

        response = await ai_service.answer_trading_question(
            question=request.question
        )

        return {
            "question": request.question,
            "answer": response,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect-daily-data")
async def trigger_daily_collection(background_tasks: BackgroundTasks):
    """
    Dispara coleta de dados diária manualmente

    Normalmente executado via cron, mas pode ser disparado
    manualmente para atualização imediata.
    """
    try:
        async def run_collection():
            collector = TradingDataCollector()
            try:
                await collector.connect()
                await collector.collect_daily_data()
            finally:
                await collector.disconnect()

        background_tasks.add_task(run_collection)

        return {
            "status": "started",
            "message": "Coleta de dados iniciada em background",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error triggering collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/force-daily-report")
async def force_daily_report():
    """
    Força a geração do relatório diário de mercado.
    Cria um alerta que aparece no chat da IA.
    """
    try:
        from infrastructure.background.sync_scheduler import sync_scheduler

        # Reset para permitir geração
        sync_scheduler._last_daily_report_date = None

        # Gerar o relatório
        await sync_scheduler._generate_ai_market_report()

        return {
            "status": "success",
            "message": "Relatório diário gerado e alerta criado",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error forcing daily report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-base/stats")
async def get_knowledge_base_stats():
    """
    Retorna estatísticas da base de conhecimento da IA
    """
    from infrastructure.ai import TradingKnowledgeBase

    kb = TradingKnowledgeBase()

    benchmarks = TradingKnowledgeBase.get_benchmarks()
    eval_criteria = TradingKnowledgeBase.get_evaluation_criteria()

    return {
        "total_strategies": len(kb.QUANT_STRATEGIES),
        "total_indicators": len(kb.INDICATOR_KNOWLEDGE),
        "total_warnings": len(kb.CRITICAL_WARNINGS),
        "risk_profiles": list(kb.PROFILE_RECOMMENDATIONS.keys()),
        "market_regimes": list(kb.MARKET_REGIMES.keys()),
        "benchmarks": {
            "medallion_annual_return": benchmarks.medallion_annual_return,
            "medallion_sharpe": benchmarks.medallion_sharpe,
            "min_acceptable_sharpe": benchmarks.min_acceptable_sharpe,
            "max_acceptable_drawdown": benchmarks.max_acceptable_drawdown,
        },
        "evaluation_criteria": {
            "min_backtest_trades": eval_criteria.min_backtest_trades,
            "min_win_rate": eval_criteria.min_win_rate,
            "min_profit_factor": eval_criteria.min_profit_factor,
            "min_sharpe_ratio": eval_criteria.min_sharpe_ratio,
            "max_drawdown": eval_criteria.max_drawdown,
        }
    }


@router.get("/historical-snapshots")
async def get_historical_snapshots(
    days: int = Query(default=30, ge=1, le=365)
):
    """
    Busca snapshots históricos para análise
    """
    try:
        collector = TradingDataCollector()
        await collector.connect()

        try:
            snapshots = await collector.get_historical_data(days=days)

            return {
                "days": days,
                "total_snapshots": len(snapshots),
                "snapshots": [
                    {
                        "date": s.date,
                        "total_pnl": s.total_pnl,
                        "total_trades": s.total_trades,
                        "win_rate": s.win_rate,
                        "active_bots": s.active_bots,
                        "alerts_count": len(s.alerts)
                    }
                    for s in snapshots
                ]
            }
        finally:
            await collector.disconnect()

    except Exception as e:
        logger.error(f"Error fetching snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Deleta uma conversa do histórico
    """
    if conversation_id in conversations:
        del conversations[conversation_id]
        return {"status": "deleted", "conversation_id": conversation_id}
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Busca histórico de uma conversa
    """
    if conversation_id in conversations:
        return {
            "conversation_id": conversation_id,
            "messages": conversations[conversation_id],
            "total_messages": len(conversations[conversation_id])
        }
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")


# ============================================================================
# Alerts Endpoints
# ============================================================================

class AlertResponse(BaseModel):
    """Alert for the chat interface"""
    id: str
    type: str  # critical, warning, info, success
    category: str  # trade, news, strategy, system
    title: str
    message: str
    timestamp: str
    read: bool = False
    actionUrl: Optional[str] = None
    strategyId: Optional[str] = None
    botId: Optional[str] = None


# In-memory storage for read alerts (should be moved to DB in production)
_read_alerts: set = set()


@router.get("/alerts")
async def get_pending_alerts():
    """
    Retorna alertas pendentes para o chat

    Inclui:
    - Alertas de estratégias marcadas como importantes
    - Sinais recentes de estratégias importantes
    - Alertas de performance crítica de bots
    - Notícias importantes (quando disponível)
    """
    try:
        alerts = []

        async with database_manager.get_session() as session:
            # 1. Buscar sinais recentes de estratégias importantes
            try:
                from sqlalchemy import text
                important_signals = await session.execute(text("""
                    SELECT
                        ss.id,
                        ss.strategy_id,
                        ss.signal_type,
                        ss.symbol,
                        ss.entry_price,
                        ss.created_at,
                        s.name as strategy_name
                    FROM strategy_signals ss
                    JOIN strategies s ON s.id = ss.strategy_id
                    WHERE s.is_important = true
                    AND ss.created_at > NOW() - INTERVAL '24 hours'
                    ORDER BY ss.created_at DESC
                    LIMIT 10
                """))

                for row in important_signals:
                    signal = row._mapping
                    alert_id = f"signal_{signal['id']}"

                    signal_emoji = "🟢" if signal['signal_type'] in ['buy', 'long'] else "🔴"

                    alerts.append({
                        "id": alert_id,
                        "type": "info",
                        "category": "trade",
                        "title": f"{signal_emoji} Sinal de {signal['strategy_name']}",
                        "message": f"{signal['signal_type'].upper()} em {signal['symbol']} @ ${signal['entry_price']:.2f}" if signal['entry_price'] else f"{signal['signal_type'].upper()} em {signal['symbol']}",
                        "timestamp": signal['created_at'].isoformat() if signal['created_at'] else datetime.now().isoformat(),
                        "read": alert_id in _read_alerts,
                        "strategyId": str(signal['strategy_id'])
                    })
            except Exception as e:
                # Se is_important não existir ainda, ignora
                logger.debug(f"Could not fetch important signals: {e}")

            # 2. Buscar bots com performance crítica (perda > 10%)
            try:
                critical_bots = await session.execute(text("""
                    SELECT
                        bs.id,
                        bs.bot_id,
                        bs.total_pnl_usd,
                        bs.win_count,
                        bs.loss_count,
                        bs.updated_at,
                        b.name as bot_name
                    FROM bot_subscriptions bs
                    JOIN bots b ON b.id = bs.bot_id
                    WHERE bs.status = 'active'
                    AND bs.total_pnl_usd < -100
                    ORDER BY bs.total_pnl_usd ASC
                    LIMIT 5
                """))

                for row in critical_bots:
                    bot = row._mapping
                    alert_id = f"bot_critical_{bot['id']}"

                    alerts.append({
                        "id": alert_id,
                        "type": "critical",
                        "category": "strategy",
                        "title": f"⚠️ Bot em perda crítica",
                        "message": f"{bot['bot_name']} com P&L de ${bot['total_pnl_usd']:.2f}",
                        "timestamp": bot['updated_at'].isoformat() if bot['updated_at'] else datetime.now().isoformat(),
                        "read": alert_id in _read_alerts,
                        "botId": str(bot['bot_id'])
                    })
            except Exception as e:
                logger.debug(f"Could not fetch critical bots: {e}")

            # 3. Buscar estratégias inativas que deveriam estar ativas
            try:
                inactive_strategies = await session.execute(text("""
                    SELECT
                        s.id,
                        s.name,
                        s.updated_at
                    FROM strategies s
                    WHERE s.is_active = false
                    AND s.is_important = true
                    AND s.updated_at > NOW() - INTERVAL '7 days'
                    LIMIT 5
                """))

                for row in inactive_strategies:
                    strategy = row._mapping
                    alert_id = f"strategy_inactive_{strategy['id']}"

                    alerts.append({
                        "id": alert_id,
                        "type": "warning",
                        "category": "strategy",
                        "title": f"📊 Estratégia importante inativa",
                        "message": f"{strategy['name']} está marcada como importante mas está desativada",
                        "timestamp": strategy['updated_at'].isoformat() if strategy['updated_at'] else datetime.now().isoformat(),
                        "read": alert_id in _read_alerts,
                        "strategyId": str(strategy['id'])
                    })
            except Exception as e:
                logger.debug(f"Could not fetch inactive strategies: {e}")

            # 4. Buscar alertas da tabela ai_alerts (incluindo resumos diários)
            try:
                db_alerts = await session.execute(text("""
                    SELECT
                        id,
                        type,
                        category,
                        title,
                        message,
                        data,
                        is_read,
                        created_at,
                        strategy_id,
                        bot_id
                    FROM ai_alerts
                    WHERE created_at > NOW() - INTERVAL '7 days'
                    ORDER BY created_at DESC
                    LIMIT 20
                """))

                for row in db_alerts:
                    alert = row._mapping
                    alert_id = f"ai_alert_{alert['id']}"

                    alert_item = {
                        "id": alert_id,
                        "type": alert['type'],
                        "category": alert['category'],
                        "title": alert['title'],
                        "message": alert['message'],
                        "timestamp": alert['created_at'].isoformat() if alert['created_at'] else datetime.now().isoformat(),
                        "read": alert['is_read'] or alert_id in _read_alerts,
                    }

                    # Add optional fields
                    if alert['data']:
                        import json
                        data = json.loads(alert['data']) if isinstance(alert['data'], str) else alert['data']
                        alert_item["data"] = data
                        # If it's a market report, include the full report
                        if data.get('full_report'):
                            alert_item["fullContent"] = data['full_report']
                        if data.get('report_date'):
                            alert_item["reportDate"] = data['report_date']

                    # Fallback: if message is long (likely a full report), use it as fullContent
                    if len(alert['message'] or '') > 500 and 'fullContent' not in alert_item:
                        alert_item["fullContent"] = alert['message']
                        # Extract date from title if possible
                        if alert['title'] and '/' in alert['title']:
                            import re
                            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', alert['title'])
                            if date_match:
                                alert_item["reportDate"] = date_match.group(1)

                    if alert['strategy_id']:
                        alert_item["strategyId"] = str(alert['strategy_id'])
                    if alert['bot_id']:
                        alert_item["botId"] = str(alert['bot_id'])

                    alerts.append(alert_item)
            except Exception as e:
                logger.debug(f"Could not fetch ai_alerts: {e}")

        # Sort by timestamp (most recent first)
        alerts.sort(key=lambda x: x['timestamp'], reverse=True)

        return {
            "success": True,
            "data": alerts[:20],  # Limit to 20 alerts
            "total": len(alerts)
        }

    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return {
            "success": True,
            "data": [],
            "total": 0
        }


@router.patch("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str):
    """
    Marca um alerta como lido
    """
    _read_alerts.add(alert_id)
    return {"success": True, "alert_id": alert_id, "read": True}


@router.delete("/alerts/read")
async def clear_read_alerts():
    """
    Limpa alertas lidos do cache
    """
    _read_alerts.clear()
    return {"success": True, "message": "Read alerts cleared"}


