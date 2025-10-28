"""
Bot Broadcast Service
Handles broadcasting master signals to all active bot subscriptions
Supports multiple exchanges (Binance, Bybit, OKX, etc)
"""
import asyncio
import json
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime
from uuid import UUID

import structlog
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.exchanges.bybit_connector import BybitConnector
from infrastructure.exchanges.bingx_connector import BingXConnector
from infrastructure.exchanges.bitget_connector import BitgetConnector

logger = structlog.get_logger(__name__)


class BotBroadcastService:
    """
    Service responsible for broadcasting trading signals from master bot
    to all active client subscriptions across multiple exchanges
    """

    def __init__(self, db_pool):
        self.db = db_pool
        self.exchange_connectors = {
            "binance": BinanceConnector,
            "bybit": BybitConnector,
            "bingx": BingXConnector,
            "bitget": BitgetConnector,
        }

    async def broadcast_signal(
        self,
        bot_id: UUID,
        ticker: str,
        action: str,
        source_ip: str = "unknown",
        payload: Optional[Dict] = None
    ) -> Dict:
        """
        Broadcast a trading signal to all active subscriptions of a bot

        Args:
            bot_id: UUID of the bot sending the signal
            ticker: Trading pair (e.g., "BTCUSDT")
            action: Trade action ("buy", "sell", "close")
            source_ip: IP address of signal source
            payload: Original payload from TradingView

        Returns:
            Dict with broadcast results and statistics
        """
        start_time = datetime.utcnow()

        logger.info(
            "Starting signal broadcast",
            bot_id=str(bot_id),
            ticker=ticker,
            action=action
        )

        # 1. Get bot configuration to validate allowed_directions
        bot = await self.db.fetchrow("""
            SELECT id, name, allowed_directions
            FROM bots
            WHERE id = $1
        """, bot_id)

        if not bot:
            logger.error("Bot not found", bot_id=str(bot_id))
            raise ValueError(f"Bot {bot_id} not found")

        # 2. Validate if action is allowed based on bot configuration
        allowed_directions = bot["allowed_directions"]

        if allowed_directions == "buy_only" and action.lower() not in ["buy", "close", "close_all"]:
            logger.warning(
                "Bot only allows BUY orders, ignoring signal",
                bot_id=str(bot_id),
                action=action,
                allowed_directions=allowed_directions
            )
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            return {
                "success": False,
                "signal_id": None,
                "total_subscribers": 0,
                "successful": 0,
                "failed": 0,
                "duration_ms": duration_ms,
                "message": f"Bot '{bot['name']}' only allows BUY orders. Signal ignored."
            }

        if allowed_directions == "sell_only" and action.lower() not in ["sell", "close", "close_all"]:
            logger.warning(
                "Bot only allows SELL orders, ignoring signal",
                bot_id=str(bot_id),
                action=action,
                allowed_directions=allowed_directions
            )
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            return {
                "success": False,
                "signal_id": None,
                "total_subscribers": 0,
                "successful": 0,
                "failed": 0,
                "duration_ms": duration_ms,
                "message": f"Bot '{bot['name']}' only allows SELL orders. Signal ignored."
            }

        logger.info(
            "Signal direction validated",
            bot_id=str(bot_id),
            action=action,
            allowed_directions=allowed_directions
        )

        # 3. Create signal record
        signal_id = await self._create_signal_record(
            bot_id, ticker, action, source_ip, payload
        )

        # 4. Get all active subscriptions for this bot
        subscriptions = await self._get_active_subscriptions(bot_id)

        if not subscriptions:
            logger.warning(
                "No active subscriptions found for bot",
                bot_id=str(bot_id)
            )
            # Calculate duration even with no subscriptions
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            await self._complete_signal(signal_id, 0, 0, 0, duration_ms)
            return {
                "success": True,
                "signal_id": str(signal_id),
                "total_subscribers": 0,
                "successful": 0,
                "failed": 0,
                "duration_ms": duration_ms
            }

        logger.info(
            f"Broadcasting to {len(subscriptions)} active subscriptions",
            bot_id=str(bot_id),
            subscribers=len(subscriptions)
        )

        # 3. Execute orders for all subscriptions in parallel
        tasks = [
            self._execute_for_subscription(
                signal_id=signal_id,
                subscription=sub,
                ticker=ticker,
                action=action
            )
            for sub in subscriptions
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 4. Count successes and failures
        successful = sum(
            1 for r in results
            if not isinstance(r, Exception) and r.get("success")
        )
        failed = len(results) - successful

        # 5. Calculate broadcast duration
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # 6. Update signal record with final statistics
        await self._complete_signal(
            signal_id,
            len(subscriptions),
            successful,
            failed,
            duration_ms
        )

        logger.info(
            "Signal broadcast completed",
            signal_id=str(signal_id),
            total=len(subscriptions),
            successful=successful,
            failed=failed,
            duration_ms=duration_ms
        )

        return {
            "success": True,
            "signal_id": str(signal_id),
            "total_subscribers": len(subscriptions),
            "successful": successful,
            "failed": failed,
            "duration_ms": duration_ms
        }

    async def _create_signal_record(
        self,
        bot_id: UUID,
        ticker: str,
        action: str,
        source_ip: str,
        payload: Optional[Dict]
    ) -> UUID:
        """Create a new signal record in database"""
        # Convert payload dict to JSON string for JSONB column
        payload_json = json.dumps(payload or {})

        signal_id = await self.db.fetchval("""
            INSERT INTO bot_signals (
                bot_id, ticker, action, source_ip, payload, created_at
            ) VALUES ($1, $2, $3, $4, $5::jsonb, NOW())
            RETURNING id
        """, bot_id, ticker, action, source_ip, payload_json)

        return signal_id

    async def _get_active_subscriptions(self, bot_id: UUID) -> List[Dict]:
        """Get all active subscriptions for a bot with exchange credentials"""
        subscriptions = await self.db.fetch("""
            SELECT
                bs.id as subscription_id,
                bs.user_id,
                bs.custom_leverage,
                bs.custom_margin_usd,
                bs.custom_stop_loss_pct,
                bs.custom_take_profit_pct,
                bs.max_daily_loss_usd,
                bs.current_daily_loss_usd,
                bs.max_concurrent_positions,
                bs.current_positions,
                ea.id as exchange_account_id,
                ea.exchange,
                ea.api_key,
                ea.secret_key as api_secret,
                b.default_leverage,
                b.default_margin_usd,
                b.default_stop_loss_pct,
                b.default_take_profit_pct,
                b.market_type,
                u.email
            FROM bot_subscriptions bs
            INNER JOIN exchange_accounts ea ON ea.id = bs.exchange_account_id
            INNER JOIN bots b ON b.id = bs.bot_id
            INNER JOIN users u ON u.id = bs.user_id
            WHERE bs.bot_id = $1
              AND bs.status = 'active'
              AND ea.is_active = true
        """, bot_id)

        return [dict(sub) for sub in subscriptions]

    async def _execute_for_subscription(
        self,
        signal_id: UUID,
        subscription: Dict,
        ticker: str,
        action: str
    ) -> Dict:
        """
        Execute order for a single subscription

        Args:
            signal_id: UUID of the signal being broadcast
            subscription: Subscription data with user and exchange info
            ticker: Trading pair
            action: Trade action

        Returns:
            Dict with execution result
        """
        execution_start = datetime.utcnow()
        subscription_id = subscription["subscription_id"]
        user_id = subscription["user_id"]

        try:
            # 1. Risk management checks
            risk_check = await self._check_risk_limits(subscription)
            if not risk_check["allowed"]:
                logger.warning(
                    "Execution skipped due to risk limits",
                    user_id=str(user_id),
                    reason=risk_check["reason"]
                )
                await self._record_execution(
                    signal_id, subscription_id, user_id,
                    "skipped", None, None, None,
                    risk_check["reason"], None
                )
                return {"success": False, "skipped": True, "reason": risk_check["reason"]}

            # 2. Get effective configuration (custom or default)
            config = self._get_effective_config(subscription)

            # 3. Get exchange connector
            exchange = subscription["exchange"].lower()
            if exchange not in self.exchange_connectors:
                raise ValueError(f"Exchange {exchange} not supported yet")

            connector = self.exchange_connectors[exchange](
                api_key=subscription["api_key"],
                api_secret=subscription["api_secret"],
                testnet=False
            )

            # 4. Get current price
            current_price = await connector.get_current_price(ticker)

            # 5. Calculate quantity based on margin and leverage
            margin_usd = Decimal(str(config["margin_usd"]))
            leverage = config["leverage"]
            price = Decimal(str(current_price))

            quantity = (margin_usd * Decimal(str(leverage))) / price
            quantity = float(quantity)

            # 6. Set leverage on exchange
            if subscription["market_type"] == "futures":
                await connector.set_leverage(ticker, leverage)

            # 7. Execute order based on action
            order_result = None
            sl_order_id = None
            tp_order_id = None
            sl_price = None
            tp_price = None

            if action.lower() == "buy":
                order_result = await connector.create_futures_order(
                    symbol=ticker,
                    side="BUY",
                    order_type="MARKET",
                    quantity=quantity
                )
            elif action.lower() == "sell":
                order_result = await connector.create_futures_order(
                    symbol=ticker,
                    side="SELL",
                    order_type="MARKET",
                    quantity=quantity
                )
            elif action.lower() == "close":
                # Close existing position
                order_result = await connector.close_position(ticker)

            # 8. Create Stop Loss and Take Profit for BUY/SELL orders
            if order_result and action.lower() in ["buy", "sell"]:
                entry_price = float(order_result.get("avgPrice", current_price))
                executed_qty = float(order_result.get("executedQty", quantity))

                # Calculate SL/TP prices
                sl_tp_prices = self._calculate_sl_tp_prices(
                    action=action.lower(),
                    entry_price=entry_price,
                    stop_loss_pct=config["stop_loss_pct"],
                    take_profit_pct=config["take_profit_pct"]
                )

                sl_price = sl_tp_prices["stop_loss"]
                tp_price = sl_tp_prices["take_profit"]

                # Create SL/TP orders with retry
                sl_tp_result = await self._create_sl_tp_orders(
                    connector=connector,
                    ticker=ticker,
                    action=action.lower(),
                    quantity=executed_qty,
                    sl_price=sl_price,
                    tp_price=tp_price
                )

                sl_order_id = sl_tp_result.get("sl_order_id")
                tp_order_id = sl_tp_result.get("tp_order_id")

                logger.info(
                    "SL/TP orders created",
                    user_id=str(user_id),
                    sl_order_id=sl_order_id,
                    tp_order_id=tp_order_id,
                    sl_price=sl_price,
                    tp_price=tp_price
                )

            # 9. Calculate execution time
            execution_end = datetime.utcnow()
            execution_time_ms = int(
                (execution_end - execution_start).total_seconds() * 1000
            )

            # 10. Record successful execution with SL/TP info
            exchange_order_id = order_result.get("orderId") if order_result else None
            executed_price = order_result.get("avgPrice") or current_price
            executed_qty = order_result.get("executedQty") or quantity

            await self._record_execution(
                signal_id, subscription_id, user_id,
                "success", exchange_order_id, executed_price, executed_qty,
                None, None, execution_time_ms,
                sl_order_id, tp_order_id, sl_price, tp_price
            )

            # 10. Update subscription statistics
            await self._update_subscription_stats(subscription_id, True)

            logger.info(
                "Order executed successfully",
                user_id=str(user_id),
                ticker=ticker,
                action=action,
                exchange_order_id=exchange_order_id,
                execution_time_ms=execution_time_ms
            )

            return {
                "success": True,
                "user_id": str(user_id),
                "exchange_order_id": exchange_order_id
            }

        except Exception as e:
            logger.error(
                "Order execution failed",
                user_id=str(user_id),
                ticker=ticker,
                error=str(e),
                exc_info=True
            )

            # Record failed execution
            execution_end = datetime.utcnow()
            execution_time_ms = int(
                (execution_end - execution_start).total_seconds() * 1000
            )

            await self._record_execution(
                signal_id, subscription_id, user_id,
                "failed", None, None, None,
                str(e), None, execution_time_ms,
                None, None, None, None  # No SL/TP for failed orders
            )

            # Update subscription statistics
            await self._update_subscription_stats(subscription_id, False)

            return {
                "success": False,
                "user_id": str(user_id),
                "error": str(e)
            }

    async def _check_risk_limits(self, subscription: Dict) -> Dict:
        """Check if subscription has exceeded risk limits"""
        # Check daily loss limit
        current_loss = subscription.get("current_daily_loss_usd", 0)
        max_loss = subscription.get("max_daily_loss_usd", 999999)

        if current_loss >= max_loss:
            return {
                "allowed": False,
                "reason": f"Daily loss limit reached: ${current_loss:.2f} >= ${max_loss:.2f}"
            }

        # Check concurrent positions limit
        current_positions = subscription.get("current_positions", 0)
        max_positions = subscription.get("max_concurrent_positions", 999)

        if current_positions >= max_positions:
            return {
                "allowed": False,
                "reason": f"Max concurrent positions reached: {current_positions} >= {max_positions}"
            }

        return {"allowed": True}

    def _get_effective_config(self, subscription: Dict) -> Dict:
        """Get effective configuration (custom overrides default)"""
        return {
            "leverage": subscription["custom_leverage"] or subscription["default_leverage"],
            "margin_usd": subscription["custom_margin_usd"] or subscription["default_margin_usd"],
            "stop_loss_pct": subscription["custom_stop_loss_pct"] or subscription["default_stop_loss_pct"],
            "take_profit_pct": subscription["custom_take_profit_pct"] or subscription["default_take_profit_pct"],
        }

    def _calculate_sl_tp_prices(
        self,
        action: str,
        entry_price: float,
        stop_loss_pct: float,
        take_profit_pct: float
    ) -> Dict[str, float]:
        """
        Calculate Stop Loss and Take Profit prices based on entry price and percentages

        Args:
            action: "buy" or "sell"
            entry_price: Entry price of the order
            stop_loss_pct: Stop loss percentage (e.g., 3.0 for 3%)
            take_profit_pct: Take profit percentage (e.g., 5.0 for 5%)

        Returns:
            Dict with "stop_loss" and "take_profit" prices
        """
        if action == "buy":
            # Long position
            sl_price = entry_price * (1 - stop_loss_pct / 100)
            tp_price = entry_price * (1 + take_profit_pct / 100)
        else:  # sell
            # Short position
            sl_price = entry_price * (1 + stop_loss_pct / 100)
            tp_price = entry_price * (1 - take_profit_pct / 100)

        return {
            "stop_loss": round(sl_price, 2),
            "take_profit": round(tp_price, 2)
        }

    async def _create_sl_tp_orders(
        self,
        connector,
        ticker: str,
        action: str,
        quantity: float,
        sl_price: float,
        tp_price: float,
        max_retries: int = 3
    ) -> Dict[str, Optional[str]]:
        """
        Create Stop Loss and Take Profit orders with retry logic

        Args:
            connector: Exchange connector instance
            ticker: Trading pair
            action: "buy" or "sell" (determines exit side)
            quantity: Quantity to close
            sl_price: Stop loss trigger price
            tp_price: Take profit trigger price
            max_retries: Maximum number of retry attempts

        Returns:
            Dict with "sl_order_id" and "tp_order_id"
        """
        # Determine exit side (opposite of entry)
        exit_side = "SELL" if action == "buy" else "BUY"

        sl_order_id = None
        tp_order_id = None

        # Try to create Stop Loss with retry
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Creating Stop Loss order (attempt {attempt + 1}/{max_retries})",
                    ticker=ticker,
                    sl_price=sl_price
                )

                sl_result = await connector.create_stop_loss_order(
                    symbol=ticker,
                    side=exit_side,
                    quantity=quantity,
                    stop_price=sl_price
                )

                if sl_result.get("success"):
                    sl_order_id = sl_result.get("orderId")
                    logger.info("Stop Loss order created successfully", order_id=sl_order_id)
                    break
                else:
                    raise Exception(sl_result.get("error", "Unknown error"))

            except Exception as e:
                logger.warning(
                    f"Stop Loss creation failed (attempt {attempt + 1})",
                    error=str(e)
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    continue
                else:
                    logger.error(
                        "CRITICAL: Stop Loss creation failed after all retries",
                        ticker=ticker,
                        error=str(e)
                    )

        # Try to create Take Profit with retry
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Creating Take Profit order (attempt {attempt + 1}/{max_retries})",
                    ticker=ticker,
                    tp_price=tp_price
                )

                tp_result = await connector.create_take_profit_order(
                    symbol=ticker,
                    side=exit_side,
                    quantity=quantity,
                    stop_price=tp_price
                )

                if tp_result.get("success"):
                    tp_order_id = tp_result.get("orderId")
                    logger.info("Take Profit order created successfully", order_id=tp_order_id)
                    break
                else:
                    raise Exception(tp_result.get("error", "Unknown error"))

            except Exception as e:
                logger.warning(
                    f"Take Profit creation failed (attempt {attempt + 1})",
                    error=str(e)
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    logger.error(
                        "CRITICAL: Take Profit creation failed after all retries",
                        ticker=ticker,
                        error=str(e)
                    )

        return {
            "sl_order_id": sl_order_id,
            "tp_order_id": tp_order_id
        }

    async def _record_execution(
        self,
        signal_id: UUID,
        subscription_id: UUID,
        user_id: UUID,
        status: str,
        exchange_order_id: Optional[str],
        executed_price: Optional[float],
        executed_quantity: Optional[float],
        error_message: Optional[str],
        error_code: Optional[str],
        execution_time_ms: Optional[int] = None,
        sl_order_id: Optional[str] = None,
        tp_order_id: Optional[str] = None,
        sl_price: Optional[float] = None,
        tp_price: Optional[float] = None
    ):
        """Record execution result in database including SL/TP orders"""
        await self.db.execute("""
            INSERT INTO bot_signal_executions (
                signal_id, subscription_id, user_id, status,
                exchange_order_id, executed_price, executed_quantity,
                error_message, error_code, execution_time_ms,
                stop_loss_order_id, take_profit_order_id,
                stop_loss_price, take_profit_price,
                created_at, completed_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW(), NOW())
        """,
            signal_id, subscription_id, user_id, status,
            exchange_order_id, executed_price, executed_quantity,
            error_message, error_code, execution_time_ms,
            sl_order_id, tp_order_id, sl_price, tp_price
        )

    async def _update_subscription_stats(
        self, subscription_id: UUID, success: bool
    ):
        """Update subscription statistics after execution"""
        if success:
            await self.db.execute("""
                UPDATE bot_subscriptions
                SET total_signals_received = total_signals_received + 1,
                    total_orders_executed = total_orders_executed + 1,
                    last_signal_at = NOW(),
                    updated_at = NOW()
                WHERE id = $1
            """, subscription_id)
        else:
            await self.db.execute("""
                UPDATE bot_subscriptions
                SET total_signals_received = total_signals_received + 1,
                    total_orders_failed = total_orders_failed + 1,
                    last_signal_at = NOW(),
                    updated_at = NOW()
                WHERE id = $1
            """, subscription_id)

    async def _complete_signal(
        self,
        signal_id: UUID,
        total_subscribers: int,
        successful: int,
        failed: int,
        duration_ms: int = None
    ):
        """Mark signal as completed with final statistics"""
        await self.db.execute("""
            UPDATE bot_signals
            SET total_subscribers = $1,
                successful_executions = $2,
                failed_executions = $3,
                broadcast_duration_ms = $4,
                completed_at = NOW()
            WHERE id = $5
        """, total_subscribers, successful, failed, duration_ms, signal_id)
