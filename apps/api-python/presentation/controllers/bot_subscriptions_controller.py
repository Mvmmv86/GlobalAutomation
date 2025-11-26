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

        # If no history data, generate sample data from executions or empty
        if not pnl_history:
            # Try to build history from executions
            try:
                executions = await transaction_db.fetch("""
                    SELECT
                        DATE(bse.created_at) as exec_date,
                        COUNT(*) as trades,
                        SUM(CASE WHEN bse.status = 'success' THEN 1 ELSE 0 END) as wins
                    FROM bot_signal_executions bse
                    WHERE bse.subscription_id = $1
                        AND bse.created_at >= $2
                    GROUP BY DATE(bse.created_at)
                    ORDER BY exec_date ASC
                """, subscription_id, start_date)

                cumulative_pnl = 0
                cumulative_wins = 0
                cumulative_losses = 0

                for exec_record in executions:
                    # Simulate P&L based on wins (this is placeholder)
                    # In production, this would come from actual closed trades
                    daily_wins = exec_record["wins"] or 0
                    daily_losses = (exec_record["trades"] or 0) - daily_wins
                    daily_pnl = (daily_wins * 5) - (daily_losses * 3)  # Placeholder calculation

                    cumulative_pnl += daily_pnl
                    cumulative_wins += daily_wins
                    cumulative_losses += daily_losses

                    total_trades = cumulative_wins + cumulative_losses
                    win_rate = (cumulative_wins / total_trades * 100) if total_trades > 0 else 0

                    pnl_history.append({
                        "date": str(exec_record["exec_date"]),
                        "daily_pnl": daily_pnl,
                        "cumulative_pnl": cumulative_pnl,
                        "daily_wins": daily_wins,
                        "daily_losses": daily_losses,
                        "cumulative_wins": cumulative_wins,
                        "cumulative_losses": cumulative_losses,
                        "win_rate": round(win_rate, 2)
                    })
            except Exception as e:
                logger.warning(f"Could not build history from executions: {e}")

        # If still no data, generate empty chart data with 0 values
        if not pnl_history:
            # Generate last N days with zeros
            for i in range(min(days, 30)):
                date = (end_date - timedelta(days=days - 1 - i)).date()
                pnl_history.append({
                    "date": str(date),
                    "daily_pnl": 0,
                    "cumulative_pnl": 0,
                    "daily_wins": 0,
                    "daily_losses": 0,
                    "cumulative_wins": 0,
                    "cumulative_losses": 0,
                    "win_rate": 0
                })

        # Calculate summary metrics
        total_wins = subscription["win_count"] or 0
        total_losses = subscription["loss_count"] or 0
        total_trades = total_wins + total_losses
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        total_pnl = float(subscription["total_pnl_usd"] or 0)

        return {
            "success": True,
            "data": {
                "subscription_id": subscription_id,
                "bot_name": subscription["bot_name"],
                "summary": {
                    "total_pnl_usd": total_pnl,
                    "win_rate": round(win_rate, 2),
                    "total_wins": total_wins,
                    "total_losses": total_losses,
                    "total_trades": total_trades,
                    "total_signals": subscription["total_signals_received"] or 0,
                    "total_orders_executed": subscription["total_orders_executed"] or 0,
                    "subscribed_at": subscription["created_at"].isoformat() if subscription["created_at"] else None
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
