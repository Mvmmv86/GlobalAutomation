"""
Admin Controller
Handles admin-specific operations like dashboard stats, user management, and bot management
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
import structlog

from infrastructure.database.connection_transaction_mode import transaction_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ============================================================================
# Pydantic Models
# ============================================================================

class BotCreate(BaseModel):
    """Model for creating a new bot"""
    name: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10, max_length=1000)
    market_type: str = Field(default="futures", pattern="^(spot|futures)$")
    trading_symbol: Optional[str] = Field(
        None,
        max_length=20,
        description="Trading pair for P&L filtering (e.g., BNBUSDT, ETHUSDT). Required for accurate P&L tracking."
    )
    allowed_directions: str = Field(
        default="both",
        pattern="^(buy_only|sell_only|both)$",
        description="Which directions are allowed: buy_only (Long), sell_only (Short), both (Long+Short)"
    )
    master_webhook_path: str = Field(..., min_length=16, max_length=255,
                                     description="Unique secret path for webhook (min 16 chars for security)")
    default_leverage: int = Field(default=10, ge=1, le=125)
    default_margin_usd: float = Field(default=50.00, ge=5.00)
    default_stop_loss_pct: float = Field(default=2.5, ge=0.1, le=50.0)
    default_take_profit_pct: float = Field(default=5.0, ge=0.1, le=100.0)
    default_max_positions: int = Field(
        default=3, ge=1, le=20,
        description="Número máximo de posições simultâneas sugerido. Clientes podem sobrescrever."
    )


class BotUpdate(BaseModel):
    """Model for updating bot configuration"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=10, max_length=1000)
    status: Optional[str] = Field(None, pattern="^(active|paused|archived)$")
    trading_symbol: Optional[str] = Field(
        None,
        max_length=20,
        description="Trading pair for P&L filtering (e.g., BNBUSDT, ETHUSDT)"
    )
    default_leverage: Optional[int] = Field(None, ge=1, le=125)
    default_margin_usd: Optional[float] = Field(None, ge=5.00)
    default_stop_loss_pct: Optional[float] = Field(None, ge=0.1, le=50.0)
    default_take_profit_pct: Optional[float] = Field(None, ge=0.1, le=100.0)
    default_max_positions: Optional[int] = Field(None, ge=1, le=20)


# ============================================================================
# Middleware - Admin Authentication
# ============================================================================

