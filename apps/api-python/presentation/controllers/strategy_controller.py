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

from infrastructure.database.connection import database_manager
from infrastructure.database.models.strategy import (
    ConfigType,
    ConditionType,
    IndicatorType,
    LogicOperator,
)
from infrastructure.services.strategy_service import StrategyService
from infrastructure.services.backtest_service import BacktestService, BacktestConfig
from infrastructure.services.advanced_backtest_service import (
    AdvancedBacktestService,
    AdvancedBacktestConfig,
    StressTestConfig,
    StressScenario,
    WalkForwardConfig,
    MonteCarloConfig,
    DataSource,
)
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
    indicator_type: str = Field(
        ...,
        pattern="^(nadaraya_watson|tpo|rsi|macd|ema|ema_cross|bollinger|atr|volume_profile|stochastic|stochastic_rsi|supertrend|adx|vwap|ichimoku|obv)$"
    )
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


class StrategySyncPayload(BaseModel):
    """Model for atomic sync of strategy with all indicators and conditions"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    symbols: Optional[List[str]] = None
    timeframe: Optional[str] = Field(None, pattern="^(1m|3m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d|3d|1w)$")
    bot_id: Optional[str] = None
    indicators: List[IndicatorCreate] = Field(default_factory=list)
    conditions: List[ConditionCreate] = Field(default_factory=list)


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
        async with database_manager.get_session() as session:
            service = StrategyService(session)
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
        async with database_manager.get_session() as session:
            service = StrategyService(session)

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

            await session.commit()

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
        async with database_manager.get_session() as session:
            service = StrategyService(session)
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
                    "documentation": strategy.documentation,
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


async def _do_update_strategy(strategy_id: str, payload: StrategyUpdate):
    """Internal function to update a strategy"""
    async with database_manager.get_session() as session:
        service = StrategyService(session)

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


@router.put("/{strategy_id}")
async def update_strategy_put(strategy_id: str, payload: StrategyUpdate):
    """Update a strategy (PUT)"""
    try:
        return await _do_update_strategy(strategy_id, payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{strategy_id}")
async def update_strategy_patch(strategy_id: str, payload: StrategyUpdate):
    """Update a strategy (PATCH)"""
    try:
        return await _do_update_strategy(strategy_id, payload)
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
        async with database_manager.get_session() as session:
            service = StrategyService(session)
            deleted = await service.delete_strategy(strategy_id)

            if not deleted:
                raise HTTPException(status_code=404, detail="Strategy not found")

            return {"success": True, "message": "Strategy deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{strategy_id}/sync")
async def sync_strategy(strategy_id: str, payload: StrategySyncPayload):
    """
    Atomic sync of strategy with all indicators and conditions.

    This endpoint replaces the entire strategy configuration in a single atomic operation:
    1. Updates basic info (name, description, symbols, timeframe, bot_id)
    2. Deletes ALL existing indicators
    3. Deletes ALL existing conditions
    4. Creates new indicators from payload
    5. Creates new conditions from payload

    All operations happen in a single transaction to prevent duplicates.
    """
    from infrastructure.database.connection_transaction_mode import transaction_db
    import uuid
    import json

    try:
        # Verify strategy exists
        strategy_row = await transaction_db.fetchrow(
            "SELECT id, name FROM strategies WHERE id = $1",
            strategy_id
        )

        if not strategy_row:
            raise HTTPException(status_code=404, detail="Strategy not found")

        # Build update fields for basic info
        update_fields = []
        update_values = []
        param_idx = 1

        if payload.name is not None:
            update_fields.append(f"name = ${param_idx}")
            update_values.append(payload.name)
            param_idx += 1

        if payload.description is not None:
            update_fields.append(f"description = ${param_idx}")
            update_values.append(payload.description)
            param_idx += 1

        if payload.symbols is not None:
            update_fields.append(f"symbols = ${param_idx}")
            # Convert list to JSON string for PostgreSQL
            update_values.append(json.dumps(payload.symbols))
            param_idx += 1

        if payload.timeframe is not None:
            update_fields.append(f"timeframe = ${param_idx}")
            update_values.append(payload.timeframe)
            param_idx += 1

        if payload.bot_id is not None:
            update_fields.append(f"bot_id = ${param_idx}")
            update_values.append(payload.bot_id if payload.bot_id else None)
            param_idx += 1

        # Add updated_at
        update_fields.append("updated_at = NOW()")

        # 1. Update basic info
        if update_fields:
            update_values.append(strategy_id)
            await transaction_db.execute(
                f"UPDATE strategies SET {', '.join(update_fields)} WHERE id = ${param_idx}",
                *update_values
            )

        # 2. Delete ALL existing indicators atomically
        deleted_indicators = await transaction_db.fetchval(
            "DELETE FROM strategy_indicators WHERE strategy_id = $1 RETURNING id",
            strategy_id
        )
        logger.info(f"Deleted existing indicators for strategy {strategy_id}")

        # 3. Delete ALL existing conditions atomically
        deleted_conditions = await transaction_db.fetchval(
            "DELETE FROM strategy_conditions WHERE strategy_id = $1 RETURNING id",
            strategy_id
        )
        logger.info(f"Deleted existing conditions for strategy {strategy_id}")

        # 4. Create new indicators
        created_indicators = []
        for idx, ind in enumerate(payload.indicators):
            ind_id = str(uuid.uuid4())
            order_idx = ind.order_index if ind.order_index else idx
            # Convert parameters dict to JSON string
            params_json = json.dumps(ind.parameters) if ind.parameters else "{}"
            await transaction_db.execute(
                """
                INSERT INTO strategy_indicators (id, strategy_id, indicator_type, parameters, order_index, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                """,
                ind_id,
                strategy_id,
                ind.indicator_type,
                params_json,
                order_idx
            )
            created_indicators.append({
                "id": ind_id,
                "indicator_type": ind.indicator_type,
                "parameters": ind.parameters,
                "order_index": order_idx
            })

        # 5. Create new conditions
        created_conditions = []
        for idx, cond in enumerate(payload.conditions):
            cond_id = str(uuid.uuid4())
            order_idx = cond.order_index if cond.order_index else idx
            # Convert conditions list to JSON string
            conditions_json = json.dumps(cond.conditions) if cond.conditions else "[]"
            await transaction_db.execute(
                """
                INSERT INTO strategy_conditions (id, strategy_id, condition_type, conditions, logic_operator, order_index, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                """,
                cond_id,
                strategy_id,
                cond.condition_type,
                conditions_json,
                cond.logic_operator,
                order_idx
            )
            created_conditions.append({
                "id": cond_id,
                "condition_type": cond.condition_type,
                "conditions": cond.conditions,
                "logic_operator": cond.logic_operator,
                "order_index": order_idx
            })

        logger.info(
            f"Strategy synced successfully",
            strategy_id=strategy_id,
            indicators=len(created_indicators),
            conditions=len(created_conditions)
        )

        return {
            "success": True,
            "message": "Strategy synced successfully",
            "data": {
                "id": strategy_id,
                "name": payload.name or strategy_row["name"],
                "symbols": payload.symbols,
                "timeframe": payload.timeframe,
                "indicators": created_indicators,
                "conditions": created_conditions
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Activation Endpoints
# ============================================================================

@router.post("/{strategy_id}/activate")
async def activate_strategy(strategy_id: str):
    """
    Activate a strategy for live trading
    """
    from infrastructure.database.connection_transaction_mode import transaction_db

    try:
        # Use asyncpg directly to avoid prepared statement issues with pgbouncer
        # Check if strategy exists and get symbols
        row = await transaction_db.fetchrow(
            "SELECT id, name, symbols FROM strategies WHERE id = $1",
            strategy_id
        )

        if not row:
            raise ValueError(f"Strategy {strategy_id} not found")

        # Check symbols
        symbols = row["symbols"]
        if not symbols or symbols == "[]" or symbols == "":
            raise ValueError("Strategy must have at least one symbol configured")

        # Check indicators count
        indicator_count = await transaction_db.fetchval(
            "SELECT COUNT(*) FROM strategy_indicators WHERE strategy_id = $1",
            strategy_id
        )

        if not indicator_count or indicator_count == 0:
            raise ValueError("Strategy must have at least one indicator configured")

        # Activate strategy
        await transaction_db.execute(
            "UPDATE strategies SET is_active = true, updated_at = NOW() WHERE id = $1",
            strategy_id
        )

        # Try to reload strategy engine if available
        try:
            engine = get_strategy_engine(None)
            if engine:
                await engine.reload_strategies()
        except Exception as engine_error:
            logger.warning(f"Could not reload strategy engine: {engine_error}")

        return {
            "success": True,
            "message": f"Strategy '{row['name']}' activated",
            "data": {
                "id": strategy_id,
                "is_active": True
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
    from infrastructure.database.connection_transaction_mode import transaction_db

    try:
        # Use asyncpg directly to avoid prepared statement issues with pgbouncer
        # Get strategy name first
        row = await transaction_db.fetchrow(
            "SELECT name FROM strategies WHERE id = $1",
            strategy_id
        )

        if not row:
            raise ValueError(f"Strategy {strategy_id} not found")

        # Deactivate strategy
        await transaction_db.execute(
            "UPDATE strategies SET is_active = false, updated_at = NOW() WHERE id = $1",
            strategy_id
        )

        # Try to reload strategy engine if available
        try:
            engine = get_strategy_engine(None)
            if engine:
                await engine.reload_strategies()
        except Exception as engine_error:
            logger.warning(f"Could not reload strategy engine: {engine_error}")

        return {
            "success": True,
            "message": f"Strategy '{row['name']}' deactivated",
            "data": {
                "id": strategy_id,
                "is_active": False
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
        async with database_manager.get_session() as session:
            service = StrategyService(session)
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
        async with database_manager.get_session() as session:
            service = StrategyService(session)

            indicator = await service.add_indicator(
                strategy_id=strategy_id,
                indicator_type=IndicatorType(payload.indicator_type),
                parameters=payload.parameters,
                order_index=payload.order_index
            )

            await session.commit()

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
        async with database_manager.get_session() as session:
            service = StrategyService(session)
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
        async with database_manager.get_session() as session:
            service = StrategyService(session)
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
        async with database_manager.get_session() as session:
            service = StrategyService(session)

            condition = await service.add_condition(
                strategy_id=strategy_id,
                condition_type=ConditionType(payload.condition_type),
                conditions=payload.conditions,
                logic_operator=LogicOperator(payload.logic_operator),
                order_index=payload.order_index
            )

            await session.commit()

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
        async with database_manager.get_session() as session:
            service = StrategyService(session)
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
        async with database_manager.get_session() as session:
            service = StrategyService(session)
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
        async with database_manager.get_session() as session:
            service = StrategyService(session)

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
        async with database_manager.get_session() as session:
            service = StrategyService(session)
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
        async with database_manager.get_session() as session:
            service = StrategyService(session)
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
        async with database_manager.get_session() as session:
            service = StrategyService(session)
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
        async with database_manager.get_session() as session:
            service = StrategyService(session)
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

    This will simulate the strategy on historical data and return performance metrics,
    including trades, candles and indicator data for chart visualization.
    """
    try:
        async with database_manager.get_session() as session:
            service = BacktestService(session)

            config = BacktestConfig(
                initial_capital=Decimal(str(payload.initial_capital)),
                leverage=payload.leverage,
                margin_percent=Decimal(str(payload.margin_percent)),
                stop_loss_percent=Decimal(str(payload.stop_loss_percent)),
                take_profit_percent=Decimal(str(payload.take_profit_percent)),
                include_fees=payload.include_fees,
                include_slippage=payload.include_slippage
            )

            # Run backtest with chart data
            result, chart_data = await service.run_backtest_with_chart_data(
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
                    "trades": result.trades if result.trades else [],
                    "equity_curve": result.equity_curve if result.equity_curve else [],
                    "candles": chart_data.get("candles", []),
                    "indicators": chart_data.get("indicators", {})
                }
            }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error running backtest: {e}\n{tb}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e) or 'Unknown error'}")


