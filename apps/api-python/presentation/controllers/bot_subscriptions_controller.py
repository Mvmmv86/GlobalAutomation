"""
Bot Subscriptions Controller
Handles client subscriptions to managed bots
"""
from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta

import structlog

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.services.bot_trade_tracker_service import BotTradeTrackerService

logger = structlog.get_logger(__name__)


# ============================================================================
# Helper Functions for Exchange P&L Fetching
# ============================================================================

async def fetch_pnl_from_exchange(
    exchange_type: str,
    api_key: str,
    api_secret: str,
    is_testnet: bool,
    symbols: List[str],
    start_time: int,
    end_time: int
) -> Dict[str, Any]:
    """
    Fetch realized P&L directly from exchange API.

    Args:
        exchange_type: 'bingx' or 'binance'
        api_key: Exchange API key
        api_secret: Exchange API secret
        is_testnet: Whether to use testnet
        symbols: List of symbols to filter (e.g., ['AAVEUSDT', 'BTCUSDT'])
        start_time: Start timestamp in milliseconds
        end_time: End timestamp in milliseconds

    Returns:
        Dict with success, total_pnl, pnl_by_symbol, pnl_history
    """
    result = {
        "success": False,
        "total_pnl": 0.0,
        "pnl_by_symbol": {},
        "pnl_history": [],
        "trades_list": [],  # Individual trades list
        "wins": 0,
        "losses": 0,
        "source": "exchange",
        "error": None
    }

    try:
        if exchange_type == "bingx":
            from infrastructure.exchanges.bingx_connector import BingXConnector
            connector = BingXConnector(api_key=api_key, api_secret=api_secret, testnet=is_testnet)

            try:
                # Fetch REALIZED_PNL income history
                income_result = await connector.get_futures_income_history(
                    income_type="REALIZED_PNL",
                    start_time=start_time,
                    end_time=end_time,
                    limit=1000
                )

                if income_result.get("success"):
                    income_history = income_result.get("income_history", [])

                    total_pnl = 0.0
                    pnl_by_symbol = {}
                    pnl_by_date = {}
                    trades_list = []
                    wins = 0
                    losses = 0

                    # Sort by time first
                    sorted_income = sorted(income_history, key=lambda x: x.get("time", 0))

                    for idx, record in enumerate(sorted_income, 1):
                        symbol = record.get("symbol", "").replace("-", "").replace("USDT", "") + "USDT"
                        original_symbol = record.get("symbol", "")
                        income_amount = float(record.get("income", 0))
                        timestamp = record.get("time", 0)

                        # Filter by symbols if provided
                        if symbols and symbol not in symbols:
                            continue

                        total_pnl += income_amount

                        # Count wins/losses
                        if income_amount > 0:
                            wins += 1
                            status = "WIN"
                        elif income_amount < 0:
                            losses += 1
                            status = "LOSS"
                        else:
                            status = "BREAK-EVEN"

                        # Build individual trade record
                        date_time_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S") if timestamp else "N/A"
                        trades_list.append({
                            "index": idx,
                            "datetime": date_time_str,
                            "symbol": original_symbol,
                            "pnl": round(income_amount, 2),
                            "status": status
                        })

                        # Aggregate by symbol
                        if symbol not in pnl_by_symbol:
                            pnl_by_symbol[symbol] = 0.0
                        pnl_by_symbol[symbol] += income_amount

                        # Aggregate by date for chart
                        if timestamp:
                            date_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")
                            if date_str not in pnl_by_date:
                                pnl_by_date[date_str] = {"pnl": 0.0, "count": 0}
                            pnl_by_date[date_str]["pnl"] += income_amount
                            pnl_by_date[date_str]["count"] += 1

                    # Convert to sorted history list
                    pnl_history = []
                    cumulative = 0.0
                    for date_str in sorted(pnl_by_date.keys()):
                        daily_pnl = pnl_by_date[date_str]["pnl"]
                        cumulative += daily_pnl
                        pnl_history.append({
                            "date": date_str,
                            "daily_pnl": round(daily_pnl, 2),
                            "cumulative_pnl": round(cumulative, 2),
                            "trades_count": pnl_by_date[date_str]["count"]
                        })

                    result["success"] = True
                    result["total_pnl"] = round(total_pnl, 2)
                    result["pnl_by_symbol"] = {k: round(v, 2) for k, v in pnl_by_symbol.items()}
                    result["pnl_history"] = pnl_history
                    result["trades_list"] = trades_list
                    result["wins"] = wins
                    result["losses"] = losses

                    logger.info(f"Fetched P&L from BingX: total={total_pnl:.2f}, trades={len(trades_list)}, wins={wins}, losses={losses}")
                else:
                    result["error"] = income_result.get("error", "Failed to fetch income history")
                    logger.warning(f"BingX income history fetch failed: {result['error']}")

            finally:
                await connector.close()

        elif exchange_type == "binance":
            from infrastructure.exchanges.binance_connector import BinanceConnector
            connector = BinanceConnector(api_key=api_key, api_secret=api_secret, testnet=is_testnet)

            try:
                # Binance uses get_futures_income
                income_result = await connector.get_futures_income(
                    income_type="REALIZED_PNL",
                    start_time=start_time,
                    end_time=end_time,
                    limit=1000
                )

                if income_result.get("success"):
                    income_history = income_result.get("income", [])

                    total_pnl = 0.0
                    pnl_by_symbol = {}
                    pnl_by_date = {}
                    trades_list = []
                    wins = 0
                    losses = 0

                    # Sort by time first
                    sorted_income = sorted(income_history, key=lambda x: x.get("time", 0))

                    for idx, record in enumerate(sorted_income, 1):
                        symbol = record.get("symbol", "")
                        income_amount = float(record.get("income", 0))
                        timestamp = record.get("time", 0)

                        if symbols and symbol not in symbols:
                            continue

                        total_pnl += income_amount

                        # Count wins/losses
                        if income_amount > 0:
                            wins += 1
                            status = "WIN"
                        elif income_amount < 0:
                            losses += 1
                            status = "LOSS"
                        else:
                            status = "BREAK-EVEN"

                        # Build individual trade record
                        date_time_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S") if timestamp else "N/A"
                        trades_list.append({
                            "index": idx,
                            "datetime": date_time_str,
                            "symbol": symbol,
                            "pnl": round(income_amount, 2),
                            "status": status
                        })

                        if symbol not in pnl_by_symbol:
                            pnl_by_symbol[symbol] = 0.0
                        pnl_by_symbol[symbol] += income_amount

                        if timestamp:
                            date_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d")
                            if date_str not in pnl_by_date:
                                pnl_by_date[date_str] = {"pnl": 0.0, "count": 0}
                            pnl_by_date[date_str]["pnl"] += income_amount
                            pnl_by_date[date_str]["count"] += 1

                    pnl_history = []
                    cumulative = 0.0
                    for date_str in sorted(pnl_by_date.keys()):
                        daily_pnl = pnl_by_date[date_str]["pnl"]
                        cumulative += daily_pnl
                        pnl_history.append({
                            "date": date_str,
                            "daily_pnl": round(daily_pnl, 2),
                            "cumulative_pnl": round(cumulative, 2),
                            "trades_count": pnl_by_date[date_str]["count"]
                        })

                    result["success"] = True
                    result["total_pnl"] = round(total_pnl, 2)
                    result["pnl_by_symbol"] = {k: round(v, 2) for k, v in pnl_by_symbol.items()}
                    result["pnl_history"] = pnl_history
                    result["trades_list"] = trades_list
                    result["wins"] = wins
                    result["losses"] = losses

                    logger.info(f"Fetched P&L from Binance: total={total_pnl:.2f}, trades={len(trades_list)}, wins={wins}, losses={losses}")
                else:
                    result["error"] = income_result.get("error", "Failed to fetch income")

            finally:
                await connector.close()
        else:
            result["error"] = f"Unsupported exchange: {exchange_type}"

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Error fetching P&L from exchange: {e}")

    return result

