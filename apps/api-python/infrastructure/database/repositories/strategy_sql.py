"""Strategy repository using transaction_db (SQL direto) - Compativel com pgBouncer"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class StrategyRepositorySQL:
    """Repository for Strategy using SQL direto (transaction_db)"""

    def __init__(self, db):
        self.db = db

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all strategies with optional filters"""
        query = """
            SELECT
                s.id, s.name, s.description, s.config_type, s.symbols, s.timeframe,
                s.is_active, s.is_backtesting, s.bot_id, s.created_by,
                s.config_yaml, s.pinescript_source, s.created_at, s.updated_at
            FROM strategies s
            WHERE 1=1
        """
        params = []
        param_idx = 1

        if is_active is not None:
            query += f" AND s.is_active = ${param_idx}"
            params.append(is_active)
            param_idx += 1

        if user_id is not None:
            query += f" AND s.created_by = ${param_idx}"
            params.append(user_id)
            param_idx += 1

        query += f" ORDER BY s.created_at DESC OFFSET ${param_idx} LIMIT ${param_idx + 1}"
        params.extend([skip, limit])

        rows = await self.db.fetch(query, *params)
        return [dict(row) for row in rows]

    async def get_strategies_with_stats(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get strategies with signal statistics"""
        # First get strategies
        strategies = await self.get_all(skip, limit, is_active, user_id)

        result = []
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        for strategy in strategies:
            strategy_id = str(strategy["id"])

            # Count signals today
            signals_today = await self.db.fetchval(
                """
                SELECT COUNT(*) FROM strategy_signals
                WHERE strategy_id = $1 AND created_at >= $2
                """,
                strategy_id, today_start
            ) or 0

            # Count executed signals
            total_executed = await self.db.fetchval(
                """
                SELECT COUNT(*) FROM strategy_signals
                WHERE strategy_id = $1 AND status = 'executed'
                """,
                strategy_id
            ) or 0

            # Get indicators
            indicators = await self.db.fetch(
                """
                SELECT indicator_type FROM strategy_indicators
                WHERE strategy_id = $1 ORDER BY order_index
                """,
                strategy_id
            )

            result.append({
                "strategy": strategy,
                "signals_today": signals_today,
                "total_executed": total_executed,
                "indicators": [row["indicator_type"] for row in indicators],
            })

        return result

    async def get_by_id(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get strategy by ID"""
        row = await self.db.fetchrow(
            """
            SELECT
                id, name, description, config_type, symbols, timeframe,
                is_active, is_backtesting, bot_id, created_by,
                config_yaml, pinescript_source, created_at, updated_at
            FROM strategies WHERE id = $1
            """,
            strategy_id
        )
        return dict(row) if row else None

    async def get_with_relations(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get strategy with indicators and conditions"""
        strategy = await self.get_by_id(strategy_id)
        if not strategy:
            return None

        # Get indicators
        indicators = await self.db.fetch(
            """
            SELECT id, indicator_type, parameters, order_index, created_at
            FROM strategy_indicators
            WHERE strategy_id = $1 ORDER BY order_index
            """,
            strategy_id
        )

        # Get conditions
        conditions = await self.db.fetch(
            """
            SELECT id, condition_type, conditions, logic_operator, order_index, created_at
            FROM strategy_conditions
            WHERE strategy_id = $1 ORDER BY order_index
            """,
            strategy_id
        )

        strategy["indicators"] = [dict(row) for row in indicators]
        strategy["conditions"] = [dict(row) for row in conditions]
        return strategy

    async def create(
        self,
        name: str,
        description: Optional[str] = None,
        config_type: str = "visual",
        symbols: List[str] = None,
        timeframe: str = "5m",
        bot_id: Optional[str] = None,
        created_by: Optional[str] = None,
        config_yaml: Optional[str] = None,
        pinescript_source: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new strategy"""
        strategy_id = str(uuid4())
        now = datetime.utcnow()

        await self.db.execute(
            """
            INSERT INTO strategies (
                id, name, description, config_type, symbols, timeframe,
                is_active, is_backtesting, bot_id, created_by,
                config_yaml, pinescript_source, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            """,
            strategy_id, name, description, config_type,
            json.dumps(symbols or []), timeframe,
            False, False, bot_id, created_by,
            config_yaml, pinescript_source, now, now
        )

        return await self.get_by_id(strategy_id)

    async def update(self, strategy_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Update a strategy"""
        if not updates:
            return await self.get_by_id(strategy_id)

        # Build dynamic update query
        set_parts = []
        params = []
        param_idx = 1

        for key, value in updates.items():
            if key in ["symbols"] and isinstance(value, list):
                value = json.dumps(value)
            set_parts.append(f"{key} = ${param_idx}")
            params.append(value)
            param_idx += 1

        set_parts.append(f"updated_at = ${param_idx}")
        params.append(datetime.utcnow())
        param_idx += 1

        params.append(strategy_id)

        query = f"""
            UPDATE strategies SET {', '.join(set_parts)}
            WHERE id = ${param_idx}
        """

        await self.db.execute(query, *params)
        return await self.get_by_id(strategy_id)

    async def delete(self, strategy_id: str) -> bool:
        """Delete a strategy (cascade deletes indicators, conditions, signals)"""
        result = await self.db.execute(
            "DELETE FROM strategies WHERE id = $1",
            strategy_id
        )
        return "DELETE 1" in result

    async def activate(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Activate a strategy"""
        return await self.update(strategy_id, is_active=True)

    async def deactivate(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Deactivate a strategy"""
        return await self.update(strategy_id, is_active=False)

    async def get_active_strategies(self) -> List[Dict[str, Any]]:
        """Get all active strategies with relations"""
        rows = await self.db.fetch(
            """
            SELECT id FROM strategies WHERE is_active = true ORDER BY created_at DESC
            """
        )
        result = []
        for row in rows:
            strategy = await self.get_with_relations(str(row["id"]))
            if strategy:
                result.append(strategy)
        return result

    async def find_by_pinescript_secret(self, secret: str) -> Optional[Dict[str, Any]]:
        """Find strategy by PineScript webhook secret stored in pinescript_source JSON"""
        # The secret is stored in pinescript_source as JSON: {"webhook_secret": "ps_xxx", ...}
        rows = await self.db.fetch(
            """
            SELECT id, name, description, config_type, symbols, timeframe,
                   is_active, is_backtesting, bot_id, created_by,
                   config_yaml, pinescript_source, created_at, updated_at
            FROM strategies
            WHERE config_type = 'pinescript'
              AND pinescript_source IS NOT NULL
            """
        )

        for row in rows:
            strategy = dict(row)
            pinescript_source = strategy.get("pinescript_source")
            if pinescript_source:
                try:
                    config = json.loads(pinescript_source)
                    if config.get("webhook_secret") == secret:
                        return strategy
                except json.JSONDecodeError:
                    continue

        return None


class StrategyIndicatorRepositorySQL:
    """Repository for StrategyIndicator using SQL direto"""

    def __init__(self, db):
        self.db = db

    async def get_by_strategy(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get all indicators for a strategy"""
        rows = await self.db.fetch(
            """
            SELECT id, strategy_id, indicator_type, parameters, order_index, created_at
            FROM strategy_indicators
            WHERE strategy_id = $1 ORDER BY order_index
            """,
            strategy_id
        )
        return [dict(row) for row in rows]

    async def create(
        self,
        strategy_id: str,
        indicator_type: str,
        parameters: Dict[str, Any] = None,
        order_index: int = 0
    ) -> Dict[str, Any]:
        """Create a new indicator"""
        indicator_id = str(uuid4())
        now = datetime.utcnow()

        await self.db.execute(
            """
            INSERT INTO strategy_indicators (id, strategy_id, indicator_type, parameters, order_index, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            indicator_id, strategy_id, indicator_type,
            json.dumps(parameters or {}), order_index, now
        )

        row = await self.db.fetchrow(
            "SELECT * FROM strategy_indicators WHERE id = $1", indicator_id
        )
        return dict(row) if row else None

    async def delete(self, indicator_id: str) -> bool:
        """Delete an indicator"""
        result = await self.db.execute(
            "DELETE FROM strategy_indicators WHERE id = $1",
            indicator_id
        )
        return "DELETE 1" in result

    async def delete_by_strategy(self, strategy_id: str) -> int:
        """Delete all indicators for a strategy"""
        result = await self.db.execute(
            "DELETE FROM strategy_indicators WHERE strategy_id = $1",
            strategy_id
        )
        # Extract count from result like "DELETE 5"
        try:
            return int(result.split()[1])
        except:
            return 0


class StrategyConditionRepositorySQL:
    """Repository for StrategyCondition using SQL direto"""

    def __init__(self, db):
        self.db = db

    async def get_by_strategy(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get all conditions for a strategy"""
        rows = await self.db.fetch(
            """
            SELECT id, strategy_id, condition_type, conditions, logic_operator, order_index, created_at
            FROM strategy_conditions
            WHERE strategy_id = $1 ORDER BY order_index
            """,
            strategy_id
        )
        return [dict(row) for row in rows]

    async def create(
        self,
        strategy_id: str,
        condition_type: str,
        conditions: List[Dict[str, Any]],
        logic_operator: str = "AND",
        order_index: int = 0
    ) -> Dict[str, Any]:
        """Create a new condition"""
        condition_id = str(uuid4())
        now = datetime.utcnow()

        await self.db.execute(
            """
            INSERT INTO strategy_conditions (id, strategy_id, condition_type, conditions, logic_operator, order_index, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            condition_id, strategy_id, condition_type,
            json.dumps(conditions), logic_operator, order_index, now
        )

        row = await self.db.fetchrow(
            "SELECT * FROM strategy_conditions WHERE id = $1", condition_id
        )
        return dict(row) if row else None

    async def delete(self, condition_id: str) -> bool:
        """Delete a condition"""
        result = await self.db.execute(
            "DELETE FROM strategy_conditions WHERE id = $1",
            condition_id
        )
        return "DELETE 1" in result

    async def delete_by_strategy(self, strategy_id: str) -> int:
        """Delete all conditions for a strategy"""
        result = await self.db.execute(
            "DELETE FROM strategy_conditions WHERE strategy_id = $1",
            strategy_id
        )
        try:
            return int(result.split()[1])
        except:
            return 0


class StrategySignalRepositorySQL:
    """Repository for StrategySignal using SQL direto"""

    def __init__(self, db):
        self.db = db

    async def get_by_strategy(
        self,
        strategy_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get signals for a strategy"""
        rows = await self.db.fetch(
            """
            SELECT id, strategy_id, symbol, signal_type, entry_price,
                   indicator_values, status, bot_signal_id, created_at
            FROM strategy_signals
            WHERE strategy_id = $1
            ORDER BY created_at DESC
            OFFSET $2 LIMIT $3
            """,
            strategy_id, skip, limit
        )
        return [dict(row) for row in rows]

    async def get_recent_all(
        self,
        limit: int = 50,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent signals across all strategies"""
        if symbol:
            rows = await self.db.fetch(
                """
                SELECT id, strategy_id, symbol, signal_type, entry_price,
                       status, created_at
                FROM strategy_signals
                WHERE symbol = $1
                ORDER BY created_at DESC LIMIT $2
                """,
                symbol, limit
            )
        else:
            rows = await self.db.fetch(
                """
                SELECT id, strategy_id, symbol, signal_type, entry_price,
                       status, created_at
                FROM strategy_signals
                ORDER BY created_at DESC LIMIT $1
                """,
                limit
            )
        return [dict(row) for row in rows]

    async def create(
        self,
        strategy_id: str,
        symbol: str,
        signal_type: str,
        entry_price: Optional[float] = None,
        indicator_values: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a new signal"""
        signal_id = str(uuid4())
        now = datetime.utcnow()

        await self.db.execute(
            """
            INSERT INTO strategy_signals (id, strategy_id, symbol, signal_type, entry_price, indicator_values, status, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            signal_id, strategy_id, symbol, signal_type, entry_price,
            json.dumps(indicator_values or {}), "pending", now
        )

        row = await self.db.fetchrow(
            "SELECT * FROM strategy_signals WHERE id = $1", signal_id
        )
        return dict(row) if row else None

    async def mark_executed(self, signal_id: str, bot_signal_id: str) -> bool:
        """Mark signal as executed"""
        result = await self.db.execute(
            """
            UPDATE strategy_signals
            SET status = 'executed', bot_signal_id = $2, updated_at = $3
            WHERE id = $1
            """,
            signal_id, bot_signal_id, datetime.utcnow()
        )
        return "UPDATE 1" in result

    async def mark_failed(self, signal_id: str) -> bool:
        """Mark signal as failed"""
        result = await self.db.execute(
            """
            UPDATE strategy_signals
            SET status = 'failed', updated_at = $2
            WHERE id = $1
            """,
            signal_id, datetime.utcnow()
        )
        return "UPDATE 1" in result

    async def update_status(self, signal_id: str, status: str) -> bool:
        """Update signal status"""
        result = await self.db.execute(
            """
            UPDATE strategy_signals
            SET status = $2, updated_at = $3
            WHERE id = $1
            """,
            signal_id, status, datetime.utcnow()
        )
        return "UPDATE 1" in result


class StrategyBacktestResultRepositorySQL:
    """Repository for StrategyBacktestResult using SQL direto"""

    def __init__(self, db):
        self.db = db

    async def get_by_strategy(
        self,
        strategy_id: str,
        skip: int = 0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get backtest results for a strategy"""
        rows = await self.db.fetch(
            """
            SELECT id, strategy_id, start_date, end_date, symbol,
                   initial_capital, leverage, margin_percent, stop_loss_percent, take_profit_percent,
                   include_fees, include_slippage,
                   total_trades, winning_trades, losing_trades, win_rate, profit_factor,
                   total_pnl, total_pnl_percent, max_drawdown, sharpe_ratio,
                   trades, equity_curve, created_at
            FROM strategy_backtest_results
            WHERE strategy_id = $1
            ORDER BY created_at DESC
            OFFSET $2 LIMIT $3
            """,
            strategy_id, skip, limit
        )
        return [dict(row) for row in rows]

    async def get_by_id(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Get backtest result by ID"""
        row = await self.db.fetchrow(
            """
            SELECT * FROM strategy_backtest_results WHERE id = $1
            """,
            result_id
        )
        return dict(row) if row else None

    async def create(self, strategy_id: str, **data) -> Dict[str, Any]:
        """Create a new backtest result"""
        result_id = str(uuid4())
        now = datetime.utcnow()

        # Build insert query dynamically
        columns = ["id", "strategy_id", "created_at", "updated_at"]
        values = [result_id, strategy_id, now, now]
        placeholders = ["$1", "$2", "$3", "$4"]

        idx = 5
        for key, value in data.items():
            columns.append(key)
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            values.append(value)
            placeholders.append(f"${idx}")
            idx += 1

        query = f"""
            INSERT INTO strategy_backtest_results ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """

        await self.db.execute(query, *values)
        return await self.get_by_id(result_id)
