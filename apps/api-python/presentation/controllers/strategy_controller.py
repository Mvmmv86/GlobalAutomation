"""
Strategy Controller
Handles all strategy-related endpoints (CRUD, backtest, signals, engine status)
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import structlog

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.database.models.strategy import (
    ConfigType,
    ConditionType,
    IndicatorType,
    LogicOperator,
)
from infrastructure.services.strategy_service import StrategyService
from infrastructure.services.backtest_service import BacktestService, BacktestConfig
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
        service = StrategyService(transaction_db)
        strategies = await service.list_strategies(
            active_only=active_only,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "data": strategies,
            "total": len(strategies)
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
        service = StrategyService(transaction_db)

        strategy = await service.create_strategy(
            name=payload.name,
            description=payload.description,
            config_type=ConfigType(payload.config_type),
            symbols=payload.symbols,
            timeframe=payload.timeframe,
            bot_id=payload.bot_id,
            config_yaml=payload.config_yaml,
            pinescript_source=payload.pinescript_source
        )

        return {
            "success": True,
            "data": {
                "id": str(strategy.id),
                "name": strategy.name,
                "config_type": strategy.config_type.value,
                "symbols": strategy.symbols,
                "timeframe": strategy.timeframe,
                "is_active": strategy.is_active
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
        service = StrategyService(transaction_db)
        strategy = await service.get_strategy(strategy_id)

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {
            "success": True,
            "data": {
                "id": str(strategy.id),
                "name": strategy.name,
                "description": strategy.description,
                "config_type": strategy.config_type.value,
                "symbols": strategy.symbols,
                "timeframe": strategy.timeframe,
                "is_active": strategy.is_active,
                "is_backtesting": strategy.is_backtesting,
                "bot_id": strategy.bot_id,
                "config_yaml": strategy.config_yaml,
                "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
                "indicators": [
                    {
                        "id": str(ind.id),
                        "indicator_type": ind.indicator_type.value,
                        "parameters": ind.parameters,
                        "order_index": ind.order_index
                    }
                    for ind in strategy.indicators
                ],
                "conditions": [
                    {
                        "id": str(cond.id),
                        "condition_type": cond.condition_type.value,
                        "conditions": cond.conditions,
                        "logic_operator": cond.logic_operator.value,
                        "order_index": cond.order_index
                    }
                    for cond in strategy.conditions
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
        service = StrategyService(transaction_db)

        updates = payload.model_dump(exclude_unset=True)
        strategy = await service.update_strategy(strategy_id, **updates)

        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {
            "success": True,
            "data": {
                "id": str(strategy.id),
                "name": strategy.name,
                "symbols": strategy.symbols,
                "timeframe": strategy.timeframe
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
        service = StrategyService(transaction_db)
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
        service = StrategyService(transaction_db)
        strategy = await service.activate_strategy(strategy_id)

        # Reload strategy engine
        engine = get_strategy_engine(transaction_db)
        await engine.reload_strategies()

        return {
            "success": True,
            "message": f"Strategy '{strategy.name}' activated",
            "data": {
                "id": str(strategy.id),
                "is_active": strategy.is_active
            }
        }

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
        service = StrategyService(transaction_db)
        strategy = await service.deactivate_strategy(strategy_id)

        # Reload strategy engine
        engine = get_strategy_engine(transaction_db)
        await engine.reload_strategies()

        return {
            "success": True,
            "message": f"Strategy '{strategy.name}' deactivated",
            "data": {
                "id": str(strategy.id),
                "is_active": strategy.is_active
            }
        }

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
        service = StrategyService(transaction_db)
        indicators = await service.get_indicators(strategy_id)

        return {
            "success": True,
            "data": [
                {
                    "id": str(ind.id),
                    "indicator_type": ind.indicator_type.value,
                    "parameters": ind.parameters,
                    "order_index": ind.order_index
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
        service = StrategyService(transaction_db)

        indicator = await service.add_indicator(
            strategy_id=strategy_id,
            indicator_type=IndicatorType(payload.indicator_type),
            parameters=payload.parameters,
            order_index=payload.order_index
        )

        return {
            "success": True,
            "data": {
                "id": str(indicator.id),
                "indicator_type": indicator.indicator_type.value,
                "parameters": indicator.parameters
            }
        }

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
        service = StrategyService(transaction_db)
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
        service = StrategyService(transaction_db)
        conditions = await service.get_conditions(strategy_id)

        return {
            "success": True,
            "data": [
                {
                    "id": str(cond.id),
                    "condition_type": cond.condition_type.value,
                    "conditions": cond.conditions,
                    "logic_operator": cond.logic_operator.value,
                    "order_index": cond.order_index
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
        service = StrategyService(transaction_db)

        condition = await service.add_condition(
            strategy_id=strategy_id,
            condition_type=ConditionType(payload.condition_type),
            conditions=payload.conditions,
            logic_operator=LogicOperator(payload.logic_operator),
            order_index=payload.order_index
        )

        return {
            "success": True,
            "data": {
                "id": str(condition.id),
                "condition_type": condition.condition_type.value,
                "conditions": condition.conditions
            }
        }

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
        service = StrategyService(transaction_db)
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
        service = StrategyService(transaction_db)
        strategy = await service.apply_yaml_config(strategy_id, payload.yaml_content)

        return {
            "success": True,
            "message": "YAML configuration applied",
            "data": {
                "id": str(strategy.id),
                "config_type": strategy.config_type.value
            }
        }

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
        service = StrategyService(transaction_db)

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
        service = StrategyService(transaction_db)
        strategy = await service.link_bot(strategy_id, bot_id)

        return {
            "success": True,
            "message": "Strategy linked to bot",
            "data": {
                "strategy_id": str(strategy.id),
                "bot_id": strategy.bot_id
            }
        }

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
        service = StrategyService(transaction_db)
        strategy = await service.unlink_bot(strategy_id)

        return {
            "success": True,
            "message": "Strategy unlinked from bot",
            "data": {
                "strategy_id": str(strategy.id),
                "bot_id": None
            }
        }

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
        service = StrategyService(transaction_db)
        signals = await service.get_signals(strategy_id, limit=limit, offset=offset)

        return {
            "success": True,
            "data": [
                {
                    "id": str(sig.id),
                    "symbol": sig.symbol,
                    "signal_type": sig.signal_type.value,
                    "entry_price": float(sig.entry_price) if sig.entry_price else None,
                    "status": sig.status.value,
                    "indicator_values": sig.indicator_values,
                    "created_at": sig.created_at.isoformat() if sig.created_at else None
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
        service = StrategyService(transaction_db)
        signals = await service.get_recent_signals(limit=limit, symbol=symbol)

        return {
            "success": True,
            "data": [
                {
                    "id": str(sig.id),
                    "strategy_id": sig.strategy_id,
                    "symbol": sig.symbol,
                    "signal_type": sig.signal_type.value,
                    "entry_price": float(sig.entry_price) if sig.entry_price else None,
                    "status": sig.status.value,
                    "created_at": sig.created_at.isoformat() if sig.created_at else None
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

@router.post("/{strategy_id}/backtest")
async def run_backtest(strategy_id: str, payload: BacktestRequest):
    """
    Run a backtest for a strategy

    This will simulate the strategy on historical data and return performance metrics.
    """
    try:
        service = BacktestService(transaction_db)

        config = BacktestConfig(
            initial_capital=Decimal(str(payload.initial_capital)),
            leverage=payload.leverage,
            margin_percent=Decimal(str(payload.margin_percent)),
            stop_loss_percent=Decimal(str(payload.stop_loss_percent)),
            take_profit_percent=Decimal(str(payload.take_profit_percent)),
            include_fees=payload.include_fees,
            include_slippage=payload.include_slippage
        )

        result = await service.run_backtest(
            strategy_id=strategy_id,
            symbol=payload.symbol,
            start_date=payload.start_date,
            end_date=payload.end_date,
            config=config
        )

        return {
            "success": True,
            "data": {
                "id": str(result.id),
                "strategy_id": str(result.strategy_id),
                "symbol": result.symbol,
                "start_date": result.start_date.isoformat(),
                "end_date": result.end_date.isoformat(),
                "metrics": {
                    "total_trades": result.total_trades,
                    "winning_trades": result.winning_trades,
                    "losing_trades": result.losing_trades,
                    "win_rate": float(result.win_rate) if result.win_rate else None,
                    "profit_factor": float(result.profit_factor) if result.profit_factor else None,
                    "total_pnl": float(result.total_pnl) if result.total_pnl else None,
                    "total_pnl_percent": float(result.total_pnl_percent) if result.total_pnl_percent else None,
                    "max_drawdown": float(result.max_drawdown) if result.max_drawdown else None,
                    "sharpe_ratio": float(result.sharpe_ratio) if result.sharpe_ratio else None,
                },
                "trades_count": len(result.trades) if result.trades else 0,
                "equity_curve_points": len(result.equity_curve) if result.equity_curve else 0
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}/backtest/results")
async def get_backtest_results(
    strategy_id: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    """
    Get backtest results for a strategy
    """
    try:
        strategy_service = StrategyService(transaction_db)
        results = await strategy_service.get_backtest_results(strategy_id, limit=limit)

        return {
            "success": True,
            "data": [
                {
                    "id": str(r.id),
                    "symbol": r.symbol,
                    "start_date": r.start_date.isoformat(),
                    "end_date": r.end_date.isoformat(),
                    "total_trades": r.total_trades,
                    "win_rate": float(r.win_rate) if r.win_rate else None,
                    "total_pnl_percent": float(r.total_pnl_percent) if r.total_pnl_percent else None,
                    "max_drawdown": float(r.max_drawdown) if r.max_drawdown else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None
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
        from infrastructure.database.repositories.strategy import StrategyBacktestResultRepository

        repo = StrategyBacktestResultRepository(transaction_db)
        result = await repo.get(result_id)

        if not result or str(result.strategy_id) != strategy_id:
            raise HTTPException(status_code=404, detail="Backtest result not found")

        return {
            "success": True,
            "data": {
                "id": str(result.id),
                "strategy_id": str(result.strategy_id),
                "symbol": result.symbol,
                "start_date": result.start_date.isoformat(),
                "end_date": result.end_date.isoformat(),
                "config": {
                    "initial_capital": float(result.initial_capital),
                    "leverage": result.leverage,
                    "margin_percent": float(result.margin_percent),
                    "stop_loss_percent": float(result.stop_loss_percent),
                    "take_profit_percent": float(result.take_profit_percent),
                    "include_fees": result.include_fees,
                    "include_slippage": result.include_slippage
                },
                "metrics": {
                    "total_trades": result.total_trades,
                    "winning_trades": result.winning_trades,
                    "losing_trades": result.losing_trades,
                    "win_rate": float(result.win_rate) if result.win_rate else None,
                    "profit_factor": float(result.profit_factor) if result.profit_factor else None,
                    "total_pnl": float(result.total_pnl) if result.total_pnl else None,
                    "total_pnl_percent": float(result.total_pnl_percent) if result.total_pnl_percent else None,
                    "max_drawdown": float(result.max_drawdown) if result.max_drawdown else None,
                    "sharpe_ratio": float(result.sharpe_ratio) if result.sharpe_ratio else None,
                },
                "trades": result.trades,
                "equity_curve": result.equity_curve,
                "created_at": result.created_at.isoformat() if result.created_at else None
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