@router.get("/{strategy_id}/backtest/results")
async def get_backtest_results(
    strategy_id: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    """
    Get backtest results for a strategy
    """
    try:
        async with database_manager.get_session() as session:
            strategy_service = StrategyService(session)
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

        async with database_manager.get_session() as session:
            repo = StrategyBacktestResultRepository(session)
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
        async with database_manager.get_session() as session:
            engine = get_strategy_engine(session)
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
        async with database_manager.get_session() as session:
            engine = get_strategy_engine(session)
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
# Documentation Endpoints
# ============================================================================

@router.get("/{strategy_id}/documentation")
async def get_strategy_documentation(strategy_id: str):
    """
    Get detailed documentation for a strategy.

    This endpoint returns comprehensive information for admins to understand:
    - What the strategy does and how it works
    - When to use it and when NOT to use it
    - Recommended assets and timeframes
    - Risk management guidelines
    - Performance expectations based on backtests
    """
    try:
        async with database_manager.get_session() as session:
            from sqlalchemy import select
            from infrastructure.database.models.strategy import Strategy

            result = await session.execute(
                select(Strategy).where(Strategy.id == strategy_id)
            )
            strategy = result.scalar_one_or_none()

            if not strategy:
                raise HTTPException(status_code=404, detail="Strategy not found")

            return {
                "success": True,
                "data": {
                    "id": str(strategy.id),
                    "name": strategy.name,
                    "timeframe": strategy.timeframe,
                    "symbols": strategy.symbols,
                    "documentation": strategy.documentation or {}
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/all")
async def get_strategies_catalog():
    """
    Get a catalog of all available strategies with their documentation summaries.

    This is useful for admins to compare and choose between strategies.
    Returns a summary of each strategy including:
    - Basic info (name, timeframe, assets)
    - Performance expectations
    - Experience level required
    - When to use
    """
    try:
        async with database_manager.get_session() as session:
            from sqlalchemy import select
            from infrastructure.database.models.strategy import Strategy

            result = await session.execute(
                select(Strategy).order_by(Strategy.created_at)
            )
            strategies = result.scalars().all()

            catalog = []
            for s in strategies:
                docs = s.documentation or {}
                catalog.append({
                    "id": str(s.id),
                    "name": s.name,
                    "timeframe": s.timeframe,
                    "symbols": s.symbols,
                    "is_active": s.is_active,
                    "summary": {
                        "titulo": docs.get("titulo", s.name),
                        "resumo": docs.get("resumo", s.description or ""),
                        "sharpe_ratio": docs.get("performance_esperada", {}).get("sharpe_ratio", "N/A"),
                        "win_rate": docs.get("performance_esperada", {}).get("win_rate", "N/A"),
                        "nivel_experiencia": docs.get("nivel_experiencia", "N/A"),
                        "complexidade": docs.get("complexidade", "N/A"),
                        "baseado_em": docs.get("baseado_em", {}).get("fonte", "N/A")
                    }
                })

            return {
                "success": True,
                "total": len(catalog),
                "data": catalog
            }

    except Exception as e:
        logger.error(f"Error getting strategies catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Advanced Backtest Endpoints
# ============================================================================

class AdvancedBacktestRequest(BaseModel):
    """Model for running an advanced backtest"""
    symbols: List[str] = Field(default=["BTCUSDT"], min_items=1)
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(default=10000, ge=100)
    leverage: int = Field(default=10, ge=1, le=125)
    margin_percent: float = Field(default=5.0, ge=1, le=100)
    stop_loss_percent: float = Field(default=2.0, ge=0.1, le=50)
    take_profit_percent: float = Field(default=4.0, ge=0.1, le=100)

    # Multi-asset options
    portfolio_mode: bool = Field(default=False, description="Distribute capital across assets")
    equal_weight: bool = Field(default=True, description="Equal weight for each asset")

    # Stress Test options
    enable_stress_test: bool = Field(default=False)
    stress_scenarios: List[str] = Field(
        default=[],
        description="Scenarios: flash_crash, black_swan, liquidity_crisis, extreme_vol"
    )

    # Walk-Forward options
    enable_walk_forward: bool = Field(default=False)
    walk_forward_folds: int = Field(default=5, ge=2, le=20)
    in_sample_ratio: float = Field(default=0.7, ge=0.5, le=0.9)

    # Monte Carlo options
    enable_monte_carlo: bool = Field(default=False)
    monte_carlo_simulations: int = Field(default=1000, ge=100, le=10000)


@router.post("/{strategy_id}/backtest/advanced")
async def run_advanced_backtest(strategy_id: str, payload: AdvancedBacktestRequest):
    """
    Run an advanced backtest with professional features:

    - **Multi-Asset**: Test on multiple symbols simultaneously
    - **Long Period**: Supports 5-10+ years using SPOT data (since 2017)
    - **Stress Testing**: Simulate flash crashes, black swan events, liquidity crises
    - **Walk-Forward**: Validate strategy is not overfitted
    - **Monte Carlo**: Calculate Value at Risk (VaR) and probability distributions

    Returns comprehensive results including:
    - Per-asset performance metrics
    - Portfolio-level Sharpe/Sortino ratios
    - Walk-forward degradation analysis
    - VaR 95% and VaR 99%
    - Stress test survival rate
    """
    try:
        async with database_manager.get_session() as session:
            service = AdvancedBacktestService(session)

            # Build stress test config
            stress_config = StressTestConfig(
                enabled=payload.enable_stress_test,
                scenarios=[StressScenario(s) for s in payload.stress_scenarios if s in [e.value for e in StressScenario]]
            )

            # Build walk-forward config
            wf_config = WalkForwardConfig(
                enabled=payload.enable_walk_forward,
                in_sample_ratio=payload.in_sample_ratio,
                num_folds=payload.walk_forward_folds
            )

            # Build Monte Carlo config
            mc_config = MonteCarloConfig(
                enabled=payload.enable_monte_carlo,
                num_simulations=payload.monte_carlo_simulations
            )

            # Build advanced config
            config = AdvancedBacktestConfig(
                initial_capital=Decimal(str(payload.initial_capital)),
                leverage=payload.leverage,
                margin_percent=Decimal(str(payload.margin_percent)),
                stop_loss_percent=Decimal(str(payload.stop_loss_percent)),
                take_profit_percent=Decimal(str(payload.take_profit_percent)),
                data_source=DataSource.AUTO,
                symbols=payload.symbols,
                portfolio_mode=payload.portfolio_mode,
                equal_weight=payload.equal_weight,
                stress_test=stress_config,
                walk_forward=wf_config,
                monte_carlo=mc_config
            )

            result = await service.run_advanced_backtest(
                strategy_id=strategy_id,
                start_date=payload.start_date,
                end_date=payload.end_date,
                config=config
            )

            # Format response
            return {
                "success": True,
                "data": {
                    "summary": {
                        "total_pnl": float(result.total_pnl),
                        "total_pnl_percent": float(result.total_pnl_percent),
                        "portfolio_sharpe": float(result.portfolio_sharpe) if result.portfolio_sharpe else None,
                        "portfolio_sortino": float(result.portfolio_sortino) if result.portfolio_sortino else None,
                        "portfolio_max_drawdown": float(result.portfolio_max_drawdown),
                        "assets_tested": len(result.asset_results),
                    },
                    "per_asset": [
                        {
                            "symbol": ar.symbol,
                            "total_trades": ar.metrics.get("total_trades"),
                            "win_rate": ar.metrics.get("win_rate"),
                            "profit_factor": ar.metrics.get("profit_factor"),
                            "sharpe_ratio": ar.metrics.get("sharpe_ratio"),
                            "max_drawdown": ar.metrics.get("max_drawdown"),
                        }
                        for ar in result.asset_results
                    ],
                    "walk_forward": {
                        "enabled": payload.enable_walk_forward,
                        "results": result.walk_forward_results,
                        "degradation_percent": result.walk_forward_degradation,
                        "is_robust": (result.walk_forward_degradation or 0) < 30  # <30% degradation is good
                    } if payload.enable_walk_forward else None,
                    "monte_carlo": {
                        "enabled": payload.enable_monte_carlo,
                        "simulations": payload.monte_carlo_simulations,
                        "var_95": float(result.var_95) if result.var_95 else None,
                        "var_99": float(result.var_99) if result.var_99 else None,
                        "details": result.monte_carlo_results
                    } if payload.enable_monte_carlo else None,
                    "stress_test": {
                        "enabled": payload.enable_stress_test,
                        "scenarios_tested": payload.stress_scenarios,
                        "worst_case_drawdown": float(result.worst_case_drawdown) if result.worst_case_drawdown else None,
                        "survival_rate": result.survival_rate,
                        "details": result.stress_test_results
                    } if payload.enable_stress_test else None,
                }
            }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error running advanced backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest/data-availability/{symbol}")
async def get_data_availability(symbol: str):
    """
    Check data availability for a symbol.

    Returns information about how far back we can test:
    - SPOT data: Available since August 2017 (~7+ years)
    - FUTURES data: Available since September 2019 (~5+ years)

    This helps you plan backtest periods appropriately.
    """
    try:
        async with database_manager.get_session() as session:
            service = AdvancedBacktestService(session)
            availability = service.get_data_availability(symbol.upper())

            return {
                "success": True,
                "data": availability
            }

    except Exception as e:
        logger.error(f"Error checking data availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest/stress-scenarios")
async def list_stress_scenarios():
    """
    List available stress test scenarios.

    Each scenario simulates a specific market condition:
    - **flash_crash**: Sudden 30%+ drop in minutes (like May 2021)
    - **black_swan**: Historical events (COVID, FTX, Luna crashes)
    - **liquidity_crisis**: Extreme slippage and execution issues
    - **extreme_vol**: Volatility 5x normal (ATR spikes)
    - **gap_down/gap_up**: Price gaps on exchange restarts

    Use these to test strategy robustness.
    """
    scenarios = [
        {
            "id": "flash_crash",
            "name": "Flash Crash",
            "description": "Simulates a sudden 30%+ drop in prices over 5 candles, followed by partial recovery",
            "historical_examples": ["May 19, 2021 (-30%)", "March 12, 2020 (-50%)"],
            "severity": "extreme"
        },
        {
            "id": "black_swan",
            "name": "Black Swan Events",
            "description": "Tests strategy on historical catastrophic events",
            "historical_examples": [
                "COVID Crash (Mar 2020): -50% in 2 days",
                "FTX Collapse (Nov 2022): -25% in 1 week",
                "Luna Collapse (May 2022): -40% in 3 days"
            ],
            "severity": "extreme"
        },
        {
            "id": "liquidity_crisis",
            "name": "Liquidity Crisis",
            "description": "Simulates poor liquidity with 2%+ slippage on trades",
            "historical_examples": ["Flash crashes", "Exchange outages"],
            "severity": "high"
        },
        {
            "id": "extreme_vol",
            "name": "Extreme Volatility",
            "description": "Simulates periods where volatility (ATR) is 5x normal",
            "historical_examples": ["Major news events", "ETF approvals/rejections"],
            "severity": "high"
        }
    ]

    return {
        "success": True,
        "data": scenarios
    }


# Global transaction_db reference (set by main.py)
transaction_db = None


def set_transaction_db(db):
    """Set the database pool for this module"""
    global transaction_db
    transaction_db = db
