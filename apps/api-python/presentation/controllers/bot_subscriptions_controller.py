"""
Bot Subscriptions Controller
Handles client subscriptions to managed bots
"""
from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

import structlog

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.services.bot_trade_tracker_service import BotTradeTrackerService

logger = structlog.get_logger(__name__)

# Initialize trade tracker service
trade_tracker = BotTradeTrackerService(transaction_db)

router = APIRouter(prefix="/api/v1/bot-subscriptions", tags=["bot-subscriptions"])


# ============================================================================
# Pydantic Models
# ============================================================================

class SubscriptionCreate(BaseModel):
    """Model for creating a bot subscription"""
    bot_id: str = Field(..., description="UUID of the bot to subscribe to")
    exchange_account_id: str = Field(..., description="UUID of exchange account to use")
    custom_leverage: Optional[int] = Field(None, ge=1, le=125)
    custom_margin_usd: Optional[float] = Field(None, ge=5.00)
    custom_stop_loss_pct: Optional[float] = Field(None, ge=0.1, le=50.0)
    custom_take_profit_pct: Optional[float] = Field(None, ge=0.1, le=100.0)
    max_daily_loss_usd: float = Field(default=200.00, ge=10.00)
    max_concurrent_positions: int = Field(default=3, ge=1, le=10)


class SubscriptionUpdate(BaseModel):
    """Model for updating subscription configuration"""
    status: Optional[str] = Field(None, pattern="^(active|paused|cancelled)$")
    custom_leverage: Optional[int] = Field(None, ge=1, le=125)
    custom_margin_usd: Optional[float] = Field(None, ge=5.00)
    custom_stop_loss_pct: Optional[float] = Field(None, ge=0.1, le=50.0)
    custom_take_profit_pct: Optional[float] = Field(None, ge=0.1, le=100.0)
    max_daily_loss_usd: Optional[float] = Field(None, ge=10.00)
    max_concurrent_positions: Optional[int] = Field(None, ge=1, le=10)


class TradeCloseRecord(BaseModel):
    """Model for recording a closed trade"""
    ticker: str = Field(..., description="Trading pair (e.g., BTCUSDT)")
    exchange_order_id: str = Field(..., description="Exchange order ID that closed the position")
    realized_pnl: float = Field(..., description="Realized P&L in USD")


# ============================================================================
# CLIENT ENDPOINTS
# ============================================================================

