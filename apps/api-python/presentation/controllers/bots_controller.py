"""
Bots Controller
Handles all bot-related endpoints (CRUD operations, master webhook)
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import os

import structlog
from slowapi import Limiter
from slowapi.util import get_remote_address

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.services.bot_broadcast_service import BotBroadcastService

logger = structlog.get_logger(__name__)

# Initialize rate limiter for webhook endpoints
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/v1/bots", tags=["bots"])


# ============================================================================
# Pydantic Models
# ============================================================================

class BotCreate(BaseModel):
    """Model for creating a new bot"""
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
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
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|paused|archived)$")
    default_leverage: Optional[int] = Field(None, ge=1, le=125)
    default_margin_usd: Optional[float] = Field(None, ge=5.00)
    default_stop_loss_pct: Optional[float] = Field(None, ge=0.1, le=50.0)
    default_take_profit_pct: Optional[float] = Field(None, ge=0.1, le=100.0)


class MasterWebhookPayload(BaseModel):
    """Payload received from TradingView master webhook"""
    ticker: str = Field(..., min_length=1)
    action: str = Field(..., pattern="^(buy|sell|close|close_all)$")
    price: Optional[float] = None
    # Note: Authentication is done via unique webhook_path, not via secret in payload


# ============================================================================
# ADMIN ENDPOINTS (Bot Management)
# ============================================================================

@router.get("")
async def list_bots(
    status: Optional[str] = None,
    market_type: Optional[str] = None
):
    """
    List all bots (admin view)

    Query params:
    - status: Filter by status (active, paused, archived)
    - market_type: Filter by market type (spot, futures)
    """
    try:
        query = """
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
            WHERE 1=1
        """
        params = []

        if status:
            query += f" AND status = ${len(params) + 1}"
            params.append(status)

        if market_type:
            query += f" AND market_type = ${len(params) + 1}"
            params.append(market_type)

        query += " ORDER BY created_at DESC"

        bots = await transaction_db.fetch(query, *params)

        return {
            "success": True,
            "data": [dict(bot) for bot in bots]
        }

    except Exception as e:
        logger.error("Error listing bots", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{bot_id}")
async def get_bot(bot_id: str):
    """Get detailed information about a specific bot"""
    try:
        bot = await transaction_db.fetchrow("""
            SELECT
                id, name, description, market_type, status,
                master_webhook_path,
                default_leverage, default_margin_usd,
                default_stop_loss_pct, default_take_profit_pct,
                total_subscribers, total_signals_sent,
                avg_win_rate, avg_pnl_pct,
                created_at, updated_at
            FROM bots
            WHERE id = $1
        """, bot_id)

        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")

        # Get recent signals
        recent_signals = await transaction_db.fetch("""
            SELECT
                id, ticker, action, total_subscribers,
                successful_executions, failed_executions,
                broadcast_duration_ms, created_at
            FROM bot_signals
            WHERE bot_id = $1
            ORDER BY created_at DESC
            LIMIT 10
        """, bot_id)

        return {
            "success": True,
            "data": {
                **dict(bot),
                "recent_signals": [dict(s) for s in recent_signals]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting bot", bot_id=bot_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_bot(bot_data: BotCreate, request: Request):
    """
    Create a new bot (admin only)

    The master_webhook_path acts as authentication - must be unique and secret (min 16 chars)
    """
    try:
        # Check if webhook_path already exists
        existing = await transaction_db.fetchval("""
            SELECT id FROM bots WHERE master_webhook_path = $1
        """, bot_data.master_webhook_path)

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Webhook path already exists. Choose a different unique path."
            )

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

        # Get base URL (same logic as useNgrokUrl hook in frontend)
        # Priority: 1) ngrok_url from DB, 2) environment vars, 3) request detection
        try:
            # Try to get ngrok URL from database (same as frontend does)
            ngrok_url_row = await transaction_db.fetchrow("""
                SELECT ngrok_url FROM system_config WHERE id = 1
            """)

            if ngrok_url_row and ngrok_url_row["ngrok_url"]:
                base_url = ngrok_url_row["ngrok_url"].rstrip('/')
                logger.info(f"Using ngrok URL from database: {base_url}")
            else:
                # Fallback to environment variable
                base_url = os.getenv("VITE_WEBHOOK_PUBLIC_URL") or os.getenv("API_BASE_URL")
                if base_url:
                    logger.info(f"Using URL from environment: {base_url}")
                else:
                    # Last fallback: detect from request
                    scheme = request.url.scheme
                    host = request.headers.get("host") or f"{request.client.host}:{request.url.port}"
                    base_url = f"{scheme}://{host}"
                    logger.info(f"Detected URL from request: {base_url}")

        except Exception as e:
            logger.warning(f"Failed to get ngrok URL from DB, using fallback: {e}")
            # Fallback to request detection
            scheme = request.url.scheme
            host = request.headers.get("host") or f"{request.client.host}:{request.url.port}"
            base_url = f"{scheme}://{host}"

        webhook_url = f"{base_url}/api/v1/bots/webhook/master/{bot_data.master_webhook_path}"

        logger.info("Bot created", bot_id=str(bot_id), name=bot_data.name, webhook_url=webhook_url)

        return {
            "success": True,
            "data": {
                "bot_id": str(bot_id),
                "webhook_url": webhook_url,
                "webhook_path": bot_data.master_webhook_path
            },
            "message": "Bot criado com sucesso! Copie a URL do webhook para configurar no TradingView."
        }

    except Exception as e:
        logger.error("Error creating bot", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{bot_id}")
async def update_bot(bot_id: str, bot_data: BotUpdate):
    """Update bot configuration (admin only)"""
    try:
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
            RETURNING id
        """

        result = await transaction_db.fetchval(query, *params)

        if not result:
            raise HTTPException(status_code=404, detail="Bot not found")

        logger.info("Bot updated", bot_id=bot_id)

        return {
            "success": True,
            "message": "Bot updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating bot", bot_id=bot_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{bot_id}")
async def delete_bot(bot_id: str):
    """Delete a bot (admin only) - Archives instead of hard delete"""
    try:
        result = await transaction_db.fetchval("""
            UPDATE bots
            SET status = 'archived', updated_at = NOW()
            WHERE id = $1
            RETURNING id
        """, bot_id)

        if not result:
            raise HTTPException(status_code=404, detail="Bot not found")

        logger.info("Bot archived", bot_id=bot_id)

        return {
            "success": True,
            "message": "Bot archived successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting bot", bot_id=bot_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MASTER WEBHOOK ENDPOINT (TradingView)
# ============================================================================

@router.post("/webhook/master/{webhook_path}")
@limiter.limit("10/minute")  # Max 10 signals per minute per IP
async def master_webhook(webhook_path: str, request: Request):
    """
    Master webhook endpoint for receiving TradingView signals
    This endpoint broadcasts signals to all active bot subscriptions

    Authentication: The webhook_path itself is unique and secret (no password needed in payload)
    Rate Limit: 10 requests per minute per IP address

    Args:
        webhook_path: Unique secret path identifying the bot (acts as authentication token)
        payload: {
            "ticker": "BTCUSDT",
            "action": "buy|sell|close|close_all",
            "price": 95000.00  (optional)
        }

    Example TradingView Alert Message:
        {
            "ticker": "{{ticker}}",
            "action": "buy",
            "price": {{close}}
        }
    """
    try:
        # Parse payload
        try:
            payload = await request.json()
        except:
            # If no JSON body, TradingView sends alert name in query params
            payload = {}

        logger.info("Master webhook received", webhook_path=webhook_path, payload=payload)

        # Extract ticker and action from payload
        # Support multiple formats:
        # 1. {"ticker": "BTCUSDT", "action": "buy"} - Custom JSON
        # 2. {"symbol": "DRIFTUSDT.P", "action": "Compra"} - TradingView PT-BR
        # 3. {"name": "DRIFTUSDT alert"} - TradingView default
        # 4. Extract from alert name if present
        import re

        # Try to get ticker from multiple field names
        ticker = payload.get("ticker") or payload.get("symbol")

        # Remove .P suffix from perpetual futures (e.g., DRIFTUSDT.P -> DRIFTUSDT)
        if ticker and ticker.endswith(".P"):
            ticker = ticker[:-2]
            logger.info("Removed .P suffix from ticker", original=payload.get("symbol"), cleaned=ticker)

        # Get action and normalize it
        action = payload.get("action", "buy")

        # Normalize Portuguese to English
        action_map = {
            "compra": "buy",
            "venda": "sell",
            "fechar": "close",
            "buy": "buy",
            "sell": "sell",
            "close": "close"
        }
        action = action_map.get(action.lower(), "buy")

        # If ticker not in payload, try to extract from alert name or trade_id
        if not ticker:
            # Try alert name
            alert_name = payload.get("name", "")
            if not alert_name:
                # Try trade_id field
                trade_id = payload.get("trade_id", "")
                if trade_id:
                    alert_name = trade_id

            # Look for common patterns: XXXUSDT, XXXUSD, XXXBTC
            ticker_match = re.search(r'([A-Z0-9]+USDT|[A-Z0-9]+USD|[A-Z0-9]+BTC)', alert_name.upper())
            if ticker_match:
                ticker = ticker_match.group(1)
                logger.info("Extracted ticker from alert name", alert_name=alert_name, ticker=ticker)

        # Validate we have a ticker
        if not ticker:
            logger.error("Could not extract ticker from webhook", payload=payload)
            raise HTTPException(
                status_code=400,
                detail="Missing ticker. Send JSON with 'ticker' or 'symbol' field, or include ticker in alert name"
            )

        # Get bot by webhook path (webhook_path itself is the authentication)
        bot = await transaction_db.fetchrow("""
            SELECT id, name, status
            FROM bots
            WHERE master_webhook_path = $1
        """, webhook_path)

        if not bot:
            logger.warning("Bot not found for webhook path", webhook_path=webhook_path)
            raise HTTPException(status_code=404, detail="Invalid webhook path")

        # Check if bot is active
        if bot["status"] != "active":
            logger.warning(
                "Bot is not active",
                webhook_path=webhook_path,
                bot_id=str(bot["id"]),
                status=bot["status"]
            )
            raise HTTPException(
                status_code=400,
                detail=f"Bot is {bot['status']}, cannot process signals"
            )

        # Broadcast signal to all active subscriptions
        broadcast_service = BotBroadcastService(transaction_db)

        result = await broadcast_service.broadcast_signal(
            bot_id=bot["id"],
            ticker=ticker,
            action=action,
            source_ip=request.client.host if request.client else "unknown",
            payload=payload
        )

        # Update bot statistics
        await transaction_db.execute("""
            UPDATE bots
            SET total_signals_sent = total_signals_sent + 1,
                updated_at = NOW()
            WHERE id = $1
        """, bot["id"])

        return {
            "success": True,
            "bot_name": bot["name"],
            "signal_id": result["signal_id"],
            "broadcast_stats": {
                "total_subscribers": result["total_subscribers"],
                "successful_executions": result["successful"],
                "failed_executions": result["failed"],
                "duration_ms": result["duration_ms"]
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Master webhook error",
            webhook_path=webhook_path,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DEBUG ENDPOINT - Signal Execution Errors
# ============================================================================

@router.get("/debug/recent-errors")
async def get_recent_signal_errors():
    """
    DEBUG: Get recent signal execution errors
    Useful for troubleshooting failed bot executions
    """
    try:
        executions = await transaction_db.fetch("""
            SELECT
                bse.id,
                bse.signal_id,
                bse.subscription_id,
                bse.status,
                bse.error_message,
                bse.execution_time_ms,
                bse.created_at,
                bs.ticker,
                bs.action,
                b.name as bot_name,
                ea.exchange,
                ea.name as account_name,
                u.email
            FROM bot_signal_executions bse
            LEFT JOIN bot_signals bs ON bse.signal_id = bs.id
            LEFT JOIN bots b ON bs.bot_id = b.id
            LEFT JOIN bot_subscriptions sub ON bse.subscription_id = sub.id
            LEFT JOIN users u ON sub.user_id = u.id
            LEFT JOIN exchange_accounts ea ON sub.exchange_account_id = ea.id
            ORDER BY bse.created_at DESC
            LIMIT 20
        """)

        return {
            "success": True,
            "data": [dict(e) for e in executions]
        }

    except Exception as e:
        logger.error("Error getting recent signal errors", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