async def verify_admin(request: Request):
    """Verify that the user is an admin"""
    import os
    user_id = request.query_params.get('admin_user_id')

    if not user_id:
        raise HTTPException(status_code=401, detail="Admin authentication required")

    # Check if user is admin - first try admins table, then fallback to users.is_admin
    is_admin = await transaction_db.fetchval("""
        SELECT EXISTS(
            SELECT 1 FROM admins a
            INNER JOIN users u ON u.id = a.user_id
            WHERE a.user_id = $1 AND a.is_active = true AND u.is_admin = true
        )
    """, user_id)

    # Fallback: Check if user has is_admin flag in users table (simpler check)
    if not is_admin:
        is_admin = await transaction_db.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM users WHERE id = $1 AND is_admin = true
            )
        """, user_id)

    # DEV ONLY: Allow any authenticated user in development
    env = os.environ.get('ENV', 'dev').lower()
    if not is_admin and env in ('dev', 'development'):
        # Check if user exists at all
        user_exists = await transaction_db.fetchval("""
            SELECT EXISTS(SELECT 1 FROM users WHERE id = $1)
        """, user_id)
        if user_exists:
            logger.warning("DEV MODE: Allowing non-admin user for admin endpoint", user_id=user_id)
            is_admin = True

    if not is_admin:
        logger.warning("Admin access denied", user_id=user_id)
        raise HTTPException(status_code=403, detail="Admin access required")

    return user_id


# ============================================================================
# DASHBOARD STATS
# ============================================================================

@router.get("/dashboard/stats")
async def get_dashboard_stats(admin_user_id: str = Depends(verify_admin)):
    """
    Get comprehensive dashboard statistics for admin
    Returns: total users, bots, webhooks, subscriptions, volume, etc.
    """
    try:
        # Total Users
        total_users = await transaction_db.fetchval("SELECT COUNT(*) FROM users WHERE is_admin = false")

        # Total Exchanges Integrated
        total_exchanges = await transaction_db.fetchval("SELECT COUNT(DISTINCT exchange) FROM exchange_accounts")

        # Total Bots Created
        total_bots = await transaction_db.fetchval("SELECT COUNT(*) FROM bots")
        active_bots = await transaction_db.fetchval("SELECT COUNT(*) FROM bots WHERE status = 'active'")

        # Total Webhooks
        total_webhooks = await transaction_db.fetchval("SELECT COUNT(*) FROM webhooks")
        active_webhooks = await transaction_db.fetchval("SELECT COUNT(*) FROM webhooks WHERE status = 'active'")

        # Total Bot Subscriptions
        total_subscriptions = await transaction_db.fetchval("SELECT COUNT(*) FROM bot_subscriptions")
        active_subscriptions = await transaction_db.fetchval(
            "SELECT COUNT(*) FROM bot_subscriptions WHERE status = 'active'"
        )

        # Total Signals Sent
        total_signals = await transaction_db.fetchval("SELECT COUNT(*) FROM bot_signals")

        # Total Orders Executed (via bot subscriptions)
        total_orders = await transaction_db.fetchval(
            "SELECT COALESCE(SUM(total_orders_executed), 0) FROM bot_subscriptions"
        )

        # Total P&L
        total_pnl = await transaction_db.fetchval(
            "SELECT COALESCE(SUM(total_pnl_usd), 0) FROM bot_subscriptions"
        )

        # Recent Activity (last 7 days)
        new_users_7d = await transaction_db.fetchval("""
            SELECT COUNT(*) FROM users
            WHERE created_at >= NOW() - INTERVAL '7 days' AND is_admin = false
        """)

        new_subscriptions_7d = await transaction_db.fetchval("""
            SELECT COUNT(*) FROM bot_subscriptions
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)

        signals_7d = await transaction_db.fetchval("""
            SELECT COUNT(*) FROM bot_signals
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)

        # Top Performing Bots
        top_bots = await transaction_db.fetch("""
            SELECT
                b.id,
                b.name,
                b.total_subscribers,
                b.total_signals_sent,
                b.avg_win_rate,
                b.avg_pnl_pct
            FROM bots b
            WHERE b.status = 'active'
            ORDER BY b.total_subscribers DESC
            LIMIT 5
        """)

        return {
            "success": True,
            "data": {
                "overview": {
                    "total_users": total_users,
                    "total_exchanges": total_exchanges,
                    "total_bots": total_bots,
                    "active_bots": active_bots,
                    "total_webhooks": total_webhooks,
                    "active_webhooks": active_webhooks,
                    "total_subscriptions": total_subscriptions,
                    "active_subscriptions": active_subscriptions,
                    "total_signals_sent": total_signals,
                    "total_orders_executed": total_orders,
                    "total_pnl_usd": float(total_pnl) if total_pnl else 0
                },
                "recent_activity": {
                    "new_users_7d": new_users_7d,
                    "new_subscriptions_7d": new_subscriptions_7d,
                    "signals_sent_7d": signals_7d
                },
                "top_bots": [dict(bot) for bot in top_bots]
            }
        }

    except Exception as e:
        logger.error("Error getting admin dashboard stats", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@router.get("/users")
async def get_all_users(
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    admin_user_id: str = Depends(verify_admin)
):
    """Get all users with pagination and search"""
    try:
        where_clause = "WHERE u.is_admin = false"
        params = []
        param_idx = 1

        if search:
            where_clause += f" AND (u.email ILIKE ${param_idx} OR u.name ILIKE ${param_idx})"
            params.append(f"%{search}%")
            param_idx += 1

        # Get total count
        count_query = f"SELECT COUNT(*) FROM users u {where_clause}"
        total = await transaction_db.fetchval(count_query, *params)

        # Get users with stats
        params.extend([limit, offset])
        users = await transaction_db.fetch(f"""
            SELECT
                u.id,
                u.email,
                u.name,
                u.created_at,
                u.last_login,
                COUNT(DISTINCT ea.id) as total_exchanges,
                COUNT(DISTINCT bs.id) as total_subscriptions,
                COUNT(DISTINCT w.id) as total_webhooks
            FROM users u
            LEFT JOIN exchange_accounts ea ON ea.user_id = u.id
            LEFT JOIN bot_subscriptions bs ON bs.user_id = u.id
            LEFT JOIN webhooks w ON w.user_id = u.id
            {where_clause}
            GROUP BY u.id, u.email, u.name, u.created_at, u.last_login
            ORDER BY u.created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """, *params)

        return {
            "success": True,
            "data": {
                "users": [dict(user) for user in users],
                "total": total,
                "limit": limit,
                "offset": offset
            }
        }

    except Exception as e:
        logger.error("Error getting users", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    admin_user_id: str = Depends(verify_admin)
):
    """Get detailed information about a specific user"""
    try:
        user = await transaction_db.fetchrow("""
            SELECT
                u.id,
                u.email,
                u.name,
                u.created_at,
                u.last_login,
                u.is_admin
            FROM users u
            WHERE u.id = $1
        """, user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's exchanges
        exchanges = await transaction_db.fetch("""
            SELECT id, name, exchange, status, created_at
            FROM exchange_accounts
            WHERE user_id = $1
            ORDER BY created_at DESC
        """, user_id)

        # Get user's subscriptions
        subscriptions = await transaction_db.fetch("""
            SELECT
                bs.id,
                bs.status,
                bs.created_at,
                b.name as bot_name,
                bs.total_signals_received,
                bs.total_pnl_usd
            FROM bot_subscriptions bs
            INNER JOIN bots b ON b.id = bs.bot_id
            WHERE bs.user_id = $1
            ORDER BY bs.created_at DESC
        """, user_id)

        # Get user's webhooks
        webhooks = await transaction_db.fetch("""
            SELECT id, name, status, total_deliveries, created_at
            FROM webhooks
            WHERE user_id = $1
            ORDER BY created_at DESC
        """, user_id)

        return {
            "success": True,
            "data": {
                **dict(user),
                "exchanges": [dict(e) for e in exchanges],
                "subscriptions": [dict(s) for s in subscriptions],
                "webhooks": [dict(w) for w in webhooks]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting user details", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BOTS MANAGEMENT (CRUD)
# ============================================================================

@router.get("/bots")
async def get_all_bots(
    status: Optional[str] = None,
    admin_user_id: str = Depends(verify_admin)
):
    """Get all bots (admin view - includes all statuses)"""
    try:
        where_clause = ""
        params = []

        if status:
            where_clause = "WHERE status = $1"
            params.append(status)

        bots = await transaction_db.fetch(f"""
            SELECT
                id, name, description, market_type, status,
                trading_symbol, master_webhook_path,
                default_leverage, default_margin_usd,
                default_stop_loss_pct, default_take_profit_pct,
                default_max_positions,
                total_subscribers, total_signals_sent,
                avg_win_rate, avg_pnl_pct,
                created_at, updated_at
            FROM bots
            {where_clause}
            ORDER BY created_at DESC
        """, *params)

        return {
            "success": True,
            "data": [dict(bot) for bot in bots]
        }

    except Exception as e:
        logger.error("Error getting bots", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bots")
async def create_bot(
    bot_data: BotCreate,
    admin_user_id: str = Depends(verify_admin)
):
    """Create a new bot"""
    try:
        # Check if webhook path already exists
        existing = await transaction_db.fetchval("""
            SELECT id FROM bots WHERE master_webhook_path = $1
        """, bot_data.master_webhook_path)

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Webhook path already in use"
            )

        # Create bot
        bot_id = await transaction_db.fetchval("""
            INSERT INTO bots (
                name, description, market_type, status,
                trading_symbol, allowed_directions, master_webhook_path,
                default_leverage, default_margin_usd,
                default_stop_loss_pct, default_take_profit_pct, default_max_positions
            ) VALUES ($1, $2, $3, 'active', $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id
        """,
            bot_data.name,
            bot_data.description,
            bot_data.market_type,
            bot_data.trading_symbol.upper() if bot_data.trading_symbol else None,
            bot_data.allowed_directions,
            bot_data.master_webhook_path,
            bot_data.default_leverage,
            bot_data.default_margin_usd,
            bot_data.default_stop_loss_pct,
            bot_data.default_take_profit_pct,
            bot_data.default_max_positions
        )

        # Log admin activity
        await transaction_db.execute("""
            INSERT INTO admin_activity_log (admin_id, action, entity_type, entity_id, details)
            SELECT a.id, 'created_bot', 'bot', $2, $3::jsonb
            FROM admins a WHERE a.user_id = $1
        """, admin_user_id, str(bot_id), f'{{"bot_name": "{bot_data.name}"}}')

        logger.info("Bot created", bot_id=str(bot_id), admin_user_id=admin_user_id)

        return {
            "success": True,
            "data": {"bot_id": str(bot_id)},
            "message": f"Bot '{bot_data.name}' created successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating bot", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/bots/{bot_id}")
async def update_bot(
    bot_id: str,
    bot_data: BotUpdate,
    admin_user_id: str = Depends(verify_admin)
):
    """Update bot configuration"""
    try:
        # Verify bot exists
        existing = await transaction_db.fetchrow("""
            SELECT id, name FROM bots WHERE id = $1
        """, bot_id)

        if not existing:
            raise HTTPException(status_code=404, detail="Bot not found")

        # Build dynamic update query
        updates = []
        params = []
        param_idx = 1

        if bot_data.name is not None:
            updates.append(f"name = ${param_idx}")
            params.append(bot_data.name)
            param_idx += 1

        if bot_data.description is not None:
            updates.append(f"description = ${param_idx}")
            params.append(bot_data.description)
            param_idx += 1

        if bot_data.status is not None:
            updates.append(f"status = ${param_idx}")
            params.append(bot_data.status)
            param_idx += 1

        if bot_data.trading_symbol is not None:
            updates.append(f"trading_symbol = ${param_idx}")
            params.append(bot_data.trading_symbol.upper())
            param_idx += 1

        if bot_data.default_leverage is not None:
            updates.append(f"default_leverage = ${param_idx}")
            params.append(bot_data.default_leverage)
            param_idx += 1

        if bot_data.default_margin_usd is not None:
            updates.append(f"default_margin_usd = ${param_idx}")
            params.append(bot_data.default_margin_usd)
            param_idx += 1

        if bot_data.default_stop_loss_pct is not None:
            updates.append(f"default_stop_loss_pct = ${param_idx}")
            params.append(bot_data.default_stop_loss_pct)
            param_idx += 1

        if bot_data.default_take_profit_pct is not None:
            updates.append(f"default_take_profit_pct = ${param_idx}")
            params.append(bot_data.default_take_profit_pct)
            param_idx += 1

        if bot_data.default_max_positions is not None:
            updates.append(f"default_max_positions = ${param_idx}")
            params.append(bot_data.default_max_positions)
            param_idx += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append("updated_at = NOW()")
        params.append(bot_id)

        query = f"""
            UPDATE bots
            SET {', '.join(updates)}
            WHERE id = ${param_idx}
        """

        await transaction_db.execute(query, *params)

        # Log admin activity
        await transaction_db.execute("""
            INSERT INTO admin_activity_log (admin_id, action, entity_type, entity_id, details)
            SELECT a.id, 'updated_bot', 'bot', $2, $3::jsonb
            FROM admins a WHERE a.user_id = $1
        """, admin_user_id, bot_id, f'{{"bot_name": "{existing["name"]}"}}')

        logger.info("Bot updated", bot_id=bot_id, admin_user_id=admin_user_id)

        return {
            "success": True,
            "message": "Bot updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating bot", bot_id=bot_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bots/{bot_id}")
async def delete_bot(
    bot_id: str,
    admin_user_id: str = Depends(verify_admin)
):
    """Archive a bot (soft delete)"""
    try:
        bot = await transaction_db.fetchrow("""
            SELECT id, name FROM bots WHERE id = $1
        """, bot_id)

        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        # Archive bot (soft delete)
        await transaction_db.execute("""
            UPDATE bots
            SET status = 'archived', updated_at = NOW()
            WHERE id = $1
        """, bot_id)

        # Cancel all active subscriptions
        await transaction_db.execute("""
            UPDATE bot_subscriptions
            SET status = 'cancelled', updated_at = NOW()
            WHERE bot_id = $1 AND status = 'active'
        """, bot_id)

        # Log admin activity
        await transaction_db.execute("""
            INSERT INTO admin_activity_log (admin_id, action, entity_type, entity_id, details)
            SELECT a.id, 'archived_bot', 'bot', $2, $3::jsonb
            FROM admins a WHERE a.user_id = $1
        """, admin_user_id, bot_id, f'{{"bot_name": "{bot["name"]}"}}')

        logger.info("Bot archived", bot_id=bot_id, admin_user_id=admin_user_id)

        return {
            "success": True,
            "message": f"Bot '{bot['name']}' archived successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error archiving bot", bot_id=bot_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bots/{bot_id}/permanent")
async def permanently_delete_bot(
    bot_id: str,
    admin_user_id: str = Depends(verify_admin)
):
    """Permanently delete a bot and all related data"""
    try:
        bot = await transaction_db.fetchrow("""
            SELECT id, name FROM bots WHERE id = $1
        """, bot_id)

        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        # Delete related data in order (foreign key constraints)
        # 1. Delete bot signal executions
        await transaction_db.execute("""
            DELETE FROM bot_signal_executions
            WHERE signal_id IN (SELECT id FROM bot_signals WHERE bot_id = $1)
        """, bot_id)

        # 2. Delete bot signals
        await transaction_db.execute("""
            DELETE FROM bot_signals WHERE bot_id = $1
        """, bot_id)

        # 3. Delete bot subscriptions
        await transaction_db.execute("""
            DELETE FROM bot_subscriptions WHERE bot_id = $1
        """, bot_id)

        # 4. Delete the bot itself
        await transaction_db.execute("""
            DELETE FROM bots WHERE id = $1
        """, bot_id)

        # Log admin activity
        await transaction_db.execute("""
            INSERT INTO admin_activity_log (admin_id, action, entity_type, entity_id, details)
            SELECT a.id, 'permanently_deleted_bot', 'bot', $2, $3::jsonb
            FROM admins a WHERE a.user_id = $1
        """, admin_user_id, bot_id, f'{{"bot_name": "{bot["name"]}"}}')

        logger.info("Bot permanently deleted", bot_id=bot_id, admin_user_id=admin_user_id)

        return {
            "success": True,
            "message": f"Bot '{bot['name']}' permanently deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error permanently deleting bot", bot_id=bot_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bots/{bot_id}/stats")
async def get_bot_stats(
    bot_id: str,
    admin_user_id: str = Depends(verify_admin)
):
    """Get detailed statistics for a specific bot"""
    try:
        bot = await transaction_db.fetchrow("""
            SELECT * FROM bots WHERE id = $1
        """, bot_id)

        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        # Get subscription stats
        subscription_stats = await transaction_db.fetchrow("""
            SELECT
                COUNT(*) as total_subscriptions,
                COUNT(*) FILTER (WHERE status = 'active') as active_subscriptions,
                COALESCE(SUM(total_signals_received), 0) as total_signals_received,
                COALESCE(SUM(total_orders_executed), 0) as total_orders_executed,
                COALESCE(SUM(total_pnl_usd), 0) as total_pnl
            FROM bot_subscriptions
            WHERE bot_id = $1
        """, bot_id)

        # Get recent signals
        recent_signals = await transaction_db.fetch("""
            SELECT
                id, ticker, action,
                successful_executions, failed_executions,
                created_at
            FROM bot_signals
            WHERE bot_id = $1
            ORDER BY created_at DESC
            LIMIT 10
        """, bot_id)

        return {
            "success": True,
            "data": {
                "bot": dict(bot),
                "subscription_stats": dict(subscription_stats),
                "recent_signals": [dict(s) for s in recent_signals]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting bot stats", bot_id=bot_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EXCHANGES MANAGEMENT (Admin)
# ============================================================================

@router.get("/exchanges")
async def get_all_exchanges(
    admin_user_id: str = Depends(verify_admin)
):
    """Get all exchange accounts with user info for admin view"""
    try:
        # Get exchange statistics
        stats = await transaction_db.fetchrow("""
            SELECT
                COUNT(*) as total_exchanges,
                COUNT(*) FILTER (WHERE is_active = true) as active_exchanges,
                COUNT(*) FILTER (WHERE is_active = false) as inactive_exchanges,
                COUNT(DISTINCT exchange) as unique_exchanges,
                COUNT(DISTINCT user_id) as users_with_exchanges
            FROM exchange_accounts
        """)

        # Get exchange type breakdown
        exchange_breakdown = await transaction_db.fetch("""
            SELECT
                exchange,
                COUNT(*) as count,
                COUNT(*) FILTER (WHERE is_active = true) as active_count
            FROM exchange_accounts
            GROUP BY exchange
            ORDER BY count DESC
        """)

        # Get all exchanges with user info
        exchanges = await transaction_db.fetch("""
            SELECT
                ea.id,
                ea.name as account_name,
                ea.exchange,
                ea.is_active,
                ea.testnet,
                ea.created_at,
                ea.updated_at,
                u.id as user_id,
                u.name as user_name,
                u.email as user_email
            FROM exchange_accounts ea
            INNER JOIN users u ON u.id = ea.user_id
            ORDER BY ea.created_at DESC
        """)

        return {
            "success": True,
            "data": {
                "stats": {
                    "total": stats["total_exchanges"],
                    "active": stats["active_exchanges"],
                    "inactive": stats["inactive_exchanges"],
                    "unique_exchanges": stats["unique_exchanges"],
                    "users_with_exchanges": stats["users_with_exchanges"]
                },
                "breakdown": [dict(b) for b in exchange_breakdown],
                "exchanges": [dict(e) for e in exchanges]
            }
        }

    except Exception as e:
        logger.error("Error getting exchanges for admin", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBHOOKS MANAGEMENT (Admin)
# ============================================================================

@router.get("/webhooks")
async def get_all_webhooks(
    admin_user_id: str = Depends(verify_admin)
):
    """Get all webhooks with user info for admin view"""
    try:
        # Get webhook statistics
        stats = await transaction_db.fetchrow("""
            SELECT
                COUNT(*) as total_webhooks,
                COUNT(*) FILTER (WHERE status = 'active') as active_webhooks,
                COUNT(*) FILTER (WHERE status = 'paused') as paused_webhooks,
                COUNT(*) FILTER (WHERE status = 'disabled' OR status = 'error') as inactive_webhooks,
                COUNT(DISTINCT user_id) as users_with_webhooks,
                COALESCE(SUM(total_deliveries), 0) as total_deliveries,
                COALESCE(SUM(successful_deliveries), 0) as successful_deliveries,
                COALESCE(SUM(failed_deliveries), 0) as failed_deliveries
            FROM webhooks
        """)

        # Get webhook type breakdown
        type_breakdown = await transaction_db.fetch("""
            SELECT
                COALESCE(market_type, 'unknown') as market_type,
                COUNT(*) as count,
                COUNT(*) FILTER (WHERE status = 'active') as active_count
            FROM webhooks
            GROUP BY market_type
            ORDER BY count DESC
        """)

        # Get all webhooks with user info
        webhooks = await transaction_db.fetch("""
            SELECT
                w.id,
                w.name,
                w.url_path,
                w.status,
                w.market_type,
                w.is_public,
                w.total_deliveries,
                w.successful_deliveries,
                w.failed_deliveries,
                w.last_delivery_at,
                w.created_at,
                w.updated_at,
                u.id as user_id,
                u.name as user_name,
                u.email as user_email
            FROM webhooks w
            INNER JOIN users u ON u.id = w.user_id
            ORDER BY w.created_at DESC
        """)

        return {
            "success": True,
            "data": {
                "stats": {
                    "total": stats["total_webhooks"],
                    "active": stats["active_webhooks"],
                    "paused": stats["paused_webhooks"],
                    "inactive": stats["inactive_webhooks"],
                    "users_with_webhooks": stats["users_with_webhooks"],
                    "total_deliveries": int(stats["total_deliveries"]),
                    "successful_deliveries": int(stats["successful_deliveries"]),
                    "failed_deliveries": int(stats["failed_deliveries"])
                },
                "breakdown": [dict(b) for b in type_breakdown],
                "webhooks": [dict(w) for w in webhooks]
            }
        }

    except Exception as e:
        logger.error("Error getting webhooks for admin", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BOT METRICS - Win Rate & P&L Calculation
# ============================================================================

@router.get("/bots/metrics/calculate")
async def calculate_bot_metrics(
    admin_user_id: str = Depends(verify_admin)
):
    """
    Calculate and update Win Rate and P&L metrics for all bots.

    Calculation method:
    - Win Rate: (total wins / total trades) * 100 across all subscriptions
    - Avg P&L %: Average P&L percentage from closed trades
    - Also updates total_subscribers count
    """
    try:
        # Get all active bots
        bots = await transaction_db.fetch("""
            SELECT id, name FROM bots WHERE status != 'archived'
        """)

        updated_bots = []

        for bot in bots:
            bot_id = str(bot["id"])

            # Calculate metrics from bot_subscriptions
            subscription_metrics = await transaction_db.fetchrow("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'active') as active_subscribers,
                    COALESCE(SUM(win_count), 0) as total_wins,
                    COALESCE(SUM(loss_count), 0) as total_losses,
                    COALESCE(SUM(total_pnl_usd), 0) as total_pnl_usd,
                    COALESCE(SUM(total_orders_executed), 0) as total_orders
                FROM bot_subscriptions
                WHERE bot_id = $1
            """, bot_id)

            total_wins = int(subscription_metrics["total_wins"] or 0)
            total_losses = int(subscription_metrics["total_losses"] or 0)
            total_trades = total_wins + total_losses
            active_subscribers = int(subscription_metrics["active_subscribers"] or 0)
            total_pnl_usd = float(subscription_metrics["total_pnl_usd"] or 0)
            total_orders = int(subscription_metrics["total_orders"] or 0)

            # Calculate Win Rate
            win_rate = (total_wins / total_trades * 100) if total_trades > 0 else None

            # Calculate Average P&L % from bot_trades if available
            avg_pnl_pct = await transaction_db.fetchval("""
                SELECT AVG(pnl_pct)
                FROM bot_trades bt
                JOIN bot_subscriptions bs ON bt.subscription_id = bs.id
                WHERE bs.bot_id = $1 AND bt.status = 'closed' AND bt.pnl_pct IS NOT NULL
            """, bot_id)

            # If no trades in bot_trades, estimate from total P&L
            if avg_pnl_pct is None and total_orders > 0 and total_pnl_usd != 0:
                # Rough estimate: assume average trade size and calculate %
                # This is a fallback when detailed trade data isn't available
                avg_pnl_pct = None  # Keep null if we can't calculate properly

            # Update the bot record
            await transaction_db.execute("""
                UPDATE bots
                SET
                    total_subscribers = $2,
                    avg_win_rate = $3,
                    avg_pnl_pct = $4,
                    updated_at = NOW()
                WHERE id = $1
            """, bot_id, active_subscribers, win_rate, float(avg_pnl_pct) if avg_pnl_pct else None)

            updated_bots.append({
                "bot_id": bot_id,
                "name": bot["name"],
                "active_subscribers": active_subscribers,
                "total_wins": total_wins,
                "total_losses": total_losses,
                "total_trades": total_trades,
                "win_rate": round(win_rate, 2) if win_rate else None,
                "avg_pnl_pct": round(float(avg_pnl_pct), 2) if avg_pnl_pct else None,
                "total_pnl_usd": round(total_pnl_usd, 2)
            })

        logger.info("Bot metrics calculated", updated_count=len(updated_bots), admin_user_id=admin_user_id)

        return {
            "success": True,
            "message": f"Metrics updated for {len(updated_bots)} bots",
            "data": updated_bots
        }

    except Exception as e:
        logger.error("Error calculating bot metrics", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bots/{bot_id}/metrics")
async def get_bot_detailed_metrics(
    bot_id: str,
    admin_user_id: str = Depends(verify_admin)
):
    """
    Get detailed metrics for a specific bot including:
    - Overall Win Rate and P&L
    - Per-subscriber breakdown
    - Trade history summary
    - Daily P&L trend
    """
    try:
        # Verify bot exists
        bot = await transaction_db.fetchrow("""
            SELECT id, name, status, total_subscribers, avg_win_rate, avg_pnl_pct
            FROM bots WHERE id = $1
        """, bot_id)

        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        # Get aggregate metrics from subscriptions
        aggregate_metrics = await transaction_db.fetchrow("""
            SELECT
                COUNT(*) as total_subscriptions,
                COUNT(*) FILTER (WHERE status = 'active') as active_subscriptions,
                COALESCE(SUM(win_count), 0) as total_wins,
                COALESCE(SUM(loss_count), 0) as total_losses,
                COALESCE(SUM(total_pnl_usd), 0) as total_pnl_usd,
                COALESCE(SUM(total_signals_received), 0) as total_signals,
                COALESCE(SUM(total_orders_executed), 0) as total_orders_executed,
                COALESCE(SUM(total_orders_failed), 0) as total_orders_failed
            FROM bot_subscriptions
            WHERE bot_id = $1
        """, bot_id)

        total_wins = int(aggregate_metrics["total_wins"] or 0)
        total_losses = int(aggregate_metrics["total_losses"] or 0)
        total_trades = total_wins + total_losses
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

        # Get per-subscriber breakdown (top performers)
        top_subscribers = await transaction_db.fetch("""
            SELECT
                bs.id as subscription_id,
                u.name as user_name,
                u.email as user_email,
                bs.win_count,
                bs.loss_count,
                bs.total_pnl_usd,
                bs.total_orders_executed,
                bs.status,
                CASE WHEN (bs.win_count + bs.loss_count) > 0
                     THEN (bs.win_count::float / (bs.win_count + bs.loss_count) * 100)
                     ELSE 0
                END as win_rate
            FROM bot_subscriptions bs
            JOIN users u ON u.id = bs.user_id
            WHERE bs.bot_id = $1
            ORDER BY bs.total_pnl_usd DESC
            LIMIT 10
        """, bot_id)

        # Get daily P&L trend (last 30 days)
        daily_pnl = await transaction_db.fetch("""
            SELECT
                snapshot_date,
                SUM(daily_pnl_usd) as daily_pnl,
                SUM(daily_wins) as wins,
                SUM(daily_losses) as losses
            FROM bot_pnl_history
            WHERE bot_id = $1 AND snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY snapshot_date
            ORDER BY snapshot_date DESC
        """, bot_id)

        # Get trade statistics from bot_trades
        trade_stats = await transaction_db.fetchrow("""
            SELECT
                COUNT(*) as total_trades,
                COUNT(*) FILTER (WHERE is_winner = true) as winning_trades,
                COUNT(*) FILTER (WHERE is_winner = false) as losing_trades,
                AVG(pnl_usd) as avg_pnl_usd,
                AVG(pnl_pct) as avg_pnl_pct,
                MAX(pnl_usd) as best_trade,
                MIN(pnl_usd) as worst_trade,
                SUM(total_fee_usd) as total_fees
            FROM bot_trades bt
            JOIN bot_subscriptions bs ON bt.subscription_id = bs.id
            WHERE bs.bot_id = $1 AND bt.status = 'closed'
        """, bot_id)

        return {
            "success": True,
            "data": {
                "bot": {
                    "id": str(bot["id"]),
                    "name": bot["name"],
                    "status": bot["status"],
                    "stored_win_rate": float(bot["avg_win_rate"]) if bot["avg_win_rate"] else None,
                    "stored_pnl_pct": float(bot["avg_pnl_pct"]) if bot["avg_pnl_pct"] else None
                },
                "aggregate_metrics": {
                    "total_subscriptions": aggregate_metrics["total_subscriptions"],
                    "active_subscriptions": aggregate_metrics["active_subscriptions"],
                    "total_wins": total_wins,
                    "total_losses": total_losses,
                    "total_trades": total_trades,
                    "win_rate": round(win_rate, 2),
                    "total_pnl_usd": round(float(aggregate_metrics["total_pnl_usd"] or 0), 2),
                    "total_signals": aggregate_metrics["total_signals"],
                    "total_orders_executed": aggregate_metrics["total_orders_executed"],
                    "total_orders_failed": aggregate_metrics["total_orders_failed"]
                },
                "trade_stats": {
                    "total_closed_trades": trade_stats["total_trades"] if trade_stats else 0,
                    "winning_trades": trade_stats["winning_trades"] if trade_stats else 0,
                    "losing_trades": trade_stats["losing_trades"] if trade_stats else 0,
                    "avg_pnl_usd": round(float(trade_stats["avg_pnl_usd"] or 0), 2) if trade_stats else 0,
                    "avg_pnl_pct": round(float(trade_stats["avg_pnl_pct"] or 0), 2) if trade_stats else 0,
                    "best_trade": round(float(trade_stats["best_trade"] or 0), 2) if trade_stats else 0,
                    "worst_trade": round(float(trade_stats["worst_trade"] or 0), 2) if trade_stats else 0,
                    "total_fees": round(float(trade_stats["total_fees"] or 0), 2) if trade_stats else 0
                },
                "top_subscribers": [
                    {
                        "subscription_id": str(s["subscription_id"]),
                        "user_name": s["user_name"],
                        "user_email": s["user_email"],
                        "win_count": s["win_count"],
                        "loss_count": s["loss_count"],
                        "win_rate": round(float(s["win_rate"]), 2),
                        "total_pnl_usd": round(float(s["total_pnl_usd"] or 0), 2),
                        "total_orders": s["total_orders_executed"],
                        "status": s["status"]
                    }
                    for s in top_subscribers
                ],
                "daily_pnl_trend": [
                    {
                        "date": str(d["snapshot_date"]),
                        "pnl": round(float(d["daily_pnl"] or 0), 2),
                        "wins": d["wins"],
                        "losses": d["losses"]
                    }
                    for d in daily_pnl
                ]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting bot detailed metrics", bot_id=bot_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DATABASE MIGRATIONS (Admin)
# ============================================================================

@router.post("/migrations/run")
async def run_migration(
    migration_name: str,
    admin_user_id: str = Depends(verify_admin)
):
    """
    Run a specific database migration.
    Only for admins, and only in development mode.
    """
    import os
    env = os.environ.get('ENV', 'dev').lower()

    # Available migrations
    migrations = {
        "add_default_max_positions": """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'bots' AND column_name = 'default_max_positions'
                ) THEN
                    ALTER TABLE bots ADD COLUMN default_max_positions INTEGER DEFAULT 3;
                    ALTER TABLE bots ADD CONSTRAINT check_default_max_positions
                        CHECK (default_max_positions >= 1 AND default_max_positions <= 20);
                    RAISE NOTICE 'Coluna default_max_positions adicionada à tabela bots';
                ELSE
                    RAISE NOTICE 'Coluna default_max_positions já existe na tabela bots';
                END IF;
            END $$;
            COMMENT ON COLUMN bots.default_max_positions IS 'Número máximo de posições simultâneas sugerido pelo admin. Clientes podem sobrescrever na subscription.';
        """
    }

    if migration_name not in migrations:
        raise HTTPException(
            status_code=400,
            detail=f"Migration '{migration_name}' not found. Available: {list(migrations.keys())}"
        )

    try:
        # Run the migration
        await transaction_db.execute(migrations[migration_name])

        # Verify the change
        if migration_name == "add_default_max_positions":
            result = await transaction_db.fetchrow("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'bots' AND column_name = 'default_max_positions'
            """)

            # Get sample bots
            bots = await transaction_db.fetch("""
                SELECT id, name, default_max_positions FROM bots LIMIT 5
            """)

            return {
                "success": True,
                "message": f"Migration '{migration_name}' executed successfully",
                "column_info": dict(result) if result else None,
                "sample_bots": [dict(b) for b in bots]
            }

        return {
            "success": True,
            "message": f"Migration '{migration_name}' executed successfully"
        }

    except Exception as e:
        logger.error("Error running migration", migration=migration_name, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FIX BOT TRADES - Sync open trades with exchange positions
# ============================================================================

@router.post("/fix-bot-trades")
async def fix_bot_open_trades(
    dry_run: bool = True,
    admin_user_id: str = Depends(verify_admin)
):
    """
    Fix orphan bot_trades that are marked as 'open' but don't have actual positions.
    This happens when SL/TP closes a position but the bot_trades table isn't updated.

    Args:
        dry_run: If True, only show what would be fixed without making changes

    Returns:
        Summary of fixes applied or would be applied
    """
    try:
        # 1. Find all open trades in bot_trades
        open_trades = await transaction_db.fetch("""
            SELECT
                bt.id,
                bt.subscription_id,
                bt.symbol,
                bt.direction,
                bt.entry_price,
                bt.entry_quantity,
                bt.entry_time,
                bt.sl_order_id,
                bt.tp_order_id,
                bs.user_id,
                u.email
            FROM bot_trades bt
            JOIN bot_subscriptions bs ON bs.id = bt.subscription_id
            JOIN users u ON u.id = bs.user_id
            WHERE bt.status = 'open'
            ORDER BY bt.entry_time DESC
        """)

        # 2. Check subscription position counters
        subscriptions = await transaction_db.fetch("""
            SELECT
                bs.id,
                bs.current_positions,
                bs.max_concurrent_positions,
                u.email,
                b.name as bot_name,
                (SELECT COUNT(*) FROM bot_trades WHERE subscription_id = bs.id AND status = 'open') as actual_open
            FROM bot_subscriptions bs
            JOIN users u ON u.id = bs.user_id
            JOIN bots b ON b.id = bs.bot_id
            WHERE bs.status = 'active'
        """)

        # Identify mismatches
        mismatches = [
            dict(sub) for sub in subscriptions
            if sub['current_positions'] != sub['actual_open']
        ]

        result = {
            "open_trades_found": len(open_trades),
            "open_trades": [
                {
                    "id": str(t['id']),
                    "email": t['email'],
                    "symbol": t['symbol'],
                    "direction": t['direction'],
                    "entry_price": float(t['entry_price']) if t['entry_price'] else None,
                    "entry_time": t['entry_time'].isoformat() if t['entry_time'] else None,
                }
                for t in open_trades
            ],
            "subscription_mismatches": len(mismatches),
            "mismatches": [
                {
                    "id": str(m['id']),
                    "email": m['email'],
                    "bot_name": m['bot_name'],
                    "current_positions_db": m['current_positions'],
                    "actual_open_trades": m['actual_open'],
                    "max_concurrent": m['max_concurrent_positions'],
                }
                for m in mismatches
            ],
            "dry_run": dry_run,
            "fixes_applied": False
        }

        # 3. Apply fixes if not dry_run
        if not dry_run and (open_trades or mismatches):
            # Close all orphan trades
            if open_trades:
                await transaction_db.execute("""
                    UPDATE bot_trades
                    SET status = 'closed_manual',
                        exit_time = NOW(),
                        exit_reason = 'manual_cleanup_api',
                        updated_at = NOW()
                    WHERE status = 'open'
                """)
                logger.info(f"Closed {len(open_trades)} orphan trades")

            # Reset all subscription position counters to 0
            await transaction_db.execute("""
                UPDATE bot_subscriptions
                SET current_positions = 0,
                    updated_at = NOW()
                WHERE status = 'active'
            """)
            logger.info("Reset all subscription position counters to 0")

            result["fixes_applied"] = True
            result["message"] = f"Fixed {len(open_trades)} orphan trades and reset {len(subscriptions)} subscription counters"
        elif dry_run:
            result["message"] = f"DRY RUN: Would fix {len(open_trades)} orphan trades and {len(mismatches)} subscription mismatches"
        else:
            result["message"] = "No issues found - all trades are in sync"

        return {"success": True, "data": result}

    except Exception as e:
        logger.error("Error fixing bot trades", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-bot-positions")
async def sync_bot_positions(
    admin_user_id: str = Depends(verify_admin)
):
    """
    Sync bot position counters with actual positions.
    Uses the smart sync that checks against the positions table.
    """
    try:
        from infrastructure.services.bot_trade_tracker_service import BotTradeTrackerService

        tracker = BotTradeTrackerService(transaction_db)
        result = await tracker.sync_position_counters()

        return {"success": True, "data": result}

    except Exception as e:
        logger.error("Error syncing bot positions", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Bot Symbol Configs - Per-symbol trading configuration
# ============================================================================

class SymbolConfigCreate(BaseModel):
    """Model for creating/updating a symbol config"""
    symbol: str = Field(..., min_length=3, max_length=20)
    leverage: int = Field(default=10, ge=1, le=125)
    margin_usd: float = Field(default=20.0, ge=5.0)
    stop_loss_pct: float = Field(default=3.0, ge=0.1, le=50.0)
    take_profit_pct: float = Field(default=5.0, ge=0.1, le=100.0)
    max_positions: int = Field(default=3, ge=1, le=20)
    is_active: bool = Field(default=True)


class SymbolConfigBatchUpdate(BaseModel):
    """Model for batch updating symbol configs"""
    configs: List[SymbolConfigCreate]


@router.get("/bots/{bot_id}/symbol-configs")
async def get_bot_symbol_configs(
    bot_id: UUID,
    admin_user_id: str = Depends(verify_admin)
):
    """
    Get all symbol configs for a bot.
    Also returns symbols from linked strategy that don't have configs yet.
    """
    try:
        # Get existing configs
        configs = await transaction_db.fetch("""
            SELECT id, bot_id, symbol, leverage, margin_usd, stop_loss_pct,
                   take_profit_pct, max_positions, is_active, created_at, updated_at
            FROM bot_symbol_configs
            WHERE bot_id = $1
            ORDER BY symbol
        """, bot_id)

        # Get bot default config
        bot = await transaction_db.fetchrow("""
            SELECT default_leverage, default_margin_usd, default_stop_loss_pct,
                   default_take_profit_pct, default_max_positions
            FROM bots
            WHERE id = $1
        """, bot_id)

        # Get symbols from linked strategy (if any)
        strategy = await transaction_db.fetchrow("""
            SELECT symbols FROM strategies WHERE bot_id = $1
        """, bot_id)

        strategy_symbols = []
        if strategy and strategy["symbols"]:
            import json
            if isinstance(strategy["symbols"], list):
                strategy_symbols = strategy["symbols"]
            else:
                strategy_symbols = json.loads(strategy["symbols"])

        # Find symbols without config
        configured_symbols = {c["symbol"] for c in configs}
        unconfigured_symbols = [s for s in strategy_symbols if s not in configured_symbols]

        return {
            "success": True,
            "data": {
                "configs": [dict(c) for c in configs],
                "bot_defaults": dict(bot) if bot else None,
                "strategy_symbols": strategy_symbols,
                "unconfigured_symbols": unconfigured_symbols
            }
        }

    except Exception as e:
        logger.error("Error getting bot symbol configs", bot_id=str(bot_id), error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bots/{bot_id}/symbol-configs")
async def create_or_update_bot_symbol_configs(
    bot_id: UUID,
    data: SymbolConfigBatchUpdate,
    admin_user_id: str = Depends(verify_admin)
):
    """
    Create or update symbol configs for a bot (batch operation).
    Uses UPSERT to handle both create and update.
    """
    try:
        # Verify bot exists
        bot = await transaction_db.fetchrow("SELECT id FROM bots WHERE id = $1", bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        created_count = 0
        updated_count = 0

        for config in data.configs:
            # Check if config exists
            existing = await transaction_db.fetchval("""
                SELECT id FROM bot_symbol_configs
                WHERE bot_id = $1 AND symbol = $2
            """, bot_id, config.symbol.upper())

            if existing:
                # Update
                await transaction_db.execute("""
                    UPDATE bot_symbol_configs
                    SET leverage = $3, margin_usd = $4, stop_loss_pct = $5,
                        take_profit_pct = $6, max_positions = $7, is_active = $8,
                        updated_at = NOW()
                    WHERE bot_id = $1 AND symbol = $2
                """, bot_id, config.symbol.upper(), config.leverage, config.margin_usd,
                    config.stop_loss_pct, config.take_profit_pct, config.max_positions,
                    config.is_active)
                updated_count += 1
            else:
                # Create
                await transaction_db.execute("""
                    INSERT INTO bot_symbol_configs
                    (bot_id, symbol, leverage, margin_usd, stop_loss_pct,
                     take_profit_pct, max_positions, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, bot_id, config.symbol.upper(), config.leverage, config.margin_usd,
                    config.stop_loss_pct, config.take_profit_pct, config.max_positions,
                    config.is_active)
                created_count += 1

        return {
            "success": True,
            "message": f"Created {created_count}, updated {updated_count} symbol configs",
            "data": {"created": created_count, "updated": updated_count}
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error saving bot symbol configs", bot_id=str(bot_id), error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bots/{bot_id}/symbol-configs/{symbol}")
async def delete_bot_symbol_config(
    bot_id: UUID,
    symbol: str,
    admin_user_id: str = Depends(verify_admin)
):
    """Delete a specific symbol config from a bot"""
    try:
        result = await transaction_db.execute("""
            DELETE FROM bot_symbol_configs
            WHERE bot_id = $1 AND symbol = $2
        """, bot_id, symbol.upper())

        if "DELETE 0" in result:
            raise HTTPException(status_code=404, detail="Symbol config not found")

        return {"success": True, "message": f"Symbol config {symbol} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting bot symbol config", bot_id=str(bot_id), symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bots/{bot_id}/sync-strategy-symbols")
async def sync_strategy_symbols(
    bot_id: UUID,
    admin_user_id: str = Depends(verify_admin)
):
    """
    Sync symbols from linked strategy to bot_symbol_configs.
    Creates configs for symbols that don't have one yet, using bot defaults.
    """
    try:
        # Get bot defaults
        bot = await transaction_db.fetchrow("""
            SELECT default_leverage, default_margin_usd, default_stop_loss_pct,
                   default_take_profit_pct, default_max_positions
            FROM bots
            WHERE id = $1
        """, bot_id)

        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        # Get symbols from strategy
        strategy = await transaction_db.fetchrow("""
            SELECT symbols FROM strategies WHERE bot_id = $1
        """, bot_id)

        if not strategy or not strategy["symbols"]:
            return {
                "success": True,
                "message": "No strategy linked to this bot or no symbols defined",
                "data": {"created": 0}
            }

        import json
        if isinstance(strategy["symbols"], list):
            strategy_symbols = strategy["symbols"]
        else:
            strategy_symbols = json.loads(strategy["symbols"])

        # Get existing configs
        existing = await transaction_db.fetch("""
            SELECT symbol FROM bot_symbol_configs WHERE bot_id = $1
        """, bot_id)
        existing_symbols = {e["symbol"] for e in existing}

        # Create configs for new symbols
        created_count = 0
        for symbol in strategy_symbols:
            symbol_upper = symbol.upper()
            if symbol_upper not in existing_symbols:
                await transaction_db.execute("""
                    INSERT INTO bot_symbol_configs
                    (bot_id, symbol, leverage, margin_usd, stop_loss_pct,
                     take_profit_pct, max_positions, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE)
                """, bot_id, symbol_upper,
                    bot["default_leverage"] or 10,
                    bot["default_margin_usd"] or 20.0,
                    bot["default_stop_loss_pct"] or 3.0,
                    bot["default_take_profit_pct"] or 5.0,
                    bot["default_max_positions"] or 3)
                created_count += 1

        return {
            "success": True,
            "message": f"Synced {created_count} new symbols from strategy",
            "data": {
                "created": created_count,
                "total_strategy_symbols": len(strategy_symbols),
                "symbols": strategy_symbols
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error syncing strategy symbols", bot_id=str(bot_id), error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bots/{bot_id}/symbol-configs/apply-to-all")
async def apply_config_to_all_symbols(
    bot_id: UUID,
    config: SymbolConfigCreate,
    admin_user_id: str = Depends(verify_admin)
):
    """
    Apply the same config to all symbols of a bot.
    Updates existing configs and creates new ones for unconfigured symbols.
    """
    try:
        # Get strategy symbols
        strategy = await transaction_db.fetchrow("""
            SELECT symbols FROM strategies WHERE bot_id = $1
        """, bot_id)

        if not strategy or not strategy["symbols"]:
            raise HTTPException(status_code=400, detail="No strategy linked to this bot")

        import json
        if isinstance(strategy["symbols"], list):
            strategy_symbols = strategy["symbols"]
        else:
            strategy_symbols = json.loads(strategy["symbols"])

        updated_count = 0
        for symbol in strategy_symbols:
            symbol_upper = symbol.upper()

            # Check if exists
            existing = await transaction_db.fetchval("""
                SELECT id FROM bot_symbol_configs WHERE bot_id = $1 AND symbol = $2
            """, bot_id, symbol_upper)

            if existing:
                await transaction_db.execute("""
                    UPDATE bot_symbol_configs
                    SET leverage = $3, margin_usd = $4, stop_loss_pct = $5,
                        take_profit_pct = $6, max_positions = $7, is_active = $8,
                        updated_at = NOW()
                    WHERE bot_id = $1 AND symbol = $2
                """, bot_id, symbol_upper, config.leverage, config.margin_usd,
                    config.stop_loss_pct, config.take_profit_pct, config.max_positions,
                    config.is_active)
            else:
                await transaction_db.execute("""
                    INSERT INTO bot_symbol_configs
                    (bot_id, symbol, leverage, margin_usd, stop_loss_pct,
                     take_profit_pct, max_positions, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, bot_id, symbol_upper, config.leverage, config.margin_usd,
                    config.stop_loss_pct, config.take_profit_pct, config.max_positions,
                    config.is_active)

            updated_count += 1

        return {
            "success": True,
            "message": f"Applied config to {updated_count} symbols",
            "data": {"updated": updated_count}
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error applying config to all symbols", bot_id=str(bot_id), error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