@router.get("/available-bots")
async def get_available_bots():
    """
    Get list of all available bots that clients can subscribe to
    Returns only active bots with their statistics
    """
    try:
        bots = await transaction_db.fetch("""
            SELECT
                id, name, description, market_type,
                default_leverage, default_margin_usd,
                default_stop_loss_pct, default_take_profit_pct,
                total_subscribers, total_signals_sent,
                avg_win_rate, avg_pnl_pct,
                created_at
            FROM bots
            WHERE status = 'active'
            ORDER BY total_subscribers DESC, created_at DESC
        """)

        return {
            "success": True,
            "data": [dict(bot) for bot in bots]
        }

    except Exception as e:
        logger.error("Error getting available bots", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-subscriptions")
async def get_my_subscriptions(user_id: str):
    """Get all bot subscriptions for current user"""
    try:
        subscriptions = await transaction_db.fetch("""
            SELECT
                bs.id,
                bs.status,
                bs.custom_leverage,
                bs.custom_margin_usd,
                bs.custom_stop_loss_pct,
                bs.custom_take_profit_pct,
                bs.max_daily_loss_usd,
                bs.max_concurrent_positions,
                bs.current_daily_loss_usd,
                bs.current_positions,
                bs.total_signals_received,
                bs.total_orders_executed,
                bs.total_orders_failed,
                bs.total_pnl_usd,
                bs.win_count,
                bs.loss_count,
                bs.created_at,
                bs.last_signal_at,
                b.id as bot_id,
                b.name as bot_name,
                b.description as bot_description,
                b.market_type,
                b.default_leverage,
                b.default_margin_usd,
                b.default_stop_loss_pct,
                b.default_take_profit_pct,
                ea.exchange,
                ea.name as account_name
            FROM bot_subscriptions bs
            INNER JOIN bots b ON b.id = bs.bot_id
            INNER JOIN exchange_accounts ea ON ea.id = bs.exchange_account_id
            WHERE bs.user_id = $1
            ORDER BY bs.created_at DESC
        """, user_id)

        return {
            "success": True,
            "data": [dict(sub) for sub in subscriptions]
        }

    except Exception as e:
        logger.error("Error getting user subscriptions", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def subscribe_to_bot(
    subscription_data: SubscriptionCreate,
    user_id: str = Query(..., description="User ID subscribing to the bot")
):
    """
    Subscribe to a bot
    Creates a new subscription for the user with custom configuration
    """
    try:
        # Verify bot exists and is active
        bot = await transaction_db.fetchrow("""
            SELECT id, name, status
            FROM bots
            WHERE id = $1
        """, subscription_data.bot_id)

        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        if bot["status"] != "active":
            raise HTTPException(
                status_code=400,
                detail=f"Bot is {bot['status']}, cannot subscribe"
            )

        # Verify exchange account exists and belongs to user
        exchange_account = await transaction_db.fetchrow("""
            SELECT id, exchange, is_active
            FROM exchange_accounts
            WHERE id = $1 AND user_id = $2
        """, subscription_data.exchange_account_id, user_id)

        if not exchange_account:
            raise HTTPException(
                status_code=404,
                detail="Exchange account not found or doesn't belong to you"
            )

        if not exchange_account["is_active"]:
            raise HTTPException(
                status_code=400,
                detail="Exchange account is not active"
            )

        # Check if subscription already exists
        existing = await transaction_db.fetchval("""
            SELECT id
            FROM bot_subscriptions
            WHERE user_id = $1 AND bot_id = $2
        """, user_id, subscription_data.bot_id)

        if existing:
            raise HTTPException(
                status_code=400,
                detail="You are already subscribed to this bot"
            )

        # Create subscription
        subscription_id = await transaction_db.fetchval("""
            INSERT INTO bot_subscriptions (
                user_id, bot_id, exchange_account_id, status,
                custom_leverage, custom_margin_usd,
                custom_stop_loss_pct, custom_take_profit_pct,
                max_daily_loss_usd, max_concurrent_positions
            ) VALUES ($1, $2, $3, 'active', $4, $5, $6, $7, $8, $9)
            RETURNING id
        """,
            user_id,
            subscription_data.bot_id,
            subscription_data.exchange_account_id,
            subscription_data.custom_leverage,
            subscription_data.custom_margin_usd,
            subscription_data.custom_stop_loss_pct,
            subscription_data.custom_take_profit_pct,
            subscription_data.max_daily_loss_usd,
            subscription_data.max_concurrent_positions
        )

        # Update bot subscriber count
        await transaction_db.execute("""
            UPDATE bots
            SET total_subscribers = total_subscribers + 1,
                updated_at = NOW()
            WHERE id = $1
        """, subscription_data.bot_id)

        logger.info(
            "Bot subscription created",
            user_id=user_id,
            bot_id=subscription_data.bot_id,
            subscription_id=str(subscription_id)
        )

        return {
            "success": True,
            "data": {"subscription_id": str(subscription_id)},
            "message": f"Successfully subscribed to {bot['name']}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating subscription", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{subscription_id}")
async def get_subscription(subscription_id: str, user_id: str):
    """Get detailed information about a specific subscription"""
    try:
        subscription = await transaction_db.fetchrow("""
            SELECT
                bs.*,
                b.name as bot_name,
                b.description as bot_description,
                b.market_type,
                b.default_leverage,
                b.default_margin_usd,
                b.default_stop_loss_pct,
                b.default_take_profit_pct,
                ea.exchange,
                ea.name as account_name
            FROM bot_subscriptions bs
            INNER JOIN bots b ON b.id = bs.bot_id
            INNER JOIN exchange_accounts ea ON ea.id = bs.exchange_account_id
            WHERE bs.id = $1 AND bs.user_id = $2
        """, subscription_id, user_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Get recent executions for this subscription
        recent_executions = await transaction_db.fetch("""
            SELECT
                bse.id,
                bse.status,
                bse.exchange_order_id,
                bse.executed_price,
                bse.executed_quantity,
                bse.error_message,
                bse.execution_time_ms,
                bse.created_at,
                bs_signal.ticker,
                bs_signal.action
            FROM bot_signal_executions bse
            INNER JOIN bot_signals bs_signal ON bs_signal.id = bse.signal_id
            WHERE bse.subscription_id = $1
            ORDER BY bse.created_at DESC
            LIMIT 20
        """, subscription_id)

        return {
            "success": True,
            "data": {
                **dict(subscription),
                "recent_executions": [dict(e) for e in recent_executions]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error getting subscription",
            subscription_id=subscription_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{subscription_id}")
async def update_subscription(
    subscription_id: str,
    subscription_data: SubscriptionUpdate,
    user_id: str
):
    """Update subscription configuration"""
    try:
        # Verify subscription exists and belongs to user
        existing = await transaction_db.fetchrow("""
            SELECT id, status
            FROM bot_subscriptions
            WHERE id = $1 AND user_id = $2
        """, subscription_id, user_id)

        if not existing:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Build dynamic update query
        updates = []
        params = []
        param_idx = 1

        if subscription_data.status is not None:
            updates.append(f"status = ${param_idx}")
            params.append(subscription_data.status)
            param_idx += 1

        if subscription_data.custom_leverage is not None:
            updates.append(f"custom_leverage = ${param_idx}")
            params.append(subscription_data.custom_leverage)
            param_idx += 1

        if subscription_data.custom_margin_usd is not None:
            updates.append(f"custom_margin_usd = ${param_idx}")
            params.append(subscription_data.custom_margin_usd)
            param_idx += 1

        if subscription_data.custom_stop_loss_pct is not None:
            updates.append(f"custom_stop_loss_pct = ${param_idx}")
            params.append(subscription_data.custom_stop_loss_pct)
            param_idx += 1

        if subscription_data.custom_take_profit_pct is not None:
            updates.append(f"custom_take_profit_pct = ${param_idx}")
            params.append(subscription_data.custom_take_profit_pct)
            param_idx += 1

        if subscription_data.max_daily_loss_usd is not None:
            updates.append(f"max_daily_loss_usd = ${param_idx}")
            params.append(subscription_data.max_daily_loss_usd)
            param_idx += 1

        if subscription_data.max_concurrent_positions is not None:
            updates.append(f"max_concurrent_positions = ${param_idx}")
            params.append(subscription_data.max_concurrent_positions)
            param_idx += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append("updated_at = NOW()")
        params.append(subscription_id)

        query = f"""
            UPDATE bot_subscriptions
            SET {', '.join(updates)}
            WHERE id = ${param_idx}
        """

        await transaction_db.execute(query, *params)

        logger.info("Subscription updated", subscription_id=subscription_id, user_id=user_id)

        return {
            "success": True,
            "message": "Subscription updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error updating subscription",
            subscription_id=subscription_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{subscription_id}")
async def unsubscribe_from_bot(subscription_id: str, user_id: str):
    """
    Unsubscribe from a bot
    Marks subscription as cancelled
    """
    try:
        # Verify subscription exists and belongs to user
        subscription = await transaction_db.fetchrow("""
            SELECT id, bot_id
            FROM bot_subscriptions
            WHERE id = $1 AND user_id = $2
        """, subscription_id, user_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Cancel subscription
        await transaction_db.execute("""
            UPDATE bot_subscriptions
            SET status = 'cancelled', updated_at = NOW()
            WHERE id = $1
        """, subscription_id)

        # Update bot subscriber count
        await transaction_db.execute("""
            UPDATE bots
            SET total_subscribers = GREATEST(total_subscribers - 1, 0),
                updated_at = NOW()
            WHERE id = $1
        """, subscription["bot_id"])

        logger.info(
            "Bot subscription cancelled",
            user_id=user_id,
            subscription_id=subscription_id
        )

        return {
            "success": True,
            "message": "Successfully unsubscribed from bot"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error unsubscribing",
            subscription_id=subscription_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{subscription_id}/performance")
async def get_subscription_performance(
    subscription_id: str,
    user_id: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to fetch history")
):
    """
    Get performance metrics and P&L history for a subscription.
    Used for charts in the BotDetailsModal.
    ALL statistics are filtered by the date range (days parameter).
    """
    try:
        # Verify subscription exists and belongs to user
        subscription = await transaction_db.fetchrow("""
            SELECT
                bs.id,
                bs.bot_id,
                bs.total_pnl_usd,
                bs.win_count,
                bs.loss_count,
                bs.total_signals_received,
                bs.total_orders_executed,
                bs.current_positions,
                bs.max_concurrent_positions,
                bs.created_at,
                b.name as bot_name
            FROM bot_subscriptions bs
            INNER JOIN bots b ON b.id = bs.bot_id
            WHERE bs.id = $1 AND bs.user_id = $2
        """, subscription_id, user_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # =====================================================
        # FILTERED STATISTICS - Based on date range (days)
        # =====================================================

        # Get filtered signals count from bot_signal_executions
        # Signals = unique signals received for this subscription
        # Trades = total executions (orders placed)
        filtered_signals = await transaction_db.fetchrow("""
            SELECT
                COUNT(DISTINCT bse.signal_id) as signals_count,
                COUNT(*) as total_executions,
                COUNT(*) FILTER (WHERE bse.status = 'success') as executed_count,
                COUNT(*) FILTER (WHERE bse.status = 'failed') as failed_count
            FROM bot_signal_executions bse
            WHERE bse.subscription_id = $1
                AND bse.created_at >= $2
        """, subscription_id, start_date)

        # Try to get from bot_trades first (if populated)
        filtered_trades = await transaction_db.fetchrow("""
            SELECT
                COUNT(*) as total_trades,
                COUNT(*) FILTER (WHERE is_winner = true) as wins,
                COUNT(*) FILTER (WHERE is_winner = false) as losses,
                COALESCE(SUM(pnl_usd), 0) as total_pnl
            FROM bot_trades
            WHERE subscription_id = $1
                AND status = 'closed'
                AND exit_time >= $2
        """, subscription_id, start_date)

        # Get ALL trades count from bot_trades (open + closed)
        all_trades_count = await transaction_db.fetchrow("""
            SELECT
                COUNT(*) as total_all_trades,
                COUNT(*) FILTER (WHERE status = 'open') as open_trades,
                COUNT(*) FILTER (WHERE status = 'closed') as closed_trades
            FROM bot_trades
            WHERE subscription_id = $1
                AND entry_time >= $2
        """, subscription_id, start_date)

        # FALLBACK: If bot_trades is empty, use bot_signal_executions as "trades"
        # Each successful execution = 1 trade
        bot_trades_count = all_trades_count["total_all_trades"] or 0 if all_trades_count else 0
        use_executions_as_trades = bot_trades_count == 0

        # Calculate filtered statistics
        filtered_signals_count = filtered_signals["signals_count"] or 0 if filtered_signals else 0
        filtered_executed_count = filtered_signals["executed_count"] or 0 if filtered_signals else 0
        total_executions = filtered_signals["total_executions"] or 0 if filtered_signals else 0

        if use_executions_as_trades:
            # FALLBACK MODE: bot_trades is empty, use executions as trades
            # In this case, each successful execution = 1 trade (position opened)
            # We don't have win/loss data yet because trades aren't being tracked to bot_trades
            filtered_total_trades = filtered_executed_count  # Successful executions = trades
            filtered_wins = subscription["win_count"] or 0  # Use subscription's stored values
            filtered_losses = subscription["loss_count"] or 0
            filtered_closed_trades = filtered_wins + filtered_losses
            filtered_win_rate = (filtered_wins / filtered_closed_trades * 100) if filtered_closed_trades > 0 else 0
            filtered_pnl = float(subscription["total_pnl_usd"] or 0)  # Use subscription's stored P&L
            open_trades_count = 0  # Can't determine from executions alone
            logger.info(f"Using bot_signal_executions as trades source (bot_trades empty). Total trades: {filtered_total_trades}")
        else:
            # NORMAL MODE: bot_trades has data
            filtered_wins = filtered_trades["wins"] or 0 if filtered_trades else 0
            filtered_losses = filtered_trades["losses"] or 0 if filtered_trades else 0
            filtered_closed_trades = filtered_wins + filtered_losses
            filtered_win_rate = (filtered_wins / filtered_closed_trades * 100) if filtered_closed_trades > 0 else 0
            filtered_pnl = float(filtered_trades["total_pnl"] or 0) if filtered_trades else 0
            filtered_total_trades = all_trades_count["total_all_trades"] or 0 if all_trades_count else 0
            open_trades_count = all_trades_count["open_trades"] or 0 if all_trades_count else 0

        # Try to get P&L history from bot_pnl_history table
        pnl_history = []
        try:
            history_records = await transaction_db.fetch("""
                SELECT
                    snapshot_date,
                    daily_pnl_usd,
                    cumulative_pnl_usd,
                    daily_wins,
                    daily_losses,
                    cumulative_wins,
                    cumulative_losses,
                    win_rate_pct
                FROM bot_pnl_history
                WHERE subscription_id = $1
                    AND snapshot_date >= $2
                ORDER BY snapshot_date ASC
            """, subscription_id, start_date.date())

            pnl_history = [
                {
                    "date": str(record["snapshot_date"]),
                    "daily_pnl": float(record["daily_pnl_usd"]),
                    "cumulative_pnl": float(record["cumulative_pnl_usd"]),
                    "daily_wins": record["daily_wins"],
                    "daily_losses": record["daily_losses"],
                    "cumulative_wins": record["cumulative_wins"],
                    "cumulative_losses": record["cumulative_losses"],
                    "win_rate": float(record["win_rate_pct"])
                }
                for record in history_records
            ]
        except Exception as e:
            # Table may not exist yet, generate mock data for demo
            logger.warning(f"Could not fetch P&L history: {e}")

        # If no history data, build from actual bot_trades table
        if not pnl_history:
            try:
                # Get closed trades grouped by date with REAL P&L values
                trades_by_date = await transaction_db.fetch("""
                    SELECT
                        DATE(exit_time) as trade_date,
                        SUM(pnl_usd) as daily_pnl,
                        COUNT(*) as daily_trades,
                        SUM(CASE WHEN is_winner = true THEN 1 ELSE 0 END) as daily_wins,
                        SUM(CASE WHEN is_winner = false THEN 1 ELSE 0 END) as daily_losses
                    FROM bot_trades
                    WHERE subscription_id = $1
                        AND status = 'closed'
                        AND exit_time >= $2
                    GROUP BY DATE(exit_time)
                    ORDER BY trade_date ASC
                """, subscription_id, start_date)

                cumulative_pnl = 0
                cumulative_trades = 0
                cumulative_wins = 0
                cumulative_losses = 0

                for trade_record in trades_by_date:
                    daily_pnl = float(trade_record["daily_pnl"] or 0)
                    daily_trades = trade_record["daily_trades"] or 0
                    daily_wins = trade_record["daily_wins"] or 0
                    daily_losses = trade_record["daily_losses"] or 0

                    cumulative_pnl += daily_pnl
                    cumulative_trades += daily_trades
                    cumulative_wins += daily_wins
                    cumulative_losses += daily_losses

                    total_trades = cumulative_wins + cumulative_losses
                    win_rate = (cumulative_wins / total_trades * 100) if total_trades > 0 else 0

                    pnl_history.append({
                        "date": str(trade_record["trade_date"]),
                        "daily_pnl": round(daily_pnl, 2),
                        "cumulative_pnl": round(cumulative_pnl, 2),
                        "daily_trades": daily_trades,
                        "cumulative_trades": cumulative_trades,
                        "daily_wins": daily_wins,
                        "daily_losses": daily_losses,
                        "cumulative_wins": cumulative_wins,
                        "cumulative_losses": cumulative_losses,
                        "win_rate": round(win_rate, 2)
                    })

                logger.info(f"Built P&L history from {len(pnl_history)} days of bot_trades for subscription {subscription_id}")

            except Exception as e:
                logger.warning(f"Could not build history from bot_trades: {e}")

        # If still no data, generate empty chart data with 0 values
        if not pnl_history:
            # Generate last N days with zeros
            for i in range(min(days, 30)):
                date = (end_date - timedelta(days=days - 1 - i)).date()
                pnl_history.append({
                    "date": str(date),
                    "daily_pnl": 0,
                    "cumulative_pnl": 0,
                    "daily_trades": 0,
                    "cumulative_trades": 0,
                    "daily_wins": 0,
                    "daily_losses": 0,
                    "cumulative_wins": 0,
                    "cumulative_losses": 0,
                    "win_rate": 0
                })

        # Calculate summary metrics (ALL-TIME)
        total_wins = subscription["win_count"] or 0
        total_losses = subscription["loss_count"] or 0
        total_trades_alltime = total_wins + total_losses
        win_rate = (total_wins / total_trades_alltime * 100) if total_trades_alltime > 0 else 0
        total_pnl = float(subscription["total_pnl_usd"] or 0)

        # Get BOT positions - only count positions opened by THIS BOT
        # Instead of fetching ALL exchange positions, we filter by bot signal executions
        realtime_positions = 0
        realtime_positions_data = []
        try:
            # Get symbols that this bot has opened positions for (via signal executions)
            # These are positions that haven't been closed yet (no matching bot_trade with status='closed')
            bot_open_positions = await transaction_db.fetch("""
                SELECT DISTINCT
                    bs_sig.ticker as symbol,
                    bs_sig.action as side,
                    bse.executed_price as entry_price,
                    bse.executed_quantity as size,
                    bse.created_at as entry_time
                FROM bot_signal_executions bse
                INNER JOIN bot_signals bs_sig ON bs_sig.id = bse.signal_id
                WHERE bse.subscription_id = $1
                  AND bse.status = 'success'
                  AND bse.id NOT IN (
                      SELECT signal_execution_id FROM bot_trades
                      WHERE signal_execution_id IS NOT NULL AND status = 'closed'
                  )
                ORDER BY bse.created_at DESC
            """, subscription_id)

            bot_symbols = set()
            for pos in bot_open_positions:
                symbol = pos["symbol"].replace("-", "").replace("USDT", "") + "USDT"
                bot_symbols.add(symbol)

            logger.info(f"Bot {subscription_id} has {len(bot_symbols)} open positions from signals: {bot_symbols}")

            # Now get REAL-TIME data for only these bot positions from exchange
            exchange_account = await transaction_db.fetchrow("""
                SELECT ea.id, ea.exchange, ea.api_key, ea.secret_key, ea.testnet
                FROM bot_subscriptions bs
                INNER JOIN exchange_accounts ea ON ea.id = bs.exchange_account_id
                WHERE bs.id = $1
            """, subscription_id)

            if exchange_account and bot_symbols:
                exchange_type = exchange_account["exchange"].lower()
                api_key = exchange_account["api_key"]
                api_secret = exchange_account["secret_key"]
                is_testnet = exchange_account["testnet"] or False

                if exchange_type == "bingx":
                    from infrastructure.exchanges.bingx_connector import BingXConnector
                    connector = BingXConnector(api_key=api_key, api_secret=api_secret, testnet=is_testnet)
                    try:
                        positions_result = await connector.get_futures_positions()
                        if positions_result.get("success"):
                            exchange_positions = positions_result.get("positions", [])
                            # Filter only positions that match bot's open signals
                            for pos in exchange_positions:
                                pos_symbol = pos.get("symbol", "").replace("-", "")
                                if pos_symbol in bot_symbols:
                                    realtime_positions += 1
                                    realtime_positions_data.append({
                                        "symbol": pos_symbol,
                                        "side": "LONG" if float(pos.get("positionAmt", 0)) > 0 else "SHORT",
                                        "entry_price": float(pos.get("avgPrice", pos.get("entryPrice", 0))),
                                        "size": abs(float(pos.get("positionAmt", 0))),
                                        "unrealized_pnl": float(pos.get("unrealizedProfit", 0)),
                                        "mark_price": float(pos.get("markPrice", 0)),
                                        "leverage": int(pos.get("leverage", 1)),
                                        "liquidation_price": float(pos.get("liquidationPrice", 0))
                                    })
                            logger.info(f"Filtered {realtime_positions} BOT positions from {len(exchange_positions)} total BingX positions")
                    finally:
                        await connector.close()

                elif exchange_type == "binance":
                    from infrastructure.exchanges.binance_connector import BinanceConnector
                    connector = BinanceConnector(api_key=api_key, api_secret=api_secret, testnet=is_testnet)
                    try:
                        positions_result = await connector.get_futures_positions()
                        if positions_result.get("success"):
                            exchange_positions = positions_result.get("positions", [])
                            # Filter only positions that match bot's open signals
                            for pos in exchange_positions:
                                pos_symbol = pos.get("symbol", "")
                                if pos_symbol in bot_symbols:
                                    realtime_positions += 1
                                    realtime_positions_data.append({
                                        "symbol": pos_symbol,
                                        "side": pos.get("positionSide", "LONG"),
                                        "entry_price": float(pos.get("entryPrice", 0)),
                                        "size": abs(float(pos.get("positionAmt", 0))),
                                        "unrealized_pnl": float(pos.get("unrealizedProfit", 0)),
                                        "mark_price": float(pos.get("markPrice", 0)),
                                        "leverage": int(pos.get("leverage", 1)),
                                        "liquidation_price": float(pos.get("liquidationPrice", 0))
                                    })
                            logger.info(f"Filtered {realtime_positions} BOT positions from {len(exchange_positions)} total Binance positions")
                    finally:
                        await connector.close()
            elif not bot_symbols:
                # No open bot positions - use signal execution count as fallback
                realtime_positions = len(bot_open_positions)
                realtime_positions_data = [
                    {
                        "symbol": pos["symbol"].replace("-", ""),
                        "side": pos["side"].upper() if pos["side"] else "LONG",
                        "entry_price": float(pos["entry_price"]) if pos["entry_price"] else 0,
                        "size": float(pos["size"]) if pos["size"] else 0,
                        "unrealized_pnl": 0,
                        "entry_time": pos["entry_time"].isoformat() if pos["entry_time"] else None
                    }
                    for pos in bot_open_positions
                ]
        except Exception as e:
            logger.warning(f"Could not fetch bot positions: {e}")
            realtime_positions = subscription["current_positions"] or 0

        return {
            "success": True,
            "data": {
                "subscription_id": subscription_id,
                "bot_name": subscription["bot_name"],
                "days_filter": days,
                # FILTERED statistics based on date range (days parameter)
                "filtered_summary": {
                    "total_pnl_usd": round(filtered_pnl, 2),
                    "win_rate": round(filtered_win_rate, 2),
                    "total_wins": filtered_wins,
                    "total_losses": filtered_losses,
                    "total_trades": filtered_total_trades,  # ALL trades (open + closed)
                    "closed_trades": filtered_closed_trades,  # Only closed trades
                    "open_trades": open_trades_count,  # Currently open trades
                    "total_signals": filtered_signals_count,
                    "total_orders_executed": filtered_executed_count,
                    "period_label": f"Ultimos {days} dias"
                },
                # ALL-TIME statistics (for reference)
                "all_time_summary": {
                    "total_pnl_usd": round(total_pnl, 2),
                    "win_rate": round(win_rate, 2),
                    "total_wins": total_wins,
                    "total_losses": total_losses,
                    "total_trades": total_trades_alltime,
                    "total_signals": subscription["total_signals_received"] or 0,
                    "total_orders_executed": subscription["total_orders_executed"] or 0,
                    "subscribed_at": subscription["created_at"].isoformat() if subscription["created_at"] else None
                },
                # Current state (REAL-TIME from exchange)
                "current_state": {
                    "current_positions": realtime_positions,
                    "max_concurrent_positions": subscription["max_concurrent_positions"] or 3,
                    "positions_data": realtime_positions_data  # Detailed position info
                },
                "pnl_history": pnl_history
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error getting subscription performance",
            subscription_id=subscription_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{subscription_id}/record-trade-close")
async def record_trade_close(
    subscription_id: str,
    trade_data: TradeCloseRecord,
    user_id: str = Query(..., description="User ID for verification")
):
    """
    Record a closed trade from an exchange webhook or polling.
    This endpoint is called when a SL/TP order is triggered on the exchange.

    Updates:
    - bot_trades table with the trade record
    - bot_subscriptions with updated P&L, win_count, loss_count
    - bot_pnl_history with daily snapshot
    """
    try:
        # Verify subscription exists and belongs to user
        subscription = await transaction_db.fetchrow("""
            SELECT id FROM bot_subscriptions
            WHERE id = $1 AND user_id = $2
        """, subscription_id, user_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Process the position close
        result = await trade_tracker.process_position_close(
            subscription_id=UUID(subscription_id),
            ticker=trade_data.ticker,
            exchange_order_id=trade_data.exchange_order_id,
            realized_pnl=trade_data.realized_pnl
        )

        if result.get("success"):
            return {
                "success": True,
                "data": {
                    "trade_id": result.get("trade_id"),
                    "pnl_usd": result.get("pnl_usd"),
                    "is_win": result.get("is_win")
                },
                "message": "Trade recorded successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to record trade"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error recording trade close",
            subscription_id=subscription_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily-snapshots")
async def generate_daily_snapshots():
    """
    Generate daily P&L snapshots for all active subscriptions.
    This endpoint should be called by a cron job at end of each trading day.
    """
    try:
        result = await trade_tracker.generate_daily_snapshots()

        if result.get("success"):
            return {
                "success": True,
                "data": {
                    "date": result.get("date"),
                    "snapshots_created": result.get("snapshots_created")
                },
                "message": "Daily snapshots generated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to generate snapshots"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error generating daily snapshots",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-daily-loss")
async def reset_daily_loss_counters():
    """
    Reset daily loss counters for all active subscriptions.
    This endpoint should be called by a cron job at midnight UTC.
    """
    try:
        result = await trade_tracker.reset_daily_loss_counters()

        if result.get("success"):
            return {
                "success": True,
                "message": "Daily loss counters reset successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to reset counters"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error resetting daily loss counters",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
