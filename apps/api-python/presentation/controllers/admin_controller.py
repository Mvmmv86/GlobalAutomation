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


class BotUpdate(BaseModel):
    """Model for updating bot configuration"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=10, max_length=1000)
    status: Optional[str] = Field(None, pattern="^(active|paused|archived)$")
    default_leverage: Optional[int] = Field(None, ge=1, le=125)
    default_margin_usd: Optional[float] = Field(None, ge=5.00)
    default_stop_loss_pct: Optional[float] = Field(None, ge=0.1, le=50.0)
    default_take_profit_pct: Optional[float] = Field(None, ge=0.1, le=100.0)


# ============================================================================
# Middleware - Admin Authentication
# ============================================================================

async def verify_admin(request: Request):
    """Verify that the user is an admin"""
    user_id = request.query_params.get('admin_user_id')

    if not user_id:
        raise HTTPException(status_code=401, detail="Admin authentication required")

    # Check if user is admin
    is_admin = await transaction_db.fetchval("""
        SELECT EXISTS(
            SELECT 1 FROM admins a
            INNER JOIN users u ON u.id = a.user_id
            WHERE a.user_id = $1 AND a.is_active = true AND u.is_admin = true
        )
    """, user_id)

    if not is_admin:
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
                master_webhook_path,
                default_leverage, default_margin_usd,
                default_stop_loss_pct, default_take_profit_pct,
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
                allowed_directions, master_webhook_path,
                default_leverage, default_margin_usd,
                default_stop_loss_pct, default_take_profit_pct
            ) VALUES ($1, $2, $3, 'active', $4, $5, $6, $7, $8, $9)
            RETURNING id
        """,
            bot_data.name,
            bot_data.description,
            bot_data.market_type,
            bot_data.allowed_directions,
            bot_data.master_webhook_path,
            bot_data.default_leverage,
            bot_data.default_margin_usd,
            bot_data.default_stop_loss_pct,
            bot_data.default_take_profit_pct
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
