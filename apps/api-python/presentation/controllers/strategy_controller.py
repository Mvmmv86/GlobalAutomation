"""
Strategy Controller
Handles all strategy-related endpoints (CRUD, backtest, signals, engine status)

NOTA: Usa transaction_db (SQL direto) para compatibilidade com pgBouncer
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import structlog

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.services.strategy_service_sql import StrategyServiceSQL
from infrastructure.services.strategy_engine_service import get_strategy_engine

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


# ============================================================================
# Pydantic Models
# ============================================================================

class StrategyCreate(BaseModel):
    """Model for creating a new strategy"""
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    config_type: str = Field(default="visual", pattern="^(visual|yaml|pinescript)$")
    symbols: List[str] = Field(default_factory=list)
    timeframe: str = Field(default="5m", pattern="^(1m|3m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d|3d|1w)$")
    bot_id: Optional[str] = None
    config_yaml: Optional[str] = None
    pinescript_source: Optional[str] = None


class StrategyUpdate(BaseModel):
    """Model for updating a strategy"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    symbols: Optional[List[str]] = None
    timeframe: Optional[str] = Field(None, pattern="^(1m|3m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d|3d|1w)$")
    bot_id: Optional[str] = None


class IndicatorCreate(BaseModel):
    """Model for adding an indicator"""
    indicator_type: str = Field(..., pattern="^(nadaraya_watson|tpo|rsi|macd|ema|bollinger|atr|volume_profile)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    order_index: int = Field(default=0, ge=0)


class ConditionCreate(BaseModel):
    """Model for adding a condition"""
    condition_type: str = Field(..., pattern="^(entry_long|entry_short|exit_long|exit_short)$")
    conditions: List[Dict[str, Any]] = Field(
        ...,
        description="List of condition rules: [{left: 'close', operator: '<', right: 'ndy.lower'}]"
    )
    logic_operator: str = Field(default="AND", pattern="^(AND|OR)$")
    order_index: int = Field(default=0, ge=0)


class YamlConfigApply(BaseModel):
    """Model for applying YAML configuration"""
    yaml_content: str = Field(..., min_length=10)


class BacktestRequest(BaseModel):
    """Model for running a backtest"""
    symbol: str = Field(..., min_length=1)
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(default=10000, ge=100)
    leverage: int = Field(default=10, ge=1, le=125)
    margin_percent: float = Field(default=5.0, ge=1, le=100)
    stop_loss_percent: float = Field(default=2.0, ge=0.1, le=50)
    take_profit_percent: float = Field(default=4.0, ge=0.1, le=100)
    include_fees: bool = True
    include_slippage: bool = True


class PineScriptWebhookPayload(BaseModel):
    """Model for PineScript/TradingView webhook alerts"""
    secret: str = Field(..., min_length=10, description="Webhook secret for authentication")
    action: str = Field(..., pattern="^(buy|sell|close|close_long|close_short)$", description="Trading action")
    ticker: str = Field(..., min_length=1, description="Trading symbol (e.g., BTCUSDT)")
    price: Optional[float] = Field(None, description="Entry/exit price")
    quantity: Optional[float] = Field(None, description="Order quantity")
    position_size: Optional[float] = Field(None, description="Position size from strategy")
    comment: Optional[str] = Field(None, description="Order comment from strategy")
    leverage: Optional[int] = Field(None, ge=1, le=125, description="Override leverage")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")


# ============================================================================
# Helper function to get service
# ============================================================================

def get_strategy_service() -> StrategyServiceSQL:
    """Get a StrategyServiceSQL instance with transaction_db"""
    return StrategyServiceSQL(transaction_db)


# ============================================================================
# Strategy CRUD Endpoints
# ============================================================================

@router.get("")
async def list_strategies(
    active_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    List all strategies with statistics

    Query params:
    - active_only: Only return active strategies
    - limit: Maximum number of results (default 50)
    - offset: Pagination offset
    """
    try:
        service = get_strategy_service()
        strategies_data = await service.list_strategies(
            active_only=active_only,
            limit=limit,
            offset=offset
        )

        # strategies_data já vem como lista de dicts do SQL
        result = []
        for item in strategies_data:
            strategy = item["strategy"]
            result.append({
                "id": str(strategy["id"]),
                "name": strategy["name"],
                "description": strategy.get("description"),
                "config_type": strategy.get("config_type", "visual"),
                "symbols": strategy.get("symbols") or [],
                "timeframe": strategy.get("timeframe", "5m"),
                "is_active": strategy.get("is_active", False),
                "is_backtesting": strategy.get("is_backtesting", False),
                "bot_id": str(strategy["bot_id"]) if strategy.get("bot_id") else None,
                "created_at": strategy["created_at"].isoformat() if strategy.get("created_at") else None,
                "signals_today": item.get("signals_today", 0),
                "total_executed": item.get("total_executed", 0),
                "indicators": item.get("indicators", []),
            })

        return {
            "success": True,
            "data": result,
            "total": len(result)
        }

    except Exception as e:
        logger.error(f"Error listing strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_strategy(payload: StrategyCreate):
    """
    Create a new trading strategy
    """
    try:
        service = get_strategy_service()

        strategy = await service.create_strategy(
            name=payload.name,
            description=payload.description,
            config_type=payload.config_type,
            symbols=payload.symbols,
            timeframe=payload.timeframe,
            bot_id=payload.bot_id,
            config_yaml=payload.config_yaml,
            pinescript_source=payload.pinescript_source
        )

        return {
            "success": True,
            "data": {
                "id": str(strategy["id"]),
                "name": strategy["name"],
                "config_type": strategy.get("config_type", "visual"),
                "symbols": strategy.get("symbols") or [],
                "timeframe": strategy.get("timeframe", "5m"),
                "is_active": strategy.get("is_active", False)
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str):
    """
    Get a strategy by ID with all indicators and conditions
    """
    try:
        service = get_strategy_service()
        strategy = await service.get_strategy(strategy_id)

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {
            "success": True,
            "data": {
                "id": str(strategy["id"]),
                "name": strategy["name"],
                "description": strategy.get("description"),
                "config_type": strategy.get("config_type", "visual"),
                "symbols": strategy.get("symbols") or [],
                "timeframe": strategy.get("timeframe", "5m"),
                "is_active": strategy.get("is_active", False),
                "is_backtesting": strategy.get("is_backtesting", False),
                "bot_id": str(strategy["bot_id"]) if strategy.get("bot_id") else None,
                "config_yaml": strategy.get("config_yaml"),
                "created_at": strategy["created_at"].isoformat() if strategy.get("created_at") else None,
                "indicators": [
                    {
                        "id": str(ind["id"]),
                        "indicator_type": ind["indicator_type"],
                        "parameters": ind.get("parameters") or {},
                        "order_index": ind.get("order_index", 0)
                    }
                    for ind in strategy.get("indicators", [])
                ],
                "conditions": [
                    {
                        "id": str(cond["id"]),
                        "condition_type": cond["condition_type"],
                        "conditions": cond.get("conditions") or [],
                        "logic_operator": cond.get("logic_operator", "AND"),
                        "order_index": cond.get("order_index", 0)
                    }
                    for cond in strategy.get("conditions", [])
                ]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{strategy_id}")
async def update_strategy(strategy_id: str, payload: StrategyUpdate):
    """
    Update a strategy
    """
    try:
        service = get_strategy_service()

        updates = payload.model_dump(exclude_unset=True)
        strategy = await service.update_strategy(strategy_id, **updates)

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {
            "success": True,
            "data": {
                "id": str(strategy["id"]),
                "name": strategy["name"],
                "symbols": strategy.get("symbols") or [],
                "timeframe": strategy.get("timeframe", "5m")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """
    Delete a strategy
    """
    try:
        service = get_strategy_service()
        deleted = await service.delete_strategy(strategy_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {"success": True, "message": "Strategy deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Activation Endpoints
# ============================================================================

@router.post("/{strategy_id}/activate")
async def activate_strategy(strategy_id: str):
    """
    Activate a strategy for live trading
    """
    try:
        service = get_strategy_service()
        strategy = await service.activate_strategy(strategy_id)

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Reload strategy engine
        engine = get_strategy_engine(transaction_db)
        await engine.reload_strategies()

        return {
            "success": True,
            "message": f"Strategy '{strategy['name']}' activated",
            "data": {
                "id": str(strategy["id"]),
                "is_active": strategy.get("is_active", True)
            }
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error activating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_id}/deactivate")
async def deactivate_strategy(strategy_id: str):
    """
    Deactivate a strategy
    """
    try:
        service = get_strategy_service()
        strategy = await service.deactivate_strategy(strategy_id)

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Reload strategy engine
        engine = get_strategy_engine(transaction_db)
        await engine.reload_strategies()

        return {
            "success": True,
            "message": f"Strategy '{strategy['name']}' deactivated",
            "data": {
                "id": str(strategy["id"]),
                "is_active": strategy.get("is_active", False)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Indicator Endpoints
# ============================================================================

@router.get("/{strategy_id}/indicators")
async def get_indicators(strategy_id: str):
    """
    Get all indicators for a strategy
    """
    try:
        service = get_strategy_service()
        indicators = await service.get_indicators(strategy_id)

        return {
            "success": True,
            "data": [
                {
                    "id": str(ind["id"]),
                    "indicator_type": ind["indicator_type"],
                    "parameters": ind.get("parameters") or {},
                    "order_index": ind.get("order_index", 0)
                }
                for ind in indicators
            ]
        }

    except Exception as e:
        logger.error(f"Error getting indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_id}/indicators")
async def add_indicator(strategy_id: str, payload: IndicatorCreate):
    """
    Add an indicator to a strategy
    """
    try:
        service = get_strategy_service()

        indicator = await service.add_indicator(
            strategy_id=strategy_id,
            indicator_type=payload.indicator_type,
            parameters=payload.parameters,
            order_index=payload.order_index
        )

        if not indicator:
            raise HTTPException(status_code=400, detail="Failed to create indicator")

        return {
            "success": True,
            "data": {
                "id": str(indicator["id"]),
                "indicator_type": indicator["indicator_type"],
                "parameters": indicator.get("parameters") or {}
            }
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding indicator: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{strategy_id}/indicators/{indicator_id}")
async def remove_indicator(strategy_id: str, indicator_id: str):
    """
    Remove an indicator from a strategy
    """
    try:
        service = get_strategy_service()
        deleted = await service.remove_indicator(indicator_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Indicator not found")

        return {"success": True, "message": "Indicator removed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing indicator: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Condition Endpoints
# ============================================================================

@router.get("/{strategy_id}/conditions")
async def get_conditions(strategy_id: str):
    """
    Get all conditions for a strategy
    """
    try:
        service = get_strategy_service()
        conditions = await service.get_conditions(strategy_id)

        return {
            "success": True,
            "data": [
                {
                    "id": str(cond["id"]),
                    "condition_type": cond["condition_type"],
                    "conditions": cond.get("conditions") or [],
                    "logic_operator": cond.get("logic_operator", "AND"),
                    "order_index": cond.get("order_index", 0)
                }
                for cond in conditions
            ]
        }

    except Exception as e:
        logger.error(f"Error getting conditions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_id}/conditions")
async def add_condition(strategy_id: str, payload: ConditionCreate):
    """
    Add a condition to a strategy
    """
    try:
        service = get_strategy_service()

        condition = await service.add_condition(
            strategy_id=strategy_id,
            condition_type=payload.condition_type,
            conditions=payload.conditions,
            logic_operator=payload.logic_operator,
            order_index=payload.order_index
        )

        if not condition:
            raise HTTPException(status_code=400, detail="Failed to create condition")

        return {
            "success": True,
            "data": {
                "id": str(condition["id"]),
                "condition_type": condition["condition_type"],
                "conditions": condition.get("conditions") or []
            }
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding condition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{strategy_id}/conditions/{condition_id}")
async def remove_condition(strategy_id: str, condition_id: str):
    """
    Remove a condition from a strategy
    """
    try:
        service = get_strategy_service()
        deleted = await service.remove_condition(condition_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Condition not found")

        return {"success": True, "message": "Condition removed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing condition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# YAML Configuration Endpoints
# ============================================================================

@router.post("/{strategy_id}/apply-yaml")
async def apply_yaml_config(strategy_id: str, payload: YamlConfigApply):
    """
    Apply YAML configuration to a strategy

    This will parse the YAML and create/update indicators and conditions.
    """
    try:
        service = get_strategy_service()
        strategy = await service.apply_yaml_config(strategy_id, payload.yaml_content)

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {
            "success": True,
            "message": "YAML configuration applied",
            "data": {
                "id": str(strategy["id"]),
                "config_type": strategy.get("config_type", "yaml")
            }
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error applying YAML config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/yaml")
async def get_yaml_template(
    indicators: Optional[str] = Query(None, description="Comma-separated indicator types"),
    symbols: Optional[str] = Query(None, description="Comma-separated symbols"),
):
    """
    Get a YAML configuration template
    """
    try:
        service = get_strategy_service()

        indicator_list = indicators.split(",") if indicators else None
        symbol_list = symbols.split(",") if symbols else None

        template = service.generate_yaml_template(
            indicator_types=indicator_list,
            symbols=symbol_list
        )

        return {
            "success": True,
            "data": {
                "template": template
            }
        }

    except Exception as e:
        logger.error(f"Error generating YAML template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Bot Linking Endpoints
# ============================================================================

@router.post("/{strategy_id}/link-bot/{bot_id}")
async def link_bot(strategy_id: str, bot_id: str):
    """
    Link a strategy to a bot for signal execution
    """
    try:
        service = get_strategy_service()
        strategy = await service.update_strategy(strategy_id, bot_id=bot_id)

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {
            "success": True,
            "message": "Strategy linked to bot",
            "data": {
                "strategy_id": str(strategy["id"]),
                "bot_id": strategy.get("bot_id")
            }
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error linking bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{strategy_id}/unlink-bot")
async def unlink_bot(strategy_id: str):
    """
    Unlink a strategy from its bot
    """
    try:
        service = get_strategy_service()
        strategy = await service.update_strategy(strategy_id, bot_id=None)

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {
            "success": True,
            "message": "Strategy unlinked from bot",
            "data": {
                "strategy_id": str(strategy["id"]),
                "bot_id": None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unlinking bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Signals Endpoints
# ============================================================================

@router.get("/{strategy_id}/signals")
async def get_signals(
    strategy_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    Get signals generated by a strategy
    """
    try:
        service = get_strategy_service()
        signals = await service.get_signals(strategy_id, limit=limit, offset=offset)

        return {
            "success": True,
            "data": [
                {
                    "id": str(sig["id"]),
                    "symbol": sig["symbol"],
                    "signal_type": sig["signal_type"],
                    "entry_price": float(sig["entry_price"]) if sig.get("entry_price") else None,
                    "status": sig.get("status", "pending"),
                    "indicator_values": sig.get("indicator_values"),
                    "created_at": sig["created_at"].isoformat() if sig.get("created_at") else None
                }
                for sig in signals
            ]
        }

    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/recent")
async def get_recent_signals(
    limit: int = Query(default=50, ge=1, le=200),
    symbol: Optional[str] = None,
):
    """
    Get recent signals across all strategies
    """
    try:
        service = get_strategy_service()
        signals = await service.get_recent_signals(limit=limit, symbol=symbol)

        return {
            "success": True,
            "data": [
                {
                    "id": str(sig["id"]),
                    "strategy_id": str(sig["strategy_id"]),
                    "symbol": sig["symbol"],
                    "signal_type": sig["signal_type"],
                    "entry_price": float(sig["entry_price"]) if sig.get("entry_price") else None,
                    "status": sig.get("status", "pending"),
                    "created_at": sig["created_at"].isoformat() if sig.get("created_at") else None
                }
                for sig in signals
            ]
        }

    except Exception as e:
        logger.error(f"Error getting recent signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Backtest Endpoints
# ============================================================================

@router.get("/{strategy_id}/backtest/results")
async def get_backtest_results(
    strategy_id: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    """
    Get backtest results for a strategy
    """
    try:
        service = get_strategy_service()
        results = await service.get_backtest_results(strategy_id, limit=limit)

        return {
            "success": True,
            "data": [
                {
                    "id": str(r["id"]),
                    "symbol": r["symbol"],
                    "start_date": r["start_date"].isoformat() if r.get("start_date") else None,
                    "end_date": r["end_date"].isoformat() if r.get("end_date") else None,
                    "total_trades": r.get("total_trades", 0),
                    "win_rate": float(r["win_rate"]) if r.get("win_rate") else None,
                    "total_pnl_percent": float(r["total_pnl_percent"]) if r.get("total_pnl_percent") else None,
                    "max_drawdown": float(r["max_drawdown"]) if r.get("max_drawdown") else None,
                    "created_at": r["created_at"].isoformat() if r.get("created_at") else None
                }
                for r in results
            ]
        }

    except Exception as e:
        logger.error(f"Error getting backtest results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}/backtest/results/{result_id}")
async def get_backtest_result_detail(strategy_id: str, result_id: str):
    """
    Get detailed backtest result including trades and equity curve
    """
    try:
        service = get_strategy_service()
        result = await service.get_backtest_result(result_id)

        if not result or str(result.get("strategy_id")) != strategy_id:
            raise HTTPException(status_code=404, detail="Backtest result not found")

        return {
            "success": True,
            "data": {
                "id": str(result["id"]),
                "strategy_id": str(result["strategy_id"]),
                "symbol": result["symbol"],
                "start_date": result["start_date"].isoformat() if result.get("start_date") else None,
                "end_date": result["end_date"].isoformat() if result.get("end_date") else None,
                "config": {
                    "initial_capital": float(result["initial_capital"]) if result.get("initial_capital") else 10000,
                    "leverage": result.get("leverage", 10),
                    "margin_percent": float(result["margin_percent"]) if result.get("margin_percent") else 5.0,
                    "stop_loss_percent": float(result["stop_loss_percent"]) if result.get("stop_loss_percent") else 2.0,
                    "take_profit_percent": float(result["take_profit_percent"]) if result.get("take_profit_percent") else 4.0,
                    "include_fees": result.get("include_fees", True),
                    "include_slippage": result.get("include_slippage", True)
                },
                "metrics": {
                    "total_trades": result.get("total_trades", 0),
                    "winning_trades": result.get("winning_trades", 0),
                    "losing_trades": result.get("losing_trades", 0),
                    "win_rate": float(result["win_rate"]) if result.get("win_rate") else None,
                    "profit_factor": float(result["profit_factor"]) if result.get("profit_factor") else None,
                    "total_pnl": float(result["total_pnl"]) if result.get("total_pnl") else None,
                    "total_pnl_percent": float(result["total_pnl_percent"]) if result.get("total_pnl_percent") else None,
                    "max_drawdown": float(result["max_drawdown"]) if result.get("max_drawdown") else None,
                    "sharpe_ratio": float(result["sharpe_ratio"]) if result.get("sharpe_ratio") else None,
                },
                "trades": result.get("trades"),
                "equity_curve": result.get("equity_curve"),
                "created_at": result["created_at"].isoformat() if result.get("created_at") else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest result detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Engine Status Endpoints
# ============================================================================

@router.get("/engine/status")
async def get_engine_status():
    """
    Get the status of the Strategy Engine
    """
    try:
        engine = get_strategy_engine(transaction_db)
        status = engine.get_status()

        return {
            "success": True,
            "data": status
        }

    except Exception as e:
        logger.error(f"Error getting engine status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/engine/reload")
async def reload_engine():
    """
    Force reload of all active strategies in the engine
    """
    try:
        engine = get_strategy_engine(transaction_db)
        await engine.reload_strategies()

        status = engine.get_status()

        return {
            "success": True,
            "message": "Strategy engine reloaded",
            "data": status
        }

    except Exception as e:
        logger.error(f"Error reloading engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PineScript / TradingView Webhook Endpoint
# ============================================================================

@router.post("/pinescript-webhook")
async def pinescript_webhook(payload: PineScriptWebhookPayload):
    """
    Receive webhook alerts from TradingView/PineScript strategies.

    This endpoint:
    1. Validates the secret against stored strategy configs
    2. Creates a signal in the database
    3. Forwards to bot_broadcast_service for execution (if strategy is linked to a bot)

    Expected JSON payload from TradingView alert:
    {
        "secret": "ps_xxxxx",
        "action": "buy" | "sell" | "close" | "close_long" | "close_short",
        "ticker": "BTCUSDT",
        "price": 42000.50,
        "quantity": 0.1,
        "position_size": 1,
        "comment": "Entry signal from my strategy"
    }
    """
    try:
        logger.info(f"PineScript webhook received: {payload.action} {payload.ticker}")

        service = get_strategy_service()

        # Find strategy by webhook secret
        strategy = await service.find_strategy_by_pinescript_secret(payload.secret)

        if not strategy:
            logger.warning(f"Invalid webhook secret: {payload.secret[:10]}...")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

        # Check if strategy is active
        if not strategy.get("is_active", False):
            logger.warning(f"Strategy {strategy['id']} is not active")
            raise HTTPException(status_code=400, detail="Strategy is not active")

        # Check if symbol is allowed (if strategy has symbol restrictions)
        allowed_symbols = strategy.get("symbols") or []
        if allowed_symbols and payload.ticker not in allowed_symbols:
            logger.warning(f"Symbol {payload.ticker} not allowed for strategy {strategy['id']}")
            raise HTTPException(
                status_code=400,
                detail=f"Symbol {payload.ticker} not allowed for this strategy"
            )

        # Map action to signal type
        signal_type_map = {
            "buy": "entry_long",
            "sell": "entry_short",
            "close": "exit_all",
            "close_long": "exit_long",
            "close_short": "exit_short"
        }
        signal_type = signal_type_map.get(payload.action, payload.action)

        # Create signal in database
        signal = await service.create_signal(
            strategy_id=str(strategy["id"]),
            symbol=payload.ticker,
            signal_type=signal_type,
            entry_price=payload.price,
            indicator_values={
                "source": "pinescript",
                "comment": payload.comment,
                "quantity": payload.quantity,
                "position_size": payload.position_size,
                "leverage_override": payload.leverage,
                "stop_loss": payload.stop_loss,
                "take_profit": payload.take_profit
            }
        )

        response_data = {
            "signal_id": str(signal["id"]),
            "strategy_id": str(strategy["id"]),
            "strategy_name": strategy.get("name"),
            "symbol": payload.ticker,
            "action": payload.action,
            "signal_type": signal_type,
            "status": "created"
        }

        # If strategy is linked to a bot, execute via bot_broadcast_service
        bot_id = strategy.get("bot_id")
        if bot_id:
            try:
                # Import here to avoid circular imports
                from infrastructure.services.bot_broadcast_service import BotBroadcastService

                broadcast_service = BotBroadcastService(transaction_db)

                # Determine direction
                direction = "LONG" if payload.action in ["buy", "close_short"] else "SHORT"

                # Get leverage and margin from strategy config or payload
                pinescript_config = {}
                if strategy.get("pinescript_source"):
                    import json
                    try:
                        pinescript_config = json.loads(strategy["pinescript_source"])
                    except:
                        pass

                leverage = payload.leverage or pinescript_config.get("default_leverage", 10)
                margin_pct = pinescript_config.get("default_margin_pct", 5.0)

                # Execute via bot broadcast
                execution_result = await broadcast_service.broadcast_signal(
                    bot_id=str(bot_id),
                    ticker=payload.ticker,
                    direction=direction,
                    entry_price=payload.price,
                    leverage=leverage,
                    margin_percent=margin_pct,
                    stop_loss_price=payload.stop_loss,
                    take_profit_price=payload.take_profit,
                    signal_source=f"pinescript:{strategy['name']}"
                )

                response_data["execution"] = {
                    "bot_id": str(bot_id),
                    "status": "executed" if execution_result else "failed",
                    "result": execution_result
                }

                # Update signal status
                await service.update_signal_status(
                    str(signal["id"]),
                    status="executed" if execution_result else "failed"
                )

                logger.info(f"PineScript signal executed via bot {bot_id}: {execution_result}")

            except Exception as exec_error:
                logger.error(f"Error executing PineScript signal via bot: {exec_error}")
                response_data["execution"] = {
                    "bot_id": str(bot_id),
                    "status": "error",
                    "error": str(exec_error)
                }
                await service.update_signal_status(str(signal["id"]), status="failed")
        else:
            response_data["execution"] = {
                "status": "no_bot",
                "message": "Strategy not linked to any bot - signal recorded but not executed"
            }

        return {
            "success": True,
            "message": f"PineScript signal processed: {payload.action} {payload.ticker}",
            "data": response_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PineScript webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
