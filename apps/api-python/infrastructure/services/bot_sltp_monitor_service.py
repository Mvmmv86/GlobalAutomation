"""
Bot SL/TP Monitor Service
Monitors Stop Loss and Take Profit orders for bot subscriptions
Detects when SL/TP is triggered and updates trade records
"""
import asyncio
import json
import time
from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from uuid import UUID

import structlog

from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.exchanges.bingx_connector import BingXConnector
from infrastructure.services.bot_trade_tracker_service import BotTradeTrackerService

logger = structlog.get_logger(__name__)


class BotSLTPMonitorService:
    """
    Service responsible for monitoring SL/TP orders from bot subscriptions
    and detecting when they are filled to update trade records and P&L
    """

    def __init__(self, db_pool):
        self.db = db_pool
        self.trade_tracker = BotTradeTrackerService(db_pool)
        self._is_running = False

    async def monitor_all_subscriptions(self) -> Dict:
        """
        Main monitoring loop - checks all active bot subscriptions for filled SL/TP orders
        Should be called periodically (e.g., every 30 seconds)

        Returns:
            Dict with monitoring results
        """
        if self._is_running:
            logger.warning("SL/TP monitor already running, skipping")
            return {"success": False, "reason": "already_running"}

        self._is_running = True
        start_time = datetime.utcnow()

        try:
            logger.info("Starting SL/TP monitoring cycle")

            # Get all open executions with SL/TP orders that haven't been processed yet
            open_executions = await self._get_open_executions_with_sltp()

            if not open_executions:
                logger.debug("No open executions with SL/TP to monitor")
                return {"success": True, "checked": 0, "closed": 0}

            logger.info(f"Monitoring {len(open_executions)} open executions with SL/TP orders")

            checked = 0
            closed = 0
            errors = []

            # Group by exchange account to minimize API calls
            executions_by_account = {}
            for exec_data in open_executions:
                account_id = str(exec_data["exchange_account_id"])
                if account_id not in executions_by_account:
                    executions_by_account[account_id] = []
                executions_by_account[account_id].append(exec_data)

            # Process each exchange account
            for account_id, executions in executions_by_account.items():
                try:
                    result = await self._check_account_executions(account_id, executions)
                    checked += result.get("checked", 0)
                    closed += result.get("closed", 0)
                except Exception as e:
                    error_msg = f"Error checking account {account_id}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)

            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            logger.info(
                "SL/TP monitoring cycle completed",
                checked=checked,
                closed=closed,
                duration_ms=duration_ms,
                errors=len(errors)
            )

            return {
                "success": True,
                "checked": checked,
                "closed": closed,
                "duration_ms": duration_ms,
                "errors": errors[:5] if errors else []
            }

        except Exception as e:
            logger.error("Error in SL/TP monitoring", error=str(e), exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            self._is_running = False

    async def _get_open_executions_with_sltp(self) -> List[Dict]:
        """
        Get all bot signal executions that have SL/TP orders and haven't been closed yet
        """
        try:
            executions = await self.db.fetch("""
                SELECT
                    bse.id as execution_id,
                    bse.subscription_id,
                    bse.user_id,
                    bse.signal_id,
                    bse.exchange_account_id,
                    bse.exchange_order_id,
                    bse.executed_price,
                    bse.executed_quantity,
                    bse.stop_loss_order_id,
                    bse.take_profit_order_id,
                    bse.stop_loss_price,
                    bse.take_profit_price,
                    bse.created_at as execution_time,
                    bs.ticker,
                    bs.action,
                    b.name as bot_name,
                    b.id as bot_id,
                    ea.exchange,
                    ea.api_key,
                    ea.secret_key,
                    ea.testnet
                FROM bot_signal_executions bse
                INNER JOIN bot_signals bs ON bs.id = bse.signal_id
                INNER JOIN bot_subscriptions bsub ON bsub.id = bse.subscription_id
                INNER JOIN bots b ON b.id = bsub.bot_id
                INNER JOIN exchange_accounts ea ON ea.id = bse.exchange_account_id
                WHERE bse.status = 'success'
                  AND (bse.stop_loss_order_id IS NOT NULL OR bse.take_profit_order_id IS NOT NULL)
                  AND bse.id NOT IN (
                      SELECT signal_execution_id FROM bot_trades
                      WHERE signal_execution_id IS NOT NULL AND status = 'closed'
                  )
                ORDER BY bse.created_at ASC
            """)

            return [dict(e) for e in executions]

        except Exception as e:
            logger.error("Error fetching open executions", error=str(e), exc_info=True)
            return []

    async def _check_account_executions(
        self,
        account_id: str,
        executions: List[Dict]
    ) -> Dict:
        """
        Check all executions for a single exchange account.
        Uses batch queries to minimize API calls - loads all orders once per symbol.
        """
        if not executions:
            return {"checked": 0, "closed": 0}

        # Get exchange info from first execution
        first_exec = executions[0]
        exchange = first_exec["exchange"].lower()
        api_key = first_exec["api_key"]
        api_secret = first_exec["secret_key"]
        testnet = first_exec.get("testnet", False)

        # Create connector
        connector = None
        try:
            if exchange == "bingx":
                connector = BingXConnector(api_key=api_key, api_secret=api_secret, testnet=testnet)
            elif exchange == "binance":
                connector = BinanceConnector(api_key=api_key, api_secret=api_secret, testnet=testnet)
            else:
                logger.warning(f"Exchange {exchange} not supported for SL/TP monitoring")
                return {"checked": 0, "closed": 0}

            checked = 0
            closed = 0

            # Group executions by symbol to batch API calls
            executions_by_symbol = {}
            for exec_data in executions:
                symbol = exec_data["ticker"].replace("-", "")
                if symbol not in executions_by_symbol:
                    executions_by_symbol[symbol] = []
                executions_by_symbol[symbol].append(exec_data)

            # Process each symbol group with cached order data
            for symbol, symbol_executions in executions_by_symbol.items():
                try:
                    # Load orders once for this symbol
                    orders_cache = await self._load_orders_for_symbol(connector, symbol, exchange)

                    for exec_data in symbol_executions:
                        try:
                            result = await self._check_single_execution_with_cache(
                                connector, exec_data, exchange, orders_cache
                            )
                            checked += 1
                            if result.get("closed"):
                                closed += 1
                        except Exception as e:
                            logger.error(
                                f"Error checking execution {exec_data['execution_id']}: {str(e)}",
                                exc_info=True
                            )
                except Exception as e:
                    logger.error(f"Error loading orders for symbol {symbol}: {str(e)}")

            return {"checked": checked, "closed": closed}

        finally:
            if connector:
                await connector.close()

    async def _load_orders_for_symbol(
        self,
        connector,
        symbol: str,
        exchange: str
    ) -> Dict:
        """
        Load all open and recent orders for a symbol in one batch.
        Returns a cache dict with order_id -> order_data mapping.
        """
        orders_cache = {
            "open_orders": {},  # order_id -> order_data
            "all_orders": {}    # order_id -> order_data
        }

        try:
            symbol_formatted = symbol.replace("USDT", "-USDT") if "-" not in symbol else symbol

            # Load open orders (1 API call per symbol)
            if exchange == "bingx":
                open_result = await connector.get_open_orders(symbol=symbol_formatted)
                if open_result.get("success"):
                    for order in open_result.get("orders", []):
                        order_id = str(order.get("orderId"))
                        orders_cache["open_orders"][order_id] = order

                # Load all orders from last 7 days (1 API call per symbol)
                end_time = int(time.time() * 1000)
                start_time = end_time - (7 * 24 * 60 * 60 * 1000)
                all_result = await connector.get_futures_orders(
                    symbol=symbol_formatted,
                    start_time=start_time,
                    end_time=end_time,
                    limit=500
                )
                if all_result.get("success"):
                    for order in all_result.get("orders", []):
                        order_id = str(order.get("orderId"))
                        orders_cache["all_orders"][order_id] = order

            elif exchange == "binance":
                # Similar logic for Binance
                open_result = await connector.get_open_orders(symbol=symbol)
                if open_result.get("success"):
                    for order in open_result.get("orders", []):
                        order_id = str(order.get("orderId"))
                        orders_cache["open_orders"][order_id] = order

            logger.debug(
                f"Loaded orders cache for {symbol}",
                open_count=len(orders_cache["open_orders"]),
                all_count=len(orders_cache["all_orders"])
            )

        except Exception as e:
            logger.error(f"Error loading orders cache for {symbol}: {e}")

        return orders_cache

    async def _check_single_execution_with_cache(
        self,
        connector,
        exec_data: Dict,
        exchange: str,
        orders_cache: Dict
    ) -> Dict:
        """
        Check a single execution's SL/TP orders status using cached order data.
        Much more efficient than calling API for each order.
        """
        execution_id = exec_data["execution_id"]
        sl_order_id = str(exec_data.get("stop_loss_order_id", "")) if exec_data.get("stop_loss_order_id") else None
        tp_order_id = str(exec_data.get("take_profit_order_id", "")) if exec_data.get("take_profit_order_id") else None

        # Check Stop Loss order status from cache
        if sl_order_id:
            sl_order = orders_cache["all_orders"].get(sl_order_id)
            if sl_order and sl_order.get("status") == "FILLED":
                logger.info(f"SL order {sl_order_id} FILLED for execution {execution_id}")
                return await self._process_trade_close(
                    exec_data=exec_data,
                    close_reason="stop_loss",
                    filled_order_id=sl_order_id,
                    filled_order_data=sl_order,
                    connector=connector,
                    exchange=exchange
                )
            # If in open_orders, it's still pending (NEW)
            elif sl_order_id in orders_cache["open_orders"]:
                logger.debug(f"SL order {sl_order_id} still pending (NEW)")

        # Check Take Profit order status from cache
        if tp_order_id:
            tp_order = orders_cache["all_orders"].get(tp_order_id)
            if tp_order and tp_order.get("status") == "FILLED":
                logger.info(f"TP order {tp_order_id} FILLED for execution {execution_id}")
                return await self._process_trade_close(
                    exec_data=exec_data,
                    close_reason="take_profit",
                    filled_order_id=tp_order_id,
                    filled_order_data=tp_order,
                    connector=connector,
                    exchange=exchange
                )
            # If in open_orders, it's still pending (NEW)
            elif tp_order_id in orders_cache["open_orders"]:
                logger.debug(f"TP order {tp_order_id} still pending (NEW)")

        return {"closed": False}

    async def _check_single_execution(
        self,
        connector,
        exec_data: Dict,
        exchange: str
    ) -> Dict:
        """
        Check a single execution's SL/TP orders status (legacy method, kept for compatibility)
        """
        execution_id = exec_data["execution_id"]
        symbol = exec_data["ticker"].replace("-", "")
        sl_order_id = exec_data.get("stop_loss_order_id")
        tp_order_id = exec_data.get("take_profit_order_id")

        logger.debug(
            f"Checking execution {execution_id}",
            symbol=symbol,
            sl_order_id=sl_order_id,
            tp_order_id=tp_order_id
        )

        # Check Stop Loss order status
        if sl_order_id:
            sl_status = await self._get_order_status(connector, symbol, sl_order_id, exchange)
            if sl_status and sl_status.get("status") == "FILLED":
                logger.info(f"SL order {sl_order_id} FILLED for execution {execution_id}")
                return await self._process_trade_close(
                    exec_data=exec_data,
                    close_reason="stop_loss",
                    filled_order_id=sl_order_id,
                    filled_order_data=sl_status,
                    connector=connector,
                    exchange=exchange
                )

        # Check Take Profit order status
        if tp_order_id:
            tp_status = await self._get_order_status(connector, symbol, tp_order_id, exchange)
            if tp_status and tp_status.get("status") == "FILLED":
                logger.info(f"TP order {tp_order_id} FILLED for execution {execution_id}")
                return await self._process_trade_close(
                    exec_data=exec_data,
                    close_reason="take_profit",
                    filled_order_id=tp_order_id,
                    filled_order_data=tp_status,
                    connector=connector,
                    exchange=exchange
                )

        return {"closed": False}

    async def _get_order_status(
        self,
        connector,
        symbol: str,
        order_id: str,
        exchange: str
    ) -> Optional[Dict]:
        """
        Get FUTURES order status from exchange (for SL/TP orders)
        """
        try:
            if exchange == "bingx":
                # Use FUTURES order status (not SPOT)
                result = await connector.get_futures_order_status(symbol=symbol, order_id=order_id)
            elif exchange == "binance":
                result = await connector.get_futures_order_status(symbol=symbol, order_id=order_id)
            else:
                return None

            if result.get("success"):
                # Return order data with status
                order_data = result.get("order", result)
                return {
                    "status": result.get("status", order_data.get("status")),
                    "avgPrice": result.get("avgPrice", order_data.get("avgPrice")),
                    "executedQty": result.get("executedQty", order_data.get("executedQty")),
                    "stopPrice": result.get("stopPrice", order_data.get("stopPrice")),
                    "price": result.get("avgPrice", order_data.get("avgPrice")),
                    **order_data
                }
            else:
                logger.warning(f"Failed to get order status: {result.get('error')}")
                return None

        except Exception as e:
            logger.error(f"Error getting order status: {str(e)}")
            return None

    async def _process_trade_close(
        self,
        exec_data: Dict,
        close_reason: str,
        filled_order_id: str,
        filled_order_data: Dict,
        connector,
        exchange: str
    ) -> Dict:
        """
        Process a trade close when SL/TP is triggered
        """
        try:
            execution_id = exec_data["execution_id"]
            subscription_id = exec_data["subscription_id"]
            user_id = exec_data["user_id"]
            symbol = exec_data["ticker"].replace("-", "")
            side = exec_data["action"]  # buy or sell
            bot_name = exec_data["bot_name"]
            entry_price = float(exec_data["executed_price"] or 0)
            quantity = float(exec_data["executed_quantity"] or 0)
            execution_time = exec_data["execution_time"]

            # Get exit price from filled order
            exit_price = float(filled_order_data.get("avgPrice",
                              filled_order_data.get("price",
                              filled_order_data.get("stopPrice", entry_price))))

            # Calculate P&L
            if side.lower() == "buy":
                # Long position
                pnl_usd = (exit_price - entry_price) * quantity
            else:
                # Short position
                pnl_usd = (entry_price - exit_price) * quantity

            is_winner = pnl_usd >= 0

            # Calculate P&L percentage
            position_value = entry_price * quantity
            pnl_pct = (pnl_usd / position_value * 100) if position_value > 0 else 0

            logger.info(
                f"Processing trade close",
                execution_id=str(execution_id),
                symbol=symbol,
                close_reason=close_reason,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl_usd=pnl_usd,
                is_winner=is_winner
            )

            # Try to get more accurate P&L from exchange income history
            try:
                if exchange == "bingx":
                    income_result = await connector.get_income_history(
                        symbol=symbol,
                        income_type="REALIZED_PNL",
                        limit=10
                    )
                    if income_result.get("success") and income_result.get("incomes"):
                        # Find the most recent income for this symbol
                        for income in income_result["incomes"]:
                            if abs(float(income.get("income", 0))) > 0:
                                pnl_usd = float(income.get("income", pnl_usd))
                                logger.info(f"Using exchange P&L: ${pnl_usd:.4f}")
                                break
            except Exception as e:
                logger.warning(f"Could not get income history: {e}")

            # Record the trade close
            result = await self.trade_tracker.record_trade_close(
                subscription_id=subscription_id,
                signal_execution_id=execution_id,
                ticker=symbol,
                side=side,
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=quantity,
                pnl_usd=pnl_usd,
                close_reason=close_reason
            )

            if result.get("success"):
                # Update execution record with close info
                await self.db.execute("""
                    UPDATE bot_signal_executions
                    SET sl_order_status = CASE WHEN $2 = 'stop_loss' THEN 'filled' ELSE sl_order_status END,
                        tp_order_status = CASE WHEN $2 = 'take_profit' THEN 'filled' ELSE tp_order_status END,
                        realized_pnl = $3,
                        close_reason = $2
                    WHERE id = $1
                """, execution_id, close_reason, pnl_usd)

                # Cancel the opposite order (if SL filled, cancel TP and vice versa)
                await self._cancel_opposite_order(
                    connector=connector,
                    exec_data=exec_data,
                    close_reason=close_reason,
                    symbol=symbol
                )

                # Create notification
                await self._create_close_notification(
                    user_id=user_id,
                    bot_name=bot_name,
                    symbol=symbol,
                    side=side,
                    pnl_usd=pnl_usd,
                    pnl_pct=pnl_pct,
                    close_reason=close_reason,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    execution_time=execution_time
                )

                logger.info(
                    f"Trade close processed successfully",
                    execution_id=str(execution_id),
                    trade_id=result.get("trade_id"),
                    pnl_usd=pnl_usd,
                    is_winner=is_winner
                )

                return {"closed": True, "pnl_usd": pnl_usd, "is_winner": is_winner}
            else:
                logger.error(f"Failed to record trade close: {result.get('error')}")
                return {"closed": False, "error": result.get("error")}

        except Exception as e:
            logger.error(f"Error processing trade close: {str(e)}", exc_info=True)
            return {"closed": False, "error": str(e)}

    async def _cancel_opposite_order(
        self,
        connector,
        exec_data: Dict,
        close_reason: str,
        symbol: str
    ):
        """
        Cancel the opposite order when one is filled
        (if SL is filled, cancel TP and vice versa)
        """
        try:
            if close_reason == "stop_loss":
                # Cancel Take Profit
                tp_order_id = exec_data.get("take_profit_order_id")
                if tp_order_id:
                    logger.info(f"Canceling TP order {tp_order_id} after SL was filled")
                    await connector.cancel_order(symbol=symbol, order_id=tp_order_id)
            else:
                # Cancel Stop Loss
                sl_order_id = exec_data.get("stop_loss_order_id")
                if sl_order_id:
                    logger.info(f"Canceling SL order {sl_order_id} after TP was filled")
                    await connector.cancel_order(symbol=symbol, order_id=sl_order_id)
        except Exception as e:
            logger.warning(f"Could not cancel opposite order: {e}")

    async def _create_close_notification(
        self,
        user_id: UUID,
        bot_name: str,
        symbol: str,
        side: str,
        pnl_usd: float,
        pnl_pct: float,
        close_reason: str,
        entry_price: float,
        exit_price: float,
        execution_time: datetime
    ):
        """
        Create notification for trade close
        """
        try:
            # Calculate duration
            duration = datetime.utcnow() - execution_time
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

            # Determine notification type based on P&L
            notif_type = "success" if pnl_usd >= 0 else "warning"

            # Format close reason
            reason_text = "Take Profit" if close_reason == "take_profit" else "Stop Loss"
            reason_emoji = "🎯" if close_reason == "take_profit" else "🛑"

            # Format P&L
            pnl_sign = "+" if pnl_usd >= 0 else ""
            pnl_text = f"{pnl_sign}${pnl_usd:.2f} ({pnl_sign}{pnl_pct:.1f}%)"

            # Direction
            direction = "LONG" if side.lower() == "buy" else "SHORT"

            title = f"Trade Fechado: {symbol}"
            message = (
                f"Bot: {bot_name}\n"
                f"{direction} | P&L: {pnl_text}\n"
                f"Entrada: ${entry_price:.2f} → Saída: ${exit_price:.2f}\n"
                f"{reason_emoji} {reason_text} | Duração: {duration_str}"
            )

            metadata_json = json.dumps({
                "bot_name": bot_name,
                "symbol": symbol,
                "side": side,
                "pnl_usd": pnl_usd,
                "pnl_pct": pnl_pct,
                "close_reason": close_reason,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "duration": duration_str
            })

            await self.db.execute("""
                INSERT INTO notifications (
                    type, category, title, message, user_id,
                    metadata, created_at, updated_at
                ) VALUES ($1, 'bot', $2, $3, $4, $5::jsonb, NOW(), NOW())
            """,
                notif_type,
                title,
                message,
                user_id,
                metadata_json
            )

            logger.info(f"Created close notification for user {user_id}")

        except Exception as e:
            logger.error(f"Error creating close notification: {e}", exc_info=True)


# Create singleton instance for use across the application
bot_sltp_monitor = None


def get_bot_sltp_monitor(db_pool) -> BotSLTPMonitorService:
    """Get or create the BotSLTPMonitorService singleton"""
    global bot_sltp_monitor
    if bot_sltp_monitor is None:
        bot_sltp_monitor = BotSLTPMonitorService(db_pool)
    return bot_sltp_monitor
