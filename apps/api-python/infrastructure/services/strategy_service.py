"""
Strategy Service

Provides CRUD operations and business logic for trading strategies.
This is the main service layer for strategy management.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
import yaml

from infrastructure.database.models.strategy import (
    ConfigType,
    ConditionType,
    IndicatorType,
    LogicOperator,
    Strategy,
    StrategyBacktestResult,
    StrategyCondition,
    StrategyIndicator,
    StrategySignal,
)
from infrastructure.database.repositories.strategy import (
    StrategyBacktestResultRepository,
    StrategyConditionRepository,
    StrategyIndicatorRepository,
    StrategyRepository,
    StrategySignalRepository,
)

logger = structlog.get_logger(__name__)


class StrategyService:
    """
    Strategy Service

    Provides high-level operations for managing trading strategies:
    - Create/Update/Delete strategies
    - Configure indicators and conditions
    - Activate/Deactivate strategies
    - Parse YAML configurations
    - Link strategies to bots
    """

    def __init__(self, db_pool):
        self.db = db_pool
        self._strategy_repo = StrategyRepository(db_pool)
        self._indicator_repo = StrategyIndicatorRepository(db_pool)
        self._condition_repo = StrategyConditionRepository(db_pool)
        self._signal_repo = StrategySignalRepository(db_pool)
        self._backtest_repo = StrategyBacktestResultRepository(db_pool)

    # ==================== Strategy CRUD ====================

    async def create_strategy(
        self,
        name: str,
        description: Optional[str] = None,
        config_type: ConfigType = ConfigType.VISUAL,
        symbols: List[str] = None,
        timeframe: str = "5m",
        bot_id: Optional[str] = None,
        created_by: Optional[str] = None,
        config_yaml: Optional[str] = None,
        pinescript_source: Optional[str] = None,
    ) -> Strategy:
        """
        Create a new trading strategy

        Args:
            name: Strategy name
            description: Optional description
            config_type: Configuration type (visual, yaml, pinescript)
            symbols: List of trading symbols (e.g., ["BTCUSDT", "ETHUSDT"])
            timeframe: Trading timeframe (1m, 5m, 15m, 1h, etc.)
            bot_id: Optional linked bot ID
            created_by: User ID who created the strategy
            config_yaml: YAML configuration (if config_type is YAML)
            pinescript_source: PineScript source (if config_type is PINESCRIPT)

        Returns:
            Created Strategy object
        """
        strategy = Strategy(
            name=name,
            description=description,
            config_type=config_type,
            symbols=symbols or [],
            timeframe=timeframe,
            bot_id=bot_id,
            created_by=created_by,
            config_yaml=config_yaml,
            pinescript_source=pinescript_source,
            is_active=False,
            is_backtesting=False,
        )

        created = await self._strategy_repo.create_strategy(strategy)

        # If YAML config provided, parse and create indicators/conditions
        if config_type == ConfigType.YAML and config_yaml:
            await self._apply_yaml_config(str(created.id), config_yaml)

        logger.info(
            f"Strategy created: {name}",
            strategy_id=str(created.id),
            symbols=symbols
        )

        return created

    async def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get a strategy by ID with all relations loaded"""
        return await self._strategy_repo.get_with_relations(strategy_id)

    async def list_strategies(
        self,
        user_id: Optional[str] = None,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List strategies with statistics

        Args:
            user_id: Filter by creator user ID
            active_only: Only return active strategies
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of strategies with signal statistics
        """
        return await self._strategy_repo.get_strategies_with_stats(
            user_id=user_id,
            active_only=active_only,
            limit=limit,
            offset=offset
        )

    async def update_strategy(
        self,
        strategy_id: str,
        **updates
    ) -> Optional[Strategy]:
        """
        Update a strategy

        Args:
            strategy_id: Strategy ID
            **updates: Fields to update

        Returns:
            Updated Strategy object
        """
        # Prevent updating certain fields
        updates.pop("id", None)
        updates.pop("created_at", None)

        updated = await self._strategy_repo.update(strategy_id, **updates)

        if updated:
            logger.info(f"Strategy updated: {strategy_id}", updates=list(updates.keys()))

        return updated

    async def delete_strategy(self, strategy_id: str) -> bool:
        """
        Delete a strategy (soft delete - marks as inactive first)

        Args:
            strategy_id: Strategy ID

        Returns:
            True if deleted
        """
        # Deactivate first
        await self._strategy_repo.update(strategy_id, is_active=False)

        # Then delete
        deleted = await self._strategy_repo.delete(strategy_id)

        if deleted:
            logger.info(f"Strategy deleted: {strategy_id}")

        return deleted

    # ==================== Activation ====================

    async def activate_strategy(self, strategy_id: str) -> Strategy:
        """
        Activate a strategy for live trading

        Args:
            strategy_id: Strategy ID

        Returns:
            Updated Strategy
        """
        strategy = await self._strategy_repo.get(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")

        # Validate strategy has required configuration
        full_strategy = await self._strategy_repo.get_with_relations(strategy_id)

        if not full_strategy.get_symbols_list():
            raise ValueError("Strategy must have at least one symbol configured")

        if not full_strategy.indicators:
            raise ValueError("Strategy must have at least one indicator configured")

        # Activate
        updated = await self._strategy_repo.update(strategy_id, is_active=True)

        logger.info(f"Strategy activated: {strategy_id}")

        return updated

    async def deactivate_strategy(self, strategy_id: str) -> Strategy:
        """
        Deactivate a strategy

        Args:
            strategy_id: Strategy ID

        Returns:
            Updated Strategy
        """
        updated = await self._strategy_repo.update(strategy_id, is_active=False)

        logger.info(f"Strategy deactivated: {strategy_id}")

        return updated

    # ==================== Indicators ====================

    async def add_indicator(
        self,
        strategy_id: str,
        indicator_type: IndicatorType,
        parameters: Dict[str, Any] = None,
        order_index: int = 0,
    ) -> StrategyIndicator:
        """
        Add an indicator to a strategy

        Args:
            strategy_id: Strategy ID
            indicator_type: Type of indicator
            parameters: Indicator parameters
            order_index: Order for evaluation

        Returns:
            Created StrategyIndicator
        """
        indicator = StrategyIndicator(
            strategy_id=strategy_id,
            indicator_type=indicator_type,
            parameters=parameters or {},
            order_index=order_index,
        )

        created = await self._indicator_repo.create_indicator(indicator)

        logger.info(
            f"Indicator added",
            strategy_id=strategy_id,
            indicator_type=indicator_type.value
        )

        return created

    async def update_indicator(
        self,
        indicator_id: str,
        **updates
    ) -> Optional[StrategyIndicator]:
        """Update an indicator's parameters"""
        return await self._indicator_repo.update(indicator_id, **updates)

    async def remove_indicator(self, indicator_id: str) -> bool:
        """Remove an indicator from a strategy"""
        return await self._indicator_repo.delete(indicator_id)

    async def get_indicators(self, strategy_id: str) -> List[StrategyIndicator]:
        """Get all indicators for a strategy"""
        return await self._indicator_repo.get_by_strategy(strategy_id)

    # ==================== Conditions ====================

    async def add_condition(
        self,
        strategy_id: str,
        condition_type: ConditionType,
        conditions: List[Dict[str, Any]],
        logic_operator: LogicOperator = LogicOperator.AND,
        order_index: int = 0,
    ) -> StrategyCondition:
        """
        Add a condition to a strategy

        Args:
            strategy_id: Strategy ID
            condition_type: Type (entry_long, entry_short, exit_long, exit_short)
            conditions: List of condition rules
            logic_operator: AND or OR
            order_index: Order for evaluation

        Returns:
            Created StrategyCondition

        Example conditions:
            [
                {"left": "close", "operator": "<", "right": "ndy.lower"},
                {"left": "close", "operator": "<", "right": "tpo.val"}
            ]
        """
        condition = StrategyCondition(
            strategy_id=strategy_id,
            condition_type=condition_type,
            conditions=conditions,
            logic_operator=logic_operator,
            order_index=order_index,
        )

        created = await self._condition_repo.create_condition(condition)

        logger.info(
            f"Condition added",
            strategy_id=strategy_id,
            condition_type=condition_type.value
        )

        return created

    async def update_condition(
        self,
        condition_id: str,
        **updates
    ) -> Optional[StrategyCondition]:
        """Update a condition"""
        return await self._condition_repo.update(condition_id, **updates)

    async def remove_condition(self, condition_id: str) -> bool:
        """Remove a condition from a strategy"""
        return await self._condition_repo.delete(condition_id)

    async def get_conditions(self, strategy_id: str) -> List[StrategyCondition]:
        """Get all conditions for a strategy"""
        return await self._condition_repo.get_by_strategy(strategy_id)

    # ==================== Signals ====================

    async def get_signals(
        self,
        strategy_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[StrategySignal]:
        """Get signals generated by a strategy"""
        return await self._signal_repo.get_by_strategy(strategy_id, limit=limit, offset=offset)

    async def get_recent_signals(
        self,
        limit: int = 50,
        symbol: Optional[str] = None,
    ) -> List[StrategySignal]:
        """Get recent signals across all strategies"""
        return await self._signal_repo.get_recent(limit=limit, symbol=symbol)

    # ==================== Bot Linking ====================

    async def link_bot(self, strategy_id: str, bot_id: str) -> Strategy:
        """
        Link a strategy to a bot for signal execution

        Args:
            strategy_id: Strategy ID
            bot_id: Bot ID to link

        Returns:
            Updated Strategy
        """
        # Verify bot exists
        bot = await self.db.fetchrow(
            "SELECT id, name FROM bots WHERE id = $1",
            UUID(bot_id)
        )
        if not bot:
            raise ValueError(f"Bot {bot_id} not found")

        updated = await self._strategy_repo.update(strategy_id, bot_id=bot_id)

        logger.info(
            f"Strategy linked to bot",
            strategy_id=strategy_id,
            bot_id=bot_id,
            bot_name=bot["name"]
        )

        return updated

    async def unlink_bot(self, strategy_id: str) -> Strategy:
        """
        Unlink a strategy from its bot

        Args:
            strategy_id: Strategy ID

        Returns:
            Updated Strategy
        """
        updated = await self._strategy_repo.update(strategy_id, bot_id=None)

        logger.info(f"Strategy unlinked from bot", strategy_id=strategy_id)

        return updated

    # ==================== YAML Configuration ====================

    async def apply_yaml_config(self, strategy_id: str, yaml_content: str) -> Strategy:
        """
        Apply YAML configuration to a strategy

        Args:
            strategy_id: Strategy ID
            yaml_content: YAML configuration string

        Returns:
            Updated Strategy
        """
        # Validate and apply
        await self._apply_yaml_config(strategy_id, yaml_content)

        # Update strategy with YAML
        updated = await self._strategy_repo.update(
            strategy_id,
            config_type=ConfigType.YAML,
            config_yaml=yaml_content
        )

        logger.info(f"YAML config applied", strategy_id=strategy_id)

        return updated

    async def _apply_yaml_config(self, strategy_id: str, yaml_content: str) -> None:
        """Parse YAML and create indicators/conditions"""
        try:
            config = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")

        # Clear existing indicators and conditions
        existing_indicators = await self._indicator_repo.get_by_strategy(strategy_id)
        for ind in existing_indicators:
            await self._indicator_repo.delete(str(ind.id))

        existing_conditions = await self._condition_repo.get_by_strategy(strategy_id)
        for cond in existing_conditions:
            await self._condition_repo.delete(str(cond.id))

        # Update symbols and timeframe if provided
        if "symbols" in config:
            await self._strategy_repo.update(strategy_id, symbols=config["symbols"])
        if "timeframe" in config:
            await self._strategy_repo.update(strategy_id, timeframe=config["timeframe"])

        # Create indicators
        indicators_config = config.get("indicators", [])
        for idx, ind_config in enumerate(indicators_config):
            ind_type = ind_config.get("type", "")
            try:
                indicator_type = IndicatorType(ind_type)
            except ValueError:
                logger.warning(f"Unknown indicator type: {ind_type}")
                continue

            await self.add_indicator(
                strategy_id=strategy_id,
                indicator_type=indicator_type,
                parameters=ind_config.get("parameters", {}),
                order_index=idx,
            )

        # Create conditions
        conditions_config = config.get("conditions", {})

        for cond_type_str, cond_list in conditions_config.items():
            try:
                condition_type = ConditionType(cond_type_str)
            except ValueError:
                logger.warning(f"Unknown condition type: {cond_type_str}")
                continue

            logic = cond_list.get("logic", "AND")
            logic_operator = LogicOperator.AND if logic.upper() == "AND" else LogicOperator.OR

            rules = cond_list.get("rules", [])

            await self.add_condition(
                strategy_id=strategy_id,
                condition_type=condition_type,
                conditions=rules,
                logic_operator=logic_operator,
            )

    def generate_yaml_template(
        self,
        indicator_types: List[str] = None,
        symbols: List[str] = None,
    ) -> str:
        """
        Generate a YAML template for strategy configuration

        Args:
            indicator_types: List of indicator types to include
            symbols: List of symbols

        Returns:
            YAML template string
        """
        template = {
            "name": "My Strategy",
            "description": "Strategy description",
            "symbols": symbols or ["BTCUSDT"],
            "timeframe": "5m",
            "indicators": [],
            "conditions": {
                "entry_long": {
                    "logic": "AND",
                    "rules": []
                },
                "entry_short": {
                    "logic": "AND",
                    "rules": []
                }
            }
        }

        # Add indicator templates
        indicator_templates = {
            "nadaraya_watson": {
                "type": "nadaraya_watson",
                "parameters": {
                    "bandwidth": 8,
                    "mult": 3.0,
                    "src": "close",
                    "use_atr": True,
                    "atr_period": 14
                }
            },
            "tpo": {
                "type": "tpo",
                "parameters": {
                    "period": 24,
                    "value_area_percent": 70.0,
                    "row_size": 24
                }
            },
            "rsi": {
                "type": "rsi",
                "parameters": {
                    "period": 14,
                    "overbought": 70,
                    "oversold": 30
                }
            }
        }

        if indicator_types:
            for ind_type in indicator_types:
                if ind_type in indicator_templates:
                    template["indicators"].append(indicator_templates[ind_type])
        else:
            # Default: NDY + TPO
            template["indicators"] = [
                indicator_templates["nadaraya_watson"],
                indicator_templates["tpo"]
            ]

        # Add condition templates
        template["conditions"]["entry_long"]["rules"] = [
            {"left": "close", "operator": "<", "right": "nadaraya_watson.lower"},
            {"left": "close", "operator": "<", "right": "tpo.val"}
        ]

        template["conditions"]["entry_short"]["rules"] = [
            {"left": "close", "operator": ">", "right": "nadaraya_watson.upper"},
            {"left": "close", "operator": ">", "right": "tpo.vah"}
        ]

        return yaml.dump(template, default_flow_style=False, sort_keys=False)

    # ==================== Backtest Results ====================

    async def get_backtest_results(
        self,
        strategy_id: str,
        limit: int = 10,
    ) -> List[StrategyBacktestResult]:
        """Get backtest results for a strategy"""
        return await self._backtest_repo.get_by_strategy(strategy_id, limit=limit)

    async def get_latest_backtest(
        self,
        strategy_id: str,
    ) -> Optional[StrategyBacktestResult]:
        """Get the latest backtest result for a strategy"""
        return await self._backtest_repo.get_latest(strategy_id)
