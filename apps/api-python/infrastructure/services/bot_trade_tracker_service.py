"""
Bot Trade Tracker Service
Tracks closed trades and updates subscription P&L metrics
"""
import asyncio
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime, date
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class BotTradeTrackerService:
    """
    Service responsible for tracking closed trades from bot subscriptions
    and updating P&L metrics
    """

    def __init__(self, db_pool):
        self.db = db_pool

    async def record_trade_close(
        self,
        subscription_id: UUID,
        signal_execution_id: UUID,
        ticker: str,
        side: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        pnl_usd: float,
        close_reason: str = "manual"  # manual, stop_loss, take_profit
    ) -> Dict:
        """
        Record a closed trade and update subscription metrics

        Args:
            subscription_id: UUID of the bot subscription
            signal_execution_id: UUID of the original signal execution
            ticker: Trading pair (e.g., "BTCUSDT")
            side: Trade side ("buy" or "sell")
            entry_price: Entry price of the trade
            exit_price: Exit price of the trade
            quantity: Quantity traded
            pnl_usd: Profit/Loss in USD
            close_reason: How the trade was closed

        Returns:
            Dict with trade record and updated metrics
        """
        try:
            # Determine if trade was a win or loss
            is_win = pnl_usd >= 0

            # Get user_id from subscription
            sub_info = await self.db.fetchrow("""
                SELECT user_id FROM bot_subscriptions WHERE id = $1
            """, subscription_id)
            user_id = sub_info["user_id"] if sub_info else None

            # Determine direction based on side
            direction = "long" if side.lower() == "buy" else "short"

            # Calculate P&L percentage
            pnl_pct = 0
            if entry_price > 0 and quantity > 0:
                position_value = entry_price * quantity
                pnl_pct = (pnl_usd / position_value) * 100

            # 1. Check if there's an existing open trade record for this execution
            existing_trade = await self.db.fetchrow("""
                SELECT id, entry_price, entry_quantity, entry_time
                FROM bot_trades
                WHERE signal_execution_id = $1 AND status = 'open'
            """, signal_execution_id)

            if existing_trade:
                # UPDATE existing trade record (opened by bot_broadcast_service)
                trade_id = existing_trade["id"]
                # Use stored entry values if available
                stored_entry_price = float(existing_trade["entry_price"]) if existing_trade["entry_price"] else entry_price
                stored_entry_qty = float(existing_trade["entry_quantity"]) if existing_trade["entry_quantity"] else quantity

                # Recalculate P&L with stored values if different
                if stored_entry_price != entry_price:
                    if direction == "long":
                        pnl_usd = (exit_price - stored_entry_price) * stored_entry_qty
                    else:
                        pnl_usd = (stored_entry_price - exit_price) * stored_entry_qty
                    is_win = pnl_usd >= 0
                    if stored_entry_price > 0 and stored_entry_qty > 0:
                        pnl_pct = (pnl_usd / (stored_entry_price * stored_entry_qty)) * 100

                await self.db.execute("""
                    UPDATE bot_trades
                    SET exit_price = $1,
                        exit_quantity = $2,
                        exit_time = NOW(),
                        exit_reason = $3,
                        pnl_usd = $4,
                        pnl_pct = $5,
                        is_winner = $6,
                        status = 'closed',
                        updated_at = NOW()
                    WHERE id = $7
                """,
                    exit_price, quantity, close_reason,
                    pnl_usd, pnl_pct, is_win, trade_id
                )
                logger.info(f"Updated existing trade {trade_id} to closed status")
            else:
                # INSERT new trade record (fallback if open record doesn't exist)
                trade_id = await self.db.fetchval("""
                    INSERT INTO bot_trades (
                        subscription_id, user_id, signal_execution_id,
                        symbol, side, direction,
                        entry_price, entry_quantity, entry_time,
                        exit_price, exit_quantity, exit_time, exit_reason,
                        pnl_usd, pnl_pct, is_winner, status
                    ) VALUES (
                        $1, $2, $3,
                        $4, $5, $6,
                        $7, $8, NOW(),
                        $9, $10, NOW(), $11,
                        $12, $13, $14, 'closed'
                    )
                    RETURNING id
                """,
                    subscription_id, user_id, signal_execution_id,
                    ticker, side, direction,
                    entry_price, quantity,
                    exit_price, quantity, close_reason,
                    pnl_usd, pnl_pct, is_win
                )
                logger.info(f"Inserted new closed trade {trade_id}")

            # 2. Update subscription metrics
            if is_win:
                await self.db.execute("""
                    UPDATE bot_subscriptions
                    SET total_pnl_usd = total_pnl_usd + $1,
                        win_count = win_count + 1,
                        current_positions = GREATEST(current_positions - 1, 0),
                        updated_at = NOW()
                    WHERE id = $2
                """, pnl_usd, subscription_id)
            else:
                await self.db.execute("""
                    UPDATE bot_subscriptions
                    SET total_pnl_usd = total_pnl_usd + $1,
                        loss_count = loss_count + 1,
                        current_positions = GREATEST(current_positions - 1, 0),
                        current_daily_loss_usd = current_daily_loss_usd + ABS($1),
                        updated_at = NOW()
                    WHERE id = $2
                """, pnl_usd, subscription_id)

            # 3. Update or create today's P&L history entry
            await self._update_daily_pnl(subscription_id, pnl_usd, is_win)

            logger.info(
                "Trade recorded successfully",
                trade_id=str(trade_id),
                subscription_id=str(subscription_id),
                ticker=ticker,
                pnl_usd=pnl_usd,
                is_win=is_win,
                close_reason=close_reason
            )

            return {
                "success": True,
                "trade_id": str(trade_id),
                "pnl_usd": pnl_usd,
                "is_win": is_win
            }

        except Exception as e:
            logger.error(
                "Failed to record trade",
                subscription_id=str(subscription_id),
                error=str(e),
                exc_info=True
            )
            return {
                "success": False,
                "error": str(e)
            }

    async def _update_daily_pnl(
        self,
        subscription_id: UUID,
        pnl_usd: float,
        is_win: bool
    ):
        """Update or create today's P&L history entry"""
        today = date.today()

        # Get user_id and bot_id from subscription
        sub_info = await self.db.fetchrow("""
            SELECT user_id, bot_id FROM bot_subscriptions WHERE id = $1
        """, subscription_id)

        if not sub_info:
            logger.warning("Subscription not found for daily P&L update", subscription_id=str(subscription_id))
            return

        user_id = sub_info["user_id"]
        bot_id = sub_info["bot_id"]

        # Check if today's entry exists (using correct column name: snapshot_date)
        existing = await self.db.fetchrow("""
            SELECT id, daily_pnl_usd, cumulative_pnl_usd, daily_wins, daily_losses
            FROM bot_pnl_history
            WHERE subscription_id = $1 AND snapshot_date = $2
        """, subscription_id, today)

        if existing:
            # Update existing entry
            new_daily_pnl = float(existing["daily_pnl_usd"]) + pnl_usd
            new_cumulative = float(existing["cumulative_pnl_usd"]) + pnl_usd
            new_wins = existing["daily_wins"] + (1 if is_win else 0)
            new_losses = existing["daily_losses"] + (0 if is_win else 1)

            # Calculate win rate
            total_trades = new_wins + new_losses
            win_rate = (new_wins / total_trades * 100) if total_trades > 0 else 0

            await self.db.execute("""
                UPDATE bot_pnl_history
                SET daily_pnl_usd = $1,
                    cumulative_pnl_usd = $2,
                    daily_wins = $3,
                    daily_losses = $4,
                    win_rate_pct = $5,
                    updated_at = NOW()
                WHERE id = $6
            """, new_daily_pnl, new_cumulative, new_wins, new_losses, win_rate, existing["id"])
        else:
            # Get previous cumulative P&L
            prev_cumulative = await self.db.fetchval("""
                SELECT cumulative_pnl_usd
                FROM bot_pnl_history
                WHERE subscription_id = $1 AND snapshot_date < $2
                ORDER BY snapshot_date DESC
                LIMIT 1
            """, subscription_id, today)

            # If no previous entry, get from subscription total
            if prev_cumulative is None:
                # Get current total minus this trade's P&L
                subscription = await self.db.fetchrow("""
                    SELECT total_pnl_usd FROM bot_subscriptions WHERE id = $1
                """, subscription_id)
                prev_cumulative = float(subscription["total_pnl_usd"]) - pnl_usd if subscription else 0

            cumulative_pnl = float(prev_cumulative) + pnl_usd
            daily_wins = 1 if is_win else 0
            daily_losses = 0 if is_win else 1
            win_rate = 100 if is_win else 0

            # Also get cumulative wins/losses from subscription
            sub_stats = await self.db.fetchrow("""
                SELECT win_count, loss_count FROM bot_subscriptions WHERE id = $1
            """, subscription_id)

            cumulative_wins = sub_stats["win_count"] if sub_stats else daily_wins
            cumulative_losses = sub_stats["loss_count"] if sub_stats else daily_losses

            await self.db.execute("""
                INSERT INTO bot_pnl_history (
                    subscription_id, user_id, bot_id, snapshot_date,
                    daily_pnl_usd, cumulative_pnl_usd,
                    daily_wins, daily_losses, cumulative_wins, cumulative_losses,
                    win_rate_pct
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                subscription_id, user_id, bot_id, today,
                pnl_usd, cumulative_pnl,
                daily_wins, daily_losses, cumulative_wins, cumulative_losses,
                win_rate
            )

    async def process_position_close(
        self,
        subscription_id: UUID,
        ticker: str,
        exchange_order_id: str,
        realized_pnl: float
    ) -> Dict:
        """
        Process a position close event (from exchange webhook or sync)

        This method is called when we detect a position has been closed
        via SL, TP, or manual close

        Args:
            subscription_id: UUID of the bot subscription
            ticker: Trading pair
            exchange_order_id: The exchange order ID that closed the position
            realized_pnl: The realized P&L from the exchange

        Returns:
            Dict with processing result
        """
        try:
            # Find the original signal execution for this position
            execution = await self.db.fetchrow("""
                SELECT
                    bse.id as execution_id,
                    bse.executed_price as entry_price,
                    bse.executed_quantity as quantity,
                    bs.ticker as signal_ticker,
                    bs.action as side
                FROM bot_signal_executions bse
                INNER JOIN bot_signals bs ON bs.id = bse.signal_id
                WHERE bse.subscription_id = $1
                  AND bs.ticker = $2
                  AND bse.status = 'success'
                  AND bse.id NOT IN (
                      SELECT signal_execution_id FROM bot_trades
                      WHERE signal_execution_id IS NOT NULL
                  )
                ORDER BY bse.created_at DESC
                LIMIT 1
            """, subscription_id, ticker)

            if not execution:
                logger.warning(
                    "No matching open execution found for position close",
                    subscription_id=str(subscription_id),
                    ticker=ticker,
                    exchange_order_id=exchange_order_id
                )
                return {"success": False, "error": "No matching execution found"}

            # Calculate exit price from P&L
            entry_price = float(execution["entry_price"]) if execution["entry_price"] else 0
            quantity = float(execution["quantity"]) if execution["quantity"] else 0
            side = execution["side"]

            # P&L = (exit_price - entry_price) * quantity for long
            # P&L = (entry_price - exit_price) * quantity for short
            if quantity > 0 and entry_price > 0:
                if side.lower() == "buy":
                    exit_price = entry_price + (realized_pnl / quantity)
                else:
                    exit_price = entry_price - (realized_pnl / quantity)
            else:
                exit_price = entry_price  # Fallback

            # Determine close reason based on the trade
            close_reason = "manual"
            if realized_pnl > 0:
                close_reason = "take_profit"
            elif realized_pnl < 0:
                close_reason = "stop_loss"

            return await self.record_trade_close(
                subscription_id=subscription_id,
                signal_execution_id=execution["execution_id"],
                ticker=ticker,
                side=side,
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=quantity,
                pnl_usd=realized_pnl,
                close_reason=close_reason
            )

        except Exception as e:
            logger.error(
                "Failed to process position close",
                subscription_id=str(subscription_id),
                ticker=ticker,
                error=str(e),
                exc_info=True
            )
            return {"success": False, "error": str(e)}

    async def reset_daily_loss_counters(self):
        """
        Reset daily loss counters for all subscriptions
        Should be called daily at midnight UTC
        """
        try:
            result = await self.db.execute("""
                UPDATE bot_subscriptions
                SET current_daily_loss_usd = 0,
                    updated_at = NOW()
                WHERE status = 'active'
            """)

            logger.info("Daily loss counters reset successfully")
            return {"success": True}

        except Exception as e:
            logger.error(
                "Failed to reset daily loss counters",
                error=str(e),
                exc_info=True
            )
            return {"success": False, "error": str(e)}

    async def sync_position_counters(self) -> Dict:
        """
        Synchronize current_positions counters with actual open positions.

        This method:
        1. Closes ghost trades in bot_trades that have no corresponding position in exchange
        2. Recalculates current_positions for each subscription

        Should be called periodically to fix any drift in counters.

        Returns:
            Dict with sync results
        """
        try:
            logger.debug("🔄 Starting position counter sync...")

            # ============================================================
            # STEP 1: Close ghost trades in bot_trades table
            # Ghost trades = open in bot_trades but no matching position in exchange
            # ============================================================
            ghost_trades_closed = await self._close_ghost_bot_trades()

            # ============================================================
            # STEP 2: Update subscription counters based on bot_trades
            # ============================================================
            # Get all active subscriptions with their current counter
            subscriptions = await self.db.fetch("""
                SELECT bs.id, bs.current_positions, bs.exchange_account_id, b.name as bot_name
                FROM bot_subscriptions bs
                JOIN bots b ON b.id = bs.bot_id
                WHERE bs.status = 'active'
            """)

            updated_count = 0
            corrections = []

            for sub in subscriptions:
                subscription_id = sub["id"]
                current_counter = sub["current_positions"] or 0
                bot_name = sub["bot_name"]

                # Count ACTUAL open trades in bot_trades table for this subscription
                actual_open = await self.db.fetchval("""
                    SELECT COUNT(*)
                    FROM bot_trades
                    WHERE subscription_id = $1
                      AND status = 'open'
                """, subscription_id)

                actual_open = actual_open or 0

                # Update if different
                if current_counter != actual_open:
                    await self.db.execute("""
                        UPDATE bot_subscriptions
                        SET current_positions = $1,
                            updated_at = NOW()
                        WHERE id = $2
                    """, actual_open, subscription_id)

                    updated_count += 1
                    corrections.append({
                        "subscription_id": str(subscription_id),
                        "bot_name": bot_name,
                        "old_value": current_counter,
                        "new_value": actual_open
                    })

                    logger.info(
                        f"📊 Corrected {bot_name}: {current_counter} -> {actual_open}"
                    )

            if updated_count > 0 or ghost_trades_closed > 0:
                logger.info(
                    f"✅ Position counter sync: {updated_count} counter corrections, {ghost_trades_closed} ghost trades closed",
                    updated_count=updated_count,
                    ghost_trades_closed=ghost_trades_closed
                )

            return {
                "success": True,
                "total_subscriptions": len(subscriptions),
                "updated_count": updated_count,
                "ghost_trades_closed": ghost_trades_closed,
                "corrections": corrections
            }

        except Exception as e:
            logger.error(
                "Failed to sync position counters",
                error=str(e),
                exc_info=True
            )
            return {"success": False, "error": str(e)}

    async def _close_ghost_bot_trades(self) -> int:
        """
        Close ghost bot_trades that have no corresponding open position in the exchange.

        A ghost trade is one marked as 'open' in bot_trades but:
        - Has no matching position in the positions table for the same symbol/account

        Returns:
            Number of ghost trades closed
        """
        try:
            # Find all open bot_trades that don't have a matching open position
            ghost_trades = await self.db.fetch("""
                SELECT bt.id, bt.symbol, bt.side, bs.exchange_account_id, b.name as bot_name
                FROM bot_trades bt
                JOIN bot_subscriptions bs ON bs.id = bt.subscription_id
                JOIN bots b ON b.id = bs.bot_id
                WHERE bt.status = 'open'
                  AND NOT EXISTS (
                      SELECT 1 FROM positions p
                      WHERE p.exchange_account_id = bs.exchange_account_id
                        AND UPPER(p.symbol) = UPPER(bt.symbol)
                        AND p.status = 'open'
                  )
            """)

            if not ghost_trades:
                return 0

            closed_count = 0
            for trade in ghost_trades:
                await self.db.execute("""
                    UPDATE bot_trades
                    SET status = 'closed',
                        exit_reason = 'ghost_cleanup_sync',
                        updated_at = NOW()
                    WHERE id = $1
                """, trade["id"])
                closed_count += 1
                logger.info(
                    f"👻 Closed ghost trade: {trade['bot_name']} - {trade['symbol']} {trade['side']}"
                )

            return closed_count

        except Exception as e:
            logger.error(f"Error closing ghost bot trades: {e}")
            return 0

    async def generate_daily_snapshots(self):
        """
        Generate daily P&L snapshots for all active subscriptions
        Should be called once per day (at end of trading day)
        """
        try:
            today = date.today()

            # Get all active subscriptions without today's snapshot
            subscriptions = await self.db.fetch("""
                SELECT
                    bs.id,
                    bs.user_id,
                    bs.bot_id,
                    bs.total_pnl_usd,
                    bs.win_count,
                    bs.loss_count
                FROM bot_subscriptions bs
                WHERE bs.status = 'active'
                  AND NOT EXISTS (
                      SELECT 1 FROM bot_pnl_history ph
                      WHERE ph.subscription_id = bs.id AND ph.snapshot_date = $1
                  )
            """, today)

            snapshots_created = 0

            for sub in subscriptions:
                subscription_id = sub["id"]
                user_id = sub["user_id"]
                bot_id = sub["bot_id"]

                # Get yesterday's cumulative values
                prev = await self.db.fetchrow("""
                    SELECT cumulative_pnl_usd, cumulative_wins, cumulative_losses
                    FROM bot_pnl_history
                    WHERE subscription_id = $1 AND snapshot_date < $2
                    ORDER BY snapshot_date DESC
                    LIMIT 1
                """, subscription_id, today)

                prev_pnl = float(prev["cumulative_pnl_usd"]) if prev else 0
                prev_wins = prev["cumulative_wins"] if prev else 0
                prev_losses = prev["cumulative_losses"] if prev else 0

                current_pnl = float(sub["total_pnl_usd"])
                current_wins = sub["win_count"]
                current_losses = sub["loss_count"]

                daily_pnl = current_pnl - prev_pnl
                daily_wins = current_wins - prev_wins
                daily_losses = current_losses - prev_losses

                # Only create snapshot if there was activity
                if daily_pnl != 0 or daily_wins != 0 or daily_losses != 0:
                    total_daily = daily_wins + daily_losses
                    win_rate = (daily_wins / total_daily * 100) if total_daily > 0 else 0

                    await self.db.execute("""
                        INSERT INTO bot_pnl_history (
                            subscription_id, user_id, bot_id, snapshot_date,
                            daily_pnl_usd, cumulative_pnl_usd,
                            daily_wins, daily_losses, cumulative_wins, cumulative_losses,
                            win_rate_pct
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        ON CONFLICT (subscription_id, snapshot_date) DO NOTHING
                    """,
                        subscription_id, user_id, bot_id, today,
                        daily_pnl, current_pnl,
                        daily_wins, daily_losses, current_wins, current_losses,
                        win_rate
                    )
                    snapshots_created += 1

            logger.info(
                "Daily snapshots generated",
                date=str(today),
                snapshots_created=snapshots_created
            )

            return {
                "success": True,
                "date": str(today),
                "snapshots_created": snapshots_created
            }

        except Exception as e:
            logger.error(
                "Failed to generate daily snapshots",
                error=str(e),
                exc_info=True
            )
            return {"success": False, "error": str(e)}