# Initialize trade tracker service
trade_tracker = BotTradeTrackerService(transaction_db)

router = APIRouter(prefix="/api/v1/bot-subscriptions", tags=["bot-subscriptions"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ExchangeConfig(BaseModel):
    """Configuration per exchange (used when use_same_config=False)"""
    exchange_account_id: str = Field(..., description="UUID of exchange account")
    custom_leverage: Optional[int] = Field(None, ge=1, le=125)
    custom_margin_usd: Optional[float] = Field(None, ge=5.00)
    custom_stop_loss_pct: Optional[float] = Field(None, ge=0.1, le=50.0)
    custom_take_profit_pct: Optional[float] = Field(None, ge=0.1, le=100.0)
    max_daily_loss_usd: float = Field(default=200.00, ge=10.00)
    max_concurrent_positions: int = Field(default=3, ge=1, le=10)


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


class MultiExchangeSubscriptionCreate(BaseModel):
    """Model for creating bot subscriptions with multiple exchanges (max 3)"""
    bot_id: str = Field(..., description="UUID of the bot to subscribe to")
    exchange_account_ids: List[str] = Field(..., min_length=1, max_length=3, description="List of exchange account UUIDs (max 3)")
    use_same_config: bool = Field(default=True, description="If True, same config for all exchanges")
    # Shared config (when use_same_config=True)
    custom_leverage: Optional[int] = Field(None, ge=1, le=125)
    custom_margin_usd: Optional[float] = Field(None, ge=5.00)
    custom_stop_loss_pct: Optional[float] = Field(None, ge=0.1, le=50.0)
    custom_take_profit_pct: Optional[float] = Field(None, ge=0.1, le=100.0)
    max_daily_loss_usd: float = Field(default=200.00, ge=10.00)
    max_concurrent_positions: int = Field(default=3, ge=1, le=10)
    # Individual configs (when use_same_config=False)
    individual_configs: Optional[List[ExchangeConfig]] = Field(None, description="Individual config per exchange")


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
    """Get all bot subscriptions for current user (includes multi-exchange support)"""
    try:
        subscriptions = await transaction_db.fetch("""
            SELECT
                bs.id,
                bs.exchange_account_id,
                bs.config_group_id,
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
            WHERE bs.user_id = $1 AND bs.status != 'cancelled'
            ORDER BY b.name, bs.created_at DESC
        """, user_id)

        # Group subscriptions by bot_id for multi-exchange support
        # This allows the frontend to see all exchanges for each bot
        bots_map = {}
        for sub in subscriptions:
            sub_dict = dict(sub)
            bot_id = str(sub_dict["bot_id"])

            if bot_id not in bots_map:
                bots_map[bot_id] = {
                    "bot_id": bot_id,
                    "bot_name": sub_dict["bot_name"],
                    "bot_description": sub_dict["bot_description"],
                    "market_type": sub_dict["market_type"],
                    "default_leverage": sub_dict["default_leverage"],
                    "default_margin_usd": float(sub_dict["default_margin_usd"]) if sub_dict["default_margin_usd"] else None,
                    "default_stop_loss_pct": float(sub_dict["default_stop_loss_pct"]) if sub_dict["default_stop_loss_pct"] else None,
                    "default_take_profit_pct": float(sub_dict["default_take_profit_pct"]) if sub_dict["default_take_profit_pct"] else None,
                    "exchanges": [],
                    "total_pnl_usd": 0.0,
                    "total_win_count": 0,
                    "total_loss_count": 0,
                    "total_signals_received": 0,
                    "total_orders_executed": 0
                }

            # Add exchange-specific subscription data
            bots_map[bot_id]["exchanges"].append({
                "subscription_id": str(sub_dict["id"]),
                "exchange_account_id": str(sub_dict["exchange_account_id"]),
                "exchange": sub_dict["exchange"],
                "account_name": sub_dict["account_name"],
                "status": sub_dict["status"],
                "config_group_id": str(sub_dict["config_group_id"]) if sub_dict["config_group_id"] else None,
                "custom_leverage": sub_dict["custom_leverage"],
                "custom_margin_usd": float(sub_dict["custom_margin_usd"]) if sub_dict["custom_margin_usd"] else None,
                "custom_stop_loss_pct": float(sub_dict["custom_stop_loss_pct"]) if sub_dict["custom_stop_loss_pct"] else None,
                "custom_take_profit_pct": float(sub_dict["custom_take_profit_pct"]) if sub_dict["custom_take_profit_pct"] else None,
                "max_daily_loss_usd": float(sub_dict["max_daily_loss_usd"]) if sub_dict["max_daily_loss_usd"] else None,
                "max_concurrent_positions": sub_dict["max_concurrent_positions"],
                "current_daily_loss_usd": float(sub_dict["current_daily_loss_usd"]) if sub_dict["current_daily_loss_usd"] else 0,
                "current_positions": sub_dict["current_positions"] or 0,
                "total_signals_received": sub_dict["total_signals_received"] or 0,
                "total_orders_executed": sub_dict["total_orders_executed"] or 0,
                "total_orders_failed": sub_dict["total_orders_failed"] or 0,
                "total_pnl_usd": float(sub_dict["total_pnl_usd"]) if sub_dict["total_pnl_usd"] else 0,
                "win_count": sub_dict["win_count"] or 0,
                "loss_count": sub_dict["loss_count"] or 0,
                "created_at": sub_dict["created_at"].isoformat() if sub_dict["created_at"] else None,
                "last_signal_at": sub_dict["last_signal_at"].isoformat() if sub_dict["last_signal_at"] else None
            })

            # Aggregate totals
            bots_map[bot_id]["total_pnl_usd"] += float(sub_dict["total_pnl_usd"]) if sub_dict["total_pnl_usd"] else 0
            bots_map[bot_id]["total_win_count"] += sub_dict["win_count"] or 0
            bots_map[bot_id]["total_loss_count"] += sub_dict["loss_count"] or 0
            bots_map[bot_id]["total_signals_received"] += sub_dict["total_signals_received"] or 0
            bots_map[bot_id]["total_orders_executed"] += sub_dict["total_orders_executed"] or 0

        # Convert to list and add computed fields
        grouped_data = []
        for bot_data in bots_map.values():
            bot_data["exchanges_count"] = len(bot_data["exchanges"])
            # Use first subscription's status as "overall" status (active if any active)
            bot_data["status"] = "active" if any(e["status"] == "active" for e in bot_data["exchanges"]) else "paused"
            # For backwards compatibility, use first subscription's id if only one exchange
            if len(bot_data["exchanges"]) == 1:
                bot_data["id"] = bot_data["exchanges"][0]["subscription_id"]
                bot_data["exchange"] = bot_data["exchanges"][0]["exchange"]
                bot_data["account_name"] = bot_data["exchanges"][0]["account_name"]
            grouped_data.append(bot_data)

        return {
            "success": True,
            "data": grouped_data,
            "raw_subscriptions": [dict(sub) for sub in subscriptions]  # Keep raw data for backwards compat
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

        # Check if subscription already exists FOR THIS EXCHANGE (multi-exchange support)
        existing = await transaction_db.fetchval("""
            SELECT id
            FROM bot_subscriptions
            WHERE user_id = $1 AND bot_id = $2 AND exchange_account_id = $3
        """, user_id, subscription_data.bot_id, subscription_data.exchange_account_id)

        if existing:
            raise HTTPException(
                status_code=400,
                detail="You are already subscribed to this bot with this exchange account"
            )

        # Check max 3 exchanges per bot limit
        exchange_count = await transaction_db.fetchval("""
            SELECT COUNT(*)
            FROM bot_subscriptions
            WHERE user_id = $1 AND bot_id = $2
        """, user_id, subscription_data.bot_id)

        if exchange_count >= 3:
            raise HTTPException(
                status_code=400,
                detail="Maximum 3 exchange accounts per bot allowed"
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


@router.post("/multi")
async def subscribe_to_bot_multi_exchange(
    subscription_data: MultiExchangeSubscriptionCreate,
    user_id: str = Query(..., description="User ID subscribing to the bot")
):
    """
    Subscribe to a bot with multiple exchange accounts (max 3)
    Creates subscriptions for each exchange, linked by config_group_id
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

        # Validate individual_configs if use_same_config=False
        if not subscription_data.use_same_config:
            if not subscription_data.individual_configs:
                raise HTTPException(
                    status_code=400,
                    detail="individual_configs required when use_same_config=False"
                )
            config_exchange_ids = {c.exchange_account_id for c in subscription_data.individual_configs}
            if config_exchange_ids != set(subscription_data.exchange_account_ids):
                raise HTTPException(
                    status_code=400,
                    detail="individual_configs must match exchange_account_ids"
                )

        # Count existing ACTIVE/PAUSED subscriptions for this bot
        existing_active_count = await transaction_db.fetchval("""
            SELECT COUNT(*)
            FROM bot_subscriptions
            WHERE user_id = $1 AND bot_id = $2
            AND status IN ('active', 'paused')
        """, user_id, subscription_data.bot_id)

        # Count how many of the requested exchanges already have active/paused subscriptions
        already_active = await transaction_db.fetchval("""
            SELECT COUNT(*)
            FROM bot_subscriptions
            WHERE user_id = $1 AND bot_id = $2 AND status IN ('active', 'paused')
            AND exchange_account_id = ANY($3::uuid[])
        """, user_id, subscription_data.bot_id, subscription_data.exchange_account_ids)

        # Count how many cancelled subscriptions can be reactivated
        cancelled_to_reactivate = await transaction_db.fetchval("""
            SELECT COUNT(*)
            FROM bot_subscriptions
            WHERE user_id = $1 AND bot_id = $2 AND status = 'cancelled'
            AND exchange_account_id = ANY($3::uuid[])
        """, user_id, subscription_data.bot_id, subscription_data.exchange_account_ids)

        # Truly new subscriptions = requested - already_active - cancelled_to_reactivate
        new_subscriptions_needed = len(subscription_data.exchange_account_ids) - already_active - cancelled_to_reactivate

        # Final count = existing + new
        final_count = existing_active_count + new_subscriptions_needed

        if final_count > 3:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum 3 exchange accounts per bot. Final count would be {final_count}"
            )

        # Verify all exchange accounts exist and belong to user
        for exchange_id in subscription_data.exchange_account_ids:
            exchange_account = await transaction_db.fetchrow("""
                SELECT id, exchange, is_active
                FROM exchange_accounts
                WHERE id = $1 AND user_id = $2
            """, exchange_id, user_id)

            if not exchange_account:
                raise HTTPException(
                    status_code=404,
                    detail=f"Exchange account {exchange_id} not found or doesn't belong to you"
                )

            if not exchange_account["is_active"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exchange account {exchange_id} is not active"
                )

            # NOTE: If already subscribed with this exchange (active/paused),
            # we will update its config_group_id to join this multi-exchange group

        # Generate config_group_id to link all subscriptions
        config_group_id = str(uuid4())

        # Create or reactivate subscriptions for each exchange
        created_ids = []
        for exchange_id in subscription_data.exchange_account_ids:
            # Get config for this exchange
            if subscription_data.use_same_config:
                leverage = subscription_data.custom_leverage
                margin = subscription_data.custom_margin_usd
                stop_loss = subscription_data.custom_stop_loss_pct
                take_profit = subscription_data.custom_take_profit_pct
                max_loss = subscription_data.max_daily_loss_usd
                max_positions = subscription_data.max_concurrent_positions
            else:
                config = next(c for c in subscription_data.individual_configs if c.exchange_account_id == exchange_id)
                leverage = config.custom_leverage
                margin = config.custom_margin_usd
                stop_loss = config.custom_stop_loss_pct
                take_profit = config.custom_take_profit_pct
                max_loss = config.max_daily_loss_usd
                max_positions = config.max_concurrent_positions

            # Check if there's already an active/paused subscription
            existing_active = await transaction_db.fetchrow("""
                SELECT id FROM bot_subscriptions
                WHERE user_id = $1 AND bot_id = $2 AND exchange_account_id = $3
                AND status IN ('active', 'paused')
            """, user_id, subscription_data.bot_id, exchange_id)

            if existing_active:
                # Update existing subscription to join this multi-exchange group
                subscription_id = await transaction_db.fetchval("""
                    UPDATE bot_subscriptions
                    SET config_group_id = $1,
                        custom_leverage = COALESCE($2, custom_leverage),
                        custom_margin_usd = COALESCE($3, custom_margin_usd),
                        custom_stop_loss_pct = COALESCE($4, custom_stop_loss_pct),
                        custom_take_profit_pct = COALESCE($5, custom_take_profit_pct),
                        max_daily_loss_usd = $6,
                        max_concurrent_positions = $7,
                        updated_at = NOW()
                    WHERE id = $8
                    RETURNING id
                """,
                    config_group_id,
                    leverage,
                    margin,
                    stop_loss,
                    take_profit,
                    max_loss,
                    max_positions,
                    existing_active["id"]
                )
                logger.info(f"Updated existing subscription {subscription_id} to join group {config_group_id}")
                created_ids.append(str(subscription_id))
                continue

            # Check if there's a cancelled subscription to reactivate
            existing_cancelled = await transaction_db.fetchrow("""
                SELECT id FROM bot_subscriptions
                WHERE user_id = $1 AND bot_id = $2 AND exchange_account_id = $3
                AND status = 'cancelled'
            """, user_id, subscription_data.bot_id, exchange_id)

            if existing_cancelled:
                # Reactivate the cancelled subscription with new config
                subscription_id = await transaction_db.fetchval("""
                    UPDATE bot_subscriptions
                    SET status = 'active',
                        custom_leverage = $1,
                        custom_margin_usd = $2,
                        custom_stop_loss_pct = $3,
                        custom_take_profit_pct = $4,
                        max_daily_loss_usd = $5,
                        max_concurrent_positions = $6,
                        config_group_id = $7,
                        updated_at = NOW()
                    WHERE id = $8
                    RETURNING id
                """,
                    leverage,
                    margin,
                    stop_loss,
                    take_profit,
                    max_loss,
                    max_positions,
                    config_group_id,
                    existing_cancelled["id"]
                )
                logger.info(f"Reactivated cancelled subscription {subscription_id}")
            else:
                # Create new subscription
                subscription_id = await transaction_db.fetchval("""
                    INSERT INTO bot_subscriptions (
                        user_id, bot_id, exchange_account_id, status,
                        custom_leverage, custom_margin_usd,
                        custom_stop_loss_pct, custom_take_profit_pct,
                        max_daily_loss_usd, max_concurrent_positions,
                        config_group_id
                    ) VALUES ($1, $2, $3, 'active', $4, $5, $6, $7, $8, $9, $10)
                    RETURNING id
                """,
                    user_id,
                    subscription_data.bot_id,
                    exchange_id,
                    leverage,
                    margin,
                    stop_loss,
                    take_profit,
                    max_loss,
                    max_positions,
                    config_group_id
                )
            created_ids.append(str(subscription_id))

        # Update bot subscriber count (count unique users, not subscriptions)
        await transaction_db.execute("""
            UPDATE bots
            SET total_subscribers = (
                SELECT COUNT(DISTINCT user_id)
                FROM bot_subscriptions
                WHERE bot_id = $1 AND status != 'cancelled'
            ),
            updated_at = NOW()
            WHERE id = $1
        """, subscription_data.bot_id)

        logger.info(
            "Multi-exchange bot subscriptions created",
            user_id=user_id,
            bot_id=subscription_data.bot_id,
            subscription_ids=created_ids,
            config_group_id=config_group_id
        )

        return {
            "success": True,
            "data": {
                "subscription_ids": created_ids,
                "config_group_id": config_group_id,
                "exchanges_count": len(created_ids)
            },
            "message": f"Successfully subscribed to {bot['name']} with {len(created_ids)} exchange(s)"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating multi-exchange subscription", user_id=user_id, error=str(e), exc_info=True)
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

    P&L Source Priority:
    1. Try to fetch from exchange API (BingX/Binance) - most accurate
    2. Fallback to database (bot_trades table) if exchange fails
    """
    try:
        # Verify subscription exists and belongs to user - include exchange account info
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
                bs.max_daily_loss_usd,
                bs.created_at,
                b.name as bot_name,
                b.trading_symbol as bot_trading_symbol,
                ea.id as exchange_account_id,
                ea.exchange as exchange_type,
                ea.api_key,
                ea.secret_key,
                ea.testnet
            FROM bot_subscriptions bs
            INNER JOIN bots b ON b.id = bs.bot_id
            INNER JOIN exchange_accounts ea ON ea.id = bs.exchange_account_id
            WHERE bs.id = $1 AND bs.user_id = $2
        """, subscription_id, user_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_timestamp = int(start_date.timestamp() * 1000)
        end_timestamp = int(end_date.timestamp() * 1000)

        # =====================================================
        # Get bot's traded symbol - FROM DATABASE or FALLBACK TO NAME
        # Priority: 1) b.trading_symbol from DB, 2) Extract from bot name
        # =====================================================
        bot_symbols = []
        bot_name = subscription["bot_name"]
        trading_symbol = subscription.get("bot_trading_symbol")

        if trading_symbol:
            # Use symbol from database (configured in admin)
            bot_symbols = [trading_symbol.upper()]
            logger.info(f"Using trading_symbol '{trading_symbol}' from bot config for '{bot_name}'")
        else:
            # Fallback: Extract from bot name (legacy support)
            import re as regex_module
            match = regex_module.search(r'TPO[_\s]+([A-Z]{2,10})(?:[_\s]|$)', bot_name.upper())
            if match:
                symbol_base = match.group(1)
                bot_symbols = [f"{symbol_base}USDT"]
                logger.info(f"Extracted symbol '{symbol_base}USDT' from bot name '{bot_name}' (no trading_symbol configured)")
            else:
                logger.warning(f"No trading_symbol configured and couldn't extract from bot name '{bot_name}' - P&L will be unfiltered!")

        # =====================================================
        # TRY EXCHANGE P&L FIRST (Primary Source)
        # =====================================================
        exchange_pnl_result = None
        pnl_source = "database"  # Track where P&L came from

        try:
            exchange_type = subscription["exchange_type"].lower() if subscription["exchange_type"] else None
            api_key = subscription["api_key"]
            api_secret = subscription["secret_key"]
            is_testnet = subscription["testnet"] or False

            if exchange_type and api_key and api_secret:
                logger.info(f"Fetching P&L from {exchange_type} for symbols: {bot_symbols}")

                exchange_pnl_result = await fetch_pnl_from_exchange(
                    exchange_type=exchange_type,
                    api_key=api_key,
                    api_secret=api_secret,
                    is_testnet=is_testnet,
                    symbols=bot_symbols,
                    start_time=start_timestamp,
                    end_time=end_timestamp
                )

                if exchange_pnl_result.get("success"):
                    pnl_source = "exchange"
                    logger.info(f"Successfully fetched P&L from exchange: {exchange_pnl_result['total_pnl']}")
                else:
                    logger.warning(f"Exchange P&L fetch failed, using database fallback: {exchange_pnl_result.get('error')}")
        except Exception as e:
            logger.warning(f"Error fetching P&L from exchange, using database fallback: {e}")

        # =====================================================
        # FILTERED STATISTICS - Based on date range (days)
        # =====================================================

        # Get filtered signals count from bot_signal_executions
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

        # Get from bot_trades (DATABASE FALLBACK source)
        # Apply symbol filter if bot_symbols is set
        if bot_symbols:
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
                    AND (symbol = ANY($3) OR REPLACE(REPLACE(symbol, '-', ''), 'USDT', '') || 'USDT' = ANY($3))
            """, subscription_id, start_date, bot_symbols)
        else:
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
        # Apply symbol filter if bot_symbols is set
        if bot_symbols:
            all_trades_count = await transaction_db.fetchrow("""
                SELECT
                    COUNT(*) as total_all_trades,
                    COUNT(*) FILTER (WHERE status = 'open') as open_trades,
                    COUNT(*) FILTER (WHERE status = 'closed') as closed_trades
                FROM bot_trades
                WHERE subscription_id = $1
                    AND entry_time >= $2
                    AND (symbol = ANY($3) OR REPLACE(REPLACE(symbol, '-', ''), 'USDT', '') || 'USDT' = ANY($3))
            """, subscription_id, start_date, bot_symbols)
        else:
            all_trades_count = await transaction_db.fetchrow("""
                SELECT
                    COUNT(*) as total_all_trades,
                    COUNT(*) FILTER (WHERE status = 'open') as open_trades,
                    COUNT(*) FILTER (WHERE status = 'closed') as closed_trades
                FROM bot_trades
                WHERE subscription_id = $1
                    AND entry_time >= $2
            """, subscription_id, start_date)

        # Calculate filtered statistics
        filtered_signals_count = filtered_signals["signals_count"] or 0 if filtered_signals else 0
        filtered_executed_count = filtered_signals["executed_count"] or 0 if filtered_signals else 0
        total_executions = filtered_signals["total_executions"] or 0 if filtered_signals else 0

        # Use database trades data for win/loss counts
        bot_trades_count = all_trades_count["total_all_trades"] or 0 if all_trades_count else 0
        use_executions_as_trades = bot_trades_count == 0

        if use_executions_as_trades:
            filtered_total_trades = filtered_executed_count
            filtered_wins = subscription["win_count"] or 0
            filtered_losses = subscription["loss_count"] or 0
            filtered_closed_trades = filtered_wins + filtered_losses
            open_trades_count = 0
        else:
            filtered_wins = filtered_trades["wins"] or 0 if filtered_trades else 0
            filtered_losses = filtered_trades["losses"] or 0 if filtered_trades else 0
            filtered_closed_trades = filtered_wins + filtered_losses
            filtered_total_trades = all_trades_count["total_all_trades"] or 0 if all_trades_count else 0
            open_trades_count = all_trades_count["open_trades"] or 0 if all_trades_count else 0

        # Win rate calculation
        filtered_win_rate = (filtered_wins / filtered_closed_trades * 100) if filtered_closed_trades > 0 else 0

        # =====================================================
        # P&L VALUE - Exchange (primary) or Database (fallback)
        # =====================================================
        trades_list = []  # Individual trades from exchange

        if pnl_source == "exchange" and exchange_pnl_result:
            filtered_pnl = exchange_pnl_result["total_pnl"]
            pnl_by_symbol = exchange_pnl_result.get("pnl_by_symbol", {})
            trades_list = exchange_pnl_result.get("trades_list", [])
            # Override wins/losses with exchange data
            filtered_wins = exchange_pnl_result.get("wins", filtered_wins)
            filtered_losses = exchange_pnl_result.get("losses", filtered_losses)
            filtered_total_trades = len(trades_list)
            filtered_closed_trades = filtered_wins + filtered_losses
            filtered_win_rate = (filtered_wins / filtered_closed_trades * 100) if filtered_closed_trades > 0 else 0
            logger.info(f"Using EXCHANGE P&L: {filtered_pnl}, trades={len(trades_list)}, wins={filtered_wins}, losses={filtered_losses}")
        else:
            # Database fallback
            if use_executions_as_trades:
                filtered_pnl = float(subscription["total_pnl_usd"] or 0)
            else:
                filtered_pnl = float(filtered_trades["total_pnl"] or 0) if filtered_trades else 0
            pnl_by_symbol = {}
            logger.info(f"Using DATABASE P&L (fallback): {filtered_pnl}")

        # =====================================================
        # P&L HISTORY - Exchange (primary) or Database (fallback)
        # =====================================================
        pnl_history = []

        # If exchange P&L was successful, use that history
        if pnl_source == "exchange" and exchange_pnl_result and exchange_pnl_result.get("pnl_history"):
            pnl_history = exchange_pnl_result["pnl_history"]
            logger.info(f"Using EXCHANGE P&L history: {len(pnl_history)} days")
        else:
            # Fallback: Try to get P&L history from bot_pnl_history table
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
                logger.warning(f"Could not fetch P&L history from bot_pnl_history: {e}")

            # If no history data, build from actual bot_trades table
            if not pnl_history:
                try:
                    # Get closed trades grouped by date with REAL P&L values
                    # Apply symbol filter if bot_symbols is set
                    if bot_symbols:
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
                                AND (symbol = ANY($3) OR REPLACE(REPLACE(symbol, '-', ''), 'USDT', '') || 'USDT' = ANY($3))
                            GROUP BY DATE(exit_time)
                            ORDER BY trade_date ASC
                        """, subscription_id, start_date, bot_symbols)
                    else:
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

                    logger.info(f"Built P&L history from {len(pnl_history)} days of bot_trades (database fallback)")

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

        # =====================================================
        # CALCULATE TODAY'S LOSS from pnl_history (exchange data)
        # Force reload: v2
        # =====================================================
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_loss_usd = 0.0

        # Find today's P&L from the history
        for day_record in pnl_history:
            if day_record.get("date") == today_str:
                daily_pnl = day_record.get("daily_pnl", 0)
                # today_loss_usd will be positive if there was a loss (negative P&L)
                if daily_pnl < 0:
                    today_loss_usd = abs(daily_pnl)
                break

        return {
            "success": True,
            "data": {
                "subscription_id": subscription_id,
                "bot_name": subscription["bot_name"],
                "days_filter": days,
                # P&L data source info
                "pnl_source": pnl_source,  # "exchange" or "database"
                "pnl_by_symbol": pnl_by_symbol,  # P&L breakdown by symbol (if from exchange)
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
                    "positions_data": realtime_positions_data,  # Detailed position info
                    "today_loss_usd": round(today_loss_usd, 2),  # Today's loss from exchange
                    "max_daily_loss_usd": float(subscription.get("max_daily_loss_usd") or 200)  # Max daily loss limit
                },
                "pnl_history": pnl_history,
                # Individual trades list from exchange (for history table)
                "trades_list": trades_list
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
