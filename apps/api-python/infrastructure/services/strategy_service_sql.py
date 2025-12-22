"""
Strategy Service using SQL direto (transaction_db)
Compativel com pgBouncer - sem SQLAlchemy ORM
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
import yaml

from infrastructure.database.repositories.strategy_sql import (
    StrategyRepositorySQL,
    StrategyIndicatorRepositorySQL,
    StrategyConditionRepositorySQL,
    StrategySignalRepositorySQL,
    StrategyBacktestResultRepositorySQL,
)

logger = structlog.get_logger(__name__)


class StrategyServiceSQL:
    """
    Strategy Service using SQL direto

    Provides high-level operations for managing trading strategies:
    - Create/Update/Delete strategies
    - Configure indicators and conditions
    - Activate/Deactivate strategies
    - Parse YAML configurations
    - Link strategies to bots
    """

    def __init__(self, db):
        self.db = db
        self._strategy_repo = StrategyRepositorySQL(db)
        self._indicator_repo = StrategyIndicatorRepositorySQL(db)
        self._condition_repo = StrategyConditionRepositorySQL(db)
        self._signal_repo = StrategySignalRepositorySQL(db)
        self._backtest_repo = StrategyBacktestResultRepositorySQL(db)

    # ==================== Strategy CRUD ====================

    async def create_strategy(
        self,
        name: str,
        description: Optional[str] = None,
        config_type: str = "visual",
        symbols: List[str] = None,
        timeframe: str = "5m",
        bot_id: Optional[str] = None,
        created_by: Optional[str] = None,
        config_yaml: Optional[str] = None,
        pinescript_source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new trading strategy"""
        strategy = await self._strategy_repo.create(
            name=name,
            description=description,
            config_type=config_type,
            symbols=symbols or [],
            timeframe=timeframe,
            bot_id=bot_id,
            created_by=created_by,
            config_yaml=config_yaml,
            pinescript_source=pinescript_source,
        )

        logger.info(f"Created strategy: {strategy['name']} ({strategy['id']})")
        return strategy

    async def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get a strategy by ID with all related data"""
        return await self._strategy_repo.get_with_relations(strategy_id)

    async def list_strategies(
        self,
        user_id: Optional[str] = None,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List strategies with statistics"""
        return await self._strategy_repo.get_strategies_with_stats(
            user_id=user_id,
            is_active=True if active_only else None,
            limit=limit,
            skip=offset
        )

    async def update_strategy(
        self,
        strategy_id: str,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """Update a strategy"""
        # Prevent updating certain fields
        updates.pop("id", None)
        updates.pop("created_at", None)
        updates.pop("created_by", None)

        return await self._strategy_repo.update(strategy_id, **updates)

    async def delete_strategy(self, strategy_id: str) -> bool:
        """Delete a strategy and all related data"""
        strategy = await self._strategy_repo.get_by_id(strategy_id)
        if not strategy:
            return False

        # Delete related data first (cascade should handle this, but being explicit)
        await self._indicator_repo.delete_by_strategy(strategy_id)
        await self._condition_repo.delete_by_strategy(strategy_id)

        result = await self._strategy_repo.delete(strategy_id)
        if result:
            logger.info(f"Deleted strategy: {strategy['name']} ({strategy_id})")
        return result

    async def activate_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Activate a strategy"""
        strategy = await self._strategy_repo.activate(strategy_id)
        if strategy:
            logger.info(f"Activated strategy: {strategy['name']}")
        return strategy

    async def deactivate_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Deactivate a strategy"""
        strategy = await self._strategy_repo.deactivate(strategy_id)
        if strategy:
            logger.info(f"Deactivated strategy: {strategy['name']}")
        return strategy

    # ==================== Indicators ====================

    async def add_indicator(
        self,
        strategy_id: str,
        indicator_type: str,
        parameters: Dict[str, Any] = None,
        order_index: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Add an indicator to a strategy"""
        indicator = await self._indicator_repo.create(
            strategy_id=strategy_id,
            indicator_type=indicator_type,
            parameters=parameters or {},
            order_index=order_index
        )
        return indicator

    async def get_indicators(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get all indicators for a strategy"""
        return await self._indicator_repo.get_by_strategy(strategy_id)

    async def remove_indicator(self, indicator_id: str) -> bool:
        """Remove an indicator"""
        return await self._indicator_repo.delete(indicator_id)

    async def clear_indicators(self, strategy_id: str) -> int:
        """Remove all indicators from a strategy"""
        return await self._indicator_repo.delete_by_strategy(strategy_id)

    # ==================== Conditions ====================

    async def add_condition(
        self,
        strategy_id: str,
        condition_type: str,
        conditions: List[Dict[str, Any]],
        logic_operator: str = "AND",
        order_index: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Add a condition to a strategy"""
        condition = await self._condition_repo.create(
            strategy_id=strategy_id,
            condition_type=condition_type,
            conditions=conditions,
            logic_operator=logic_operator,
            order_index=order_index
        )
        return condition

    async def get_conditions(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get all conditions for a strategy"""
        return await self._condition_repo.get_by_strategy(strategy_id)

    async def remove_condition(self, condition_id: str) -> bool:
        """Remove a condition"""
        return await self._condition_repo.delete(condition_id)

    async def clear_conditions(self, strategy_id: str) -> int:
        """Remove all conditions from a strategy"""
        return await self._condition_repo.delete_by_strategy(strategy_id)

    # ==================== Signals ====================

    async def get_signals(
        self,
        strategy_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get signals for a strategy"""
        return await self._signal_repo.get_by_strategy(strategy_id, offset, limit)

    async def get_recent_signals(
        self,
        limit: int = 50,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent signals across all strategies"""
        return await self._signal_repo.get_recent_all(limit, symbol)

    # ==================== Backtest Results ====================

    async def get_backtest_results(
        self,
        strategy_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get backtest results for a strategy"""
        return await self._backtest_repo.get_by_strategy(strategy_id, 0, limit)

    async def get_backtest_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific backtest result"""
        return await self._backtest_repo.get_by_id(result_id)

    # ==================== YAML Configuration ====================

    def generate_yaml_template(
        self,
        indicator_types: List[str] = None,
        symbols: List[str] = None
    ) -> str:
        """Generate a YAML configuration template"""
        template = {
            "strategy": {
                "name": "My Strategy",
                "symbols": symbols or ["BTCUSDT"],
                "timeframe": "5m"
            },
            "indicators": [],
            "conditions": {
                "entry_long": {
                    "operator": "AND",
                    "rules": []
                },
                "entry_short": {
                    "operator": "AND",
                    "rules": []
                },
                "exit_long": {
                    "operator": "OR",
                    "rules": []
                },
                "exit_short": {
                    "operator": "OR",
                    "rules": []
                }
            }
        }

        # Add indicator templates
        indicator_params = {
            "nadaraya_watson": {"bandwidth": 8, "mult": 3.0},
            "rsi": {"period": 14, "overbought": 70, "oversold": 30},
            "macd": {"fast": 12, "slow": 26, "signal": 9},
            "ema": {"period": 20},
            "bollinger": {"period": 20, "std_dev": 2},
            "atr": {"period": 14},
            "volume_profile": {"lookback": 24}
        }

        types_to_add = indicator_types or ["nadaraya_watson", "rsi"]
        for ind_type in types_to_add:
            if ind_type in indicator_params:
                template["indicators"].append({
                    "type": ind_type,
                    "params": indicator_params[ind_type]
                })

        return yaml.dump(template, default_flow_style=False, sort_keys=False)

    async def apply_yaml_config(
        self,
        strategy_id: str,
        yaml_content: str
    ) -> Dict[str, Any]:
        """Apply YAML configuration to a strategy"""
        try:
            config = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")

        # Update strategy basic info
        if "strategy" in config:
            strategy_config = config["strategy"]
            await self._strategy_repo.update(
                strategy_id,
                name=strategy_config.get("name"),
                symbols=strategy_config.get("symbols", []),
                timeframe=strategy_config.get("timeframe", "5m"),
                config_yaml=yaml_content
            )

        # Clear existing indicators and conditions
        await self._indicator_repo.delete_by_strategy(strategy_id)
        await self._condition_repo.delete_by_strategy(strategy_id)

        # Add indicators
        if "indicators" in config:
            for idx, ind in enumerate(config["indicators"]):
                await self._indicator_repo.create(
                    strategy_id=strategy_id,
                    indicator_type=ind.get("type"),
                    parameters=ind.get("params", {}),
                    order_index=idx
                )

        # Add conditions
        if "conditions" in config:
            condition_types = ["entry_long", "entry_short", "exit_long", "exit_short"]
            for idx, cond_type in enumerate(condition_types):
                if cond_type in config["conditions"]:
                    cond_config = config["conditions"][cond_type]
                    rules = cond_config.get("rules", [])
                    if rules:
                        await self._condition_repo.create(
                            strategy_id=strategy_id,
                            condition_type=cond_type,
                            conditions=rules,
                            logic_operator=cond_config.get("operator", "AND"),
                            order_index=idx
                        )

        return await self._strategy_repo.get_with_relations(strategy_id)

    # ==================== Active Strategies ====================

    async def get_active_strategies(self) -> List[Dict[str, Any]]:
        """Get all active strategies with full configuration"""
        return await self._strategy_repo.get_active_strategies()

    # ==================== PineScript Integration ====================

    async def find_strategy_by_pinescript_secret(
        self,
        secret: str
    ) -> Optional[Dict[str, Any]]:
        """Find a strategy by its PineScript webhook secret"""
        return await self._strategy_repo.find_by_pinescript_secret(secret)

    async def create_signal(
        self,
        strategy_id: str,
        symbol: str,
        signal_type: str,
        entry_price: Optional[float] = None,
        indicator_values: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new signal for a strategy"""
        return await self._signal_repo.create(
            strategy_id=strategy_id,
            symbol=symbol,
            signal_type=signal_type,
            entry_price=entry_price,
            indicator_values=indicator_values or {}
        )

    async def update_signal_status(
        self,
        signal_id: str,
        status: str
    ) -> bool:
        """Update the status of a signal"""
        return await self._signal_repo.update_status(signal_id, status)
