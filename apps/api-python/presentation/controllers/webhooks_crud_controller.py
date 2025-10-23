"""Webhooks CRUD Controller - API endpoints for managing webhooks"""

from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
import structlog
from datetime import datetime
import uuid

from infrastructure.database.connection_transaction_mode import transaction_db

logger = structlog.get_logger(__name__)

def create_webhooks_crud_router() -> APIRouter:
    """Create and configure the webhooks CRUD router"""
    router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks CRUD"])

    @router.get("")
    async def get_webhooks(request: Request, status: Optional[str] = None):
        """Get all webhooks with optional status filtering"""
        try:
            # Build query with optional filters
            where_conditions = []
            params = []
            param_count = 1
            
            if status:
                where_conditions.append(f"status = ${param_count}")
                params.append(status)
                param_count += 1
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            query = f"""
                SELECT
                    id, name, url_path, status, is_public,
                    market_type,
                    rate_limit_per_minute, rate_limit_per_hour,
                    max_retries, retry_delay_seconds,
                    total_deliveries, successful_deliveries, failed_deliveries,
                    last_delivery_at, last_success_at,
                    auto_pause_on_errors, error_threshold, consecutive_errors,
                    default_margin_usd, default_leverage,
                    default_stop_loss_pct, default_take_profit_pct,
                    user_id, created_at, updated_at
                FROM webhooks
                {where_clause}
                ORDER BY created_at DESC
            """
            
            webhooks = await transaction_db.fetch(query, *params)
            
            webhooks_list = []
            for webhook in webhooks:
                webhooks_list.append({
                    "id": webhook["id"],
                    "name": webhook["name"],
                    "url_path": webhook["url_path"],
                    "status": webhook["status"],
                    "is_public": webhook["is_public"],
                    "market_type": webhook.get("market_type", "spot"),  # Default to spot if column doesn't exist
                    "rate_limit_per_minute": webhook["rate_limit_per_minute"],
                    "rate_limit_per_hour": webhook["rate_limit_per_hour"],
                    "max_retries": webhook["max_retries"],
                    "retry_delay_seconds": webhook["retry_delay_seconds"],
                    "total_deliveries": webhook["total_deliveries"],
                    "successful_deliveries": webhook["successful_deliveries"],
                    "failed_deliveries": webhook["failed_deliveries"],
                    "last_delivery_at": webhook["last_delivery_at"].isoformat() if webhook["last_delivery_at"] else None,
                    "last_success_at": webhook["last_success_at"].isoformat() if webhook["last_success_at"] else None,
                    "auto_pause_on_errors": webhook["auto_pause_on_errors"],
                    "error_threshold": webhook["error_threshold"],
                    "consecutive_errors": webhook["consecutive_errors"],
                    # Trading parameters
                    "default_margin_usd": float(webhook.get("default_margin_usd", 100.0)),
                    "default_leverage": int(webhook.get("default_leverage", 10)),
                    "default_stop_loss_pct": float(webhook.get("default_stop_loss_pct", 3.0)),
                    "default_take_profit_pct": float(webhook.get("default_take_profit_pct", 5.0)),
                    "user_id": webhook["user_id"],
                    "created_at": webhook["created_at"].isoformat() if webhook["created_at"] else None,
                    "updated_at": webhook["updated_at"].isoformat() if webhook["updated_at"] else None,
                    # Calculate success rate
                    "success_rate": round(
                        (webhook["successful_deliveries"] / webhook["total_deliveries"] * 100)
                        if webhook["total_deliveries"] > 0 else 0, 2
                    )
                })
            
            logger.info("Webhooks retrieved", count=len(webhooks_list), status=status)
            return {"success": True, "data": webhooks_list}
            
        except Exception as e:
            logger.error("Error retrieving webhooks", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve webhooks")

    @router.get("/{webhook_id}")
    async def get_webhook(webhook_id: str, request: Request):
        """Get a specific webhook by ID"""
        try:
            webhook = await transaction_db.fetchrow("""
                SELECT
                    id, name, url_path, secret, status, is_public,
                    market_type,
                    rate_limit_per_minute, rate_limit_per_hour,
                    max_retries, retry_delay_seconds,
                    allowed_ips, required_headers, payload_validation_schema,
                    total_deliveries, successful_deliveries, failed_deliveries,
                    last_delivery_at, last_success_at,
                    auto_pause_on_errors, error_threshold, consecutive_errors,
                    default_margin_usd, default_leverage,
                    default_stop_loss_pct, default_take_profit_pct,
                    user_id, created_at, updated_at
                FROM webhooks
                WHERE id = $1
            """, webhook_id)
            
            if not webhook:
                raise HTTPException(status_code=404, detail="Webhook not found")
            
            webhook_data = {
                "id": webhook["id"],
                "name": webhook["name"],
                "url_path": webhook["url_path"],
                "status": webhook["status"],
                "is_public": webhook["is_public"],
                "market_type": webhook.get("market_type", "spot"),  # Default to spot if column doesn't exist
                "rate_limit_per_minute": webhook["rate_limit_per_minute"],
                "rate_limit_per_hour": webhook["rate_limit_per_hour"],
                "max_retries": webhook["max_retries"],
                "retry_delay_seconds": webhook["retry_delay_seconds"],
                "allowed_ips": webhook["allowed_ips"],
                "required_headers": webhook["required_headers"],
                "payload_validation_schema": webhook["payload_validation_schema"],
                "total_deliveries": webhook["total_deliveries"],
                "successful_deliveries": webhook["successful_deliveries"],
                "failed_deliveries": webhook["failed_deliveries"],
                "last_delivery_at": webhook["last_delivery_at"].isoformat() if webhook["last_delivery_at"] else None,
                "last_success_at": webhook["last_success_at"].isoformat() if webhook["last_success_at"] else None,
                "auto_pause_on_errors": webhook["auto_pause_on_errors"],
                "error_threshold": webhook["error_threshold"],
                "consecutive_errors": webhook["consecutive_errors"],
                # Trading parameters
                "default_margin_usd": float(webhook.get("default_margin_usd", 100.0)),
                "default_leverage": int(webhook.get("default_leverage", 10)),
                "default_stop_loss_pct": float(webhook.get("default_stop_loss_pct", 3.0)),
                "default_take_profit_pct": float(webhook.get("default_take_profit_pct", 5.0)),
                "user_id": webhook["user_id"],
                "created_at": webhook["created_at"].isoformat() if webhook["created_at"] else None,
                "updated_at": webhook["updated_at"].isoformat() if webhook["updated_at"] else None,
                "success_rate": round(
                    (webhook["successful_deliveries"] / webhook["total_deliveries"] * 100)
                    if webhook["total_deliveries"] > 0 else 0, 2
                )
            }
            
            logger.info("Webhook retrieved", webhook_id=webhook_id)
            return {"success": True, "data": webhook_data}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error retrieving webhook", webhook_id=webhook_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve webhook")

    @router.post("")
    async def create_webhook(request: Request):
        """Create a new webhook"""
        try:
            body = await request.json()

            # DEBUG: Log received body
            logger.info("📦 Creating webhook - received body", body=body)

            # Validate required fields
            required_fields = ["name", "url_path"]
            for field in required_fields:
                if field not in body:
                    logger.error(f"❌ Missing required field: {field}", body=body)
                    raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
            
            name = body.get("name", "").strip()
            url_path = body.get("url_path", "").strip()
            secret = body.get("secret", str(uuid.uuid4()))  # Generate secret if not provided
            status = body.get("status", "active")
            is_public = body.get("is_public", False)
            market_type = body.get("market_type", "futures")  # ✅ NOVO: market type (spot ou futures)
            rate_limit_per_minute = body.get("rate_limit_per_minute", 60)
            rate_limit_per_hour = body.get("rate_limit_per_hour", 1000)
            max_retries = body.get("max_retries", 3)
            retry_delay_seconds = body.get("retry_delay_seconds", 60)

            # Trading parameters
            default_margin_usd = float(body.get("default_margin_usd", 100.0))
            default_leverage = int(body.get("default_leverage", 10))
            default_stop_loss_pct = float(body.get("default_stop_loss_pct", 3.0))
            default_take_profit_pct = float(body.get("default_take_profit_pct", 5.0))

            # Validations for trading parameters
            logger.info("💰 Validating trading parameters",
                       margin=default_margin_usd, leverage=default_leverage,
                       sl=default_stop_loss_pct, tp=default_take_profit_pct)

            if default_margin_usd < 10.0:
                logger.error(f"❌ Validation failed: Margin {default_margin_usd} < 10")
                raise HTTPException(status_code=400, detail="Margin must be at least $10")
            if default_leverage < 1 or default_leverage > 125:
                logger.error(f"❌ Validation failed: Leverage {default_leverage} not in 1-125")
                raise HTTPException(status_code=400, detail="Leverage must be between 1x and 125x")
            if default_stop_loss_pct < 0.1 or default_stop_loss_pct > 100.0:
                logger.error(f"❌ Validation failed: Stop loss {default_stop_loss_pct} not in 0.1-100")
                raise HTTPException(status_code=400, detail="Stop loss must be between 0.1% and 100%")
            if default_take_profit_pct < 0.1 or default_take_profit_pct > 1000.0:
                logger.error(f"❌ Validation failed: Take profit {default_take_profit_pct} not in 0.1-1000")
                raise HTTPException(status_code=400, detail="Take profit must be between 0.1% and 1000%")

            # Validate market_type
            if market_type not in ["spot", "futures"]:
                raise HTTPException(status_code=400, detail="Invalid market_type. Use: spot or futures")
            
            # Validate status
            if status not in ["active", "paused", "disabled", "error"]:
                raise HTTPException(status_code=400, detail="Invalid status. Use: active, paused, disabled, error")
            
            # Check if url_path already exists
            existing = await transaction_db.fetchrow(
                "SELECT id FROM webhooks WHERE url_path = $1", url_path
            )
            if existing:
                raise HTTPException(status_code=400, detail="URL path already exists")
            
            # TODO: Get user_id from JWT token
            # For now, use a default user (first user in database)
            user = await transaction_db.fetchrow("SELECT id FROM users LIMIT 1")
            if not user:
                raise HTTPException(status_code=400, detail="No users found. Please create a user first.")
            
            user_id = user["id"]
            
            # Create the webhook
            # Try to insert with all parameters including trading parameters
            try:
                webhook_id = await transaction_db.fetchval("""
                    INSERT INTO webhooks (
                        name, url_path, secret, status, is_public,
                        market_type,
                        rate_limit_per_minute, rate_limit_per_hour,
                        max_retries, retry_delay_seconds,
                        auto_pause_on_errors, error_threshold,
                        default_margin_usd, default_leverage,
                        default_stop_loss_pct, default_take_profit_pct,
                        user_id, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, NOW(), NOW())
                    RETURNING id
                """, name, url_path, secret, status, is_public, market_type,
                    rate_limit_per_minute, rate_limit_per_hour,
                    max_retries, retry_delay_seconds, True, 10,
                    default_margin_usd, default_leverage,
                    default_stop_loss_pct, default_take_profit_pct,
                    user_id)
            except Exception as e:
                # Fallback if market_type column doesn't exist yet
                if "market_type" in str(e).lower():
                    logger.warning("market_type column not found, using fallback INSERT")
                    webhook_id = await transaction_db.fetchval("""
                        INSERT INTO webhooks (
                            name, url_path, secret, status, is_public,
                            rate_limit_per_minute, rate_limit_per_hour,
                            max_retries, retry_delay_seconds,
                            auto_pause_on_errors, error_threshold,
                            user_id, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
                        RETURNING id
                    """, name, url_path, secret, status, is_public,
                        rate_limit_per_minute, rate_limit_per_hour,
                        max_retries, retry_delay_seconds, True, 10, user_id)
                else:
                    raise
            
            logger.info("Webhook created", 
                       webhook_id=webhook_id, name=name, url_path=url_path, status=status)
            
            return {
                "success": True,
                "message": "Webhook created successfully",
                "data": {
                    "id": webhook_id,
                    "name": name,
                    "url_path": url_path,
                    "secret": secret,
                    "status": status,
                    "is_public": is_public
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error creating webhook", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to create webhook")

    @router.put("/{webhook_id}")
    async def update_webhook(webhook_id: str, request: Request):
        """Update an existing webhook"""
        try:
            body = await request.json()
            
            # Check if webhook exists
            existing = await transaction_db.fetchrow(
                "SELECT id FROM webhooks WHERE id = $1", webhook_id
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Webhook not found")
            
            # Build update query dynamically
            update_fields = []
            params = []
            param_count = 1
            
            updateable_fields = [
                "name", "status", "is_public", "market_type",
                "rate_limit_per_minute", "rate_limit_per_hour",
                "max_retries", "retry_delay_seconds",
                "auto_pause_on_errors", "error_threshold",
                "default_margin_usd", "default_leverage",
                "default_stop_loss_pct", "default_take_profit_pct"
            ]
            
            for field in updateable_fields:
                if field in body:
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(body[field])
                    param_count += 1
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No valid fields to update")
            
            # Add updated_at
            update_fields.append(f"updated_at = ${param_count}")
            params.append(datetime.utcnow())
            param_count += 1
            
            # Add webhook_id for WHERE clause
            params.append(webhook_id)
            
            query = f"""
                UPDATE webhooks 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
            """
            
            await transaction_db.execute(query, *params)
            
            logger.info("Webhook updated", webhook_id=webhook_id)
            return {"success": True, "message": "Webhook updated successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error updating webhook", webhook_id=webhook_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to update webhook")

    @router.delete("/{webhook_id}")
    async def delete_webhook(webhook_id: str, request: Request):
        """Delete a webhook"""
        try:
            # Check if webhook exists
            existing = await transaction_db.fetchrow(
                "SELECT id FROM webhooks WHERE id = $1", webhook_id
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Webhook not found")

            # Delete the webhook (cascade will handle deliveries)
            await transaction_db.execute(
                "DELETE FROM webhooks WHERE id = $1", webhook_id
            )

            logger.info("Webhook deleted", webhook_id=webhook_id)
            return {"success": True, "message": "Webhook deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error deleting webhook", webhook_id=webhook_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete webhook")

    @router.get("/{webhook_id}/trades")
    async def get_webhook_trades(webhook_id: str, request: Request, limit: int = 50):
        """Get all trades executed by a specific webhook"""
        try:
            # Verificar se webhook existe
            webhook = await transaction_db.fetchrow(
                "SELECT id, name FROM webhooks WHERE id = $1", webhook_id
            )
            if not webhook:
                raise HTTPException(status_code=404, detail="Webhook not found")

            # 🎯 Buscar deliveries deste webhook com seus símbolos
            deliveries = await transaction_db.fetch("""
                SELECT
                    id,
                    payload::jsonb->>'ticker' as ticker,
                    payload::jsonb->>'symbol' as symbol_field
                FROM webhook_deliveries
                WHERE webhook_id = $1::uuid
                ORDER BY created_at DESC
            """, webhook_id)

            # Se não houver deliveries, retornar vazio
            if not deliveries:
                logger.info("No deliveries found for webhook", webhook_id=webhook_id)
                return {
                    "success": True,
                    "data": {
                        "webhook_name": webhook["name"],
                        "trades": [],
                        "total": 0
                    }
                }

            # Extrair símbolos únicos das deliveries
            symbols = set()
            for d in deliveries:
                symbol = d.get('ticker') or d.get('symbol_field')
                if symbol:
                    symbols.add(symbol)

            # Se tiver símbolos, filtrar trades por esses símbolos
            # Caso contrário, buscar por delivery_id
            if symbols:
                # 🎯 Filtrar trades pelos símbolos específicos deste webhook
                symbol_list = list(symbols)
                placeholders = ', '.join([f'${i+2}' for i in range(len(symbol_list))])

                trades = await transaction_db.fetch(f"""
                    SELECT
                        t.id,
                        t.symbol,
                        t.side,
                        t.order_type,
                        t.quantity,
                        t.price,
                        t.filled_quantity,
                        t.average_price,
                        t.status,
                        t.exchange_order_id,
                        t.created_at,
                        t.updated_at,
                        t.error_message
                    FROM trading_orders t
                    WHERE t.symbol = ANY($1::text[])
                    AND t.created_at >= (
                        SELECT MIN(created_at)
                        FROM webhook_deliveries
                        WHERE webhook_id = $2::uuid
                    )
                    ORDER BY t.created_at DESC
                    LIMIT $3
                """, symbol_list, webhook_id, limit)
            else:
                # Fallback: buscar todos os trades recentes
                trades = await transaction_db.fetch("""
                    SELECT
                        t.id,
                        t.symbol,
                        t.side,
                        t.order_type,
                        t.quantity,
                        t.price,
                        t.filled_quantity,
                        t.average_price,
                        t.status,
                        t.exchange_order_id,
                        t.created_at,
                        t.updated_at,
                        t.error_message
                    FROM trading_orders t
                    WHERE t.created_at >= (
                        SELECT MIN(created_at)
                        FROM webhook_deliveries
                        WHERE webhook_id = $1::uuid
                    )
                    ORDER BY t.created_at DESC
                    LIMIT $2
                """, webhook_id, limit)

            # 🎯 Buscar dados REAIS da Binance (posições, P&L, alavancagem)
            binance_positions = {}
            try:
                # Get main account for real-time data
                main_account = await transaction_db.fetchrow("""
                    SELECT id, api_key, secret_key, testnet
                    FROM exchange_accounts
                    WHERE testnet = false AND is_active = true AND is_main = true
                    LIMIT 1
                """)

                if main_account:
                    from infrastructure.exchanges.binance_connector import BinanceConnector
                    from infrastructure.security.encryption_service import EncryptionService

                    # Descriptografar as chaves API do banco de dados
                    encryption_service = EncryptionService()

                    try:
                        api_key = encryption_service.decrypt_string(main_account['api_key']) if main_account['api_key'] else None
                        secret_key = encryption_service.decrypt_string(main_account['secret_key']) if main_account['secret_key'] else None
                        logger.info(f"✅ API keys decrypted successfully for webhook test")
                    except Exception as decrypt_error:
                        logger.error(f"❌ Failed to decrypt API keys: {decrypt_error}")
                        raise HTTPException(
                            status_code=500,
                            detail="Cannot decrypt exchange API keys. Please check your exchange account configuration."
                        )

                    # Validar que as chaves foram descriptografadas
                    if not api_key or not secret_key:
                        logger.error(f"❌ API keys are empty after decryption")
                        raise HTTPException(
                            status_code=500,
                            detail="Exchange API keys are not configured correctly"
                        )

                    connector = BinanceConnector(
                        api_key=api_key,
                        api_secret=secret_key,
                        testnet=False
                    )

                    # Get real-time futures positions
                    positions_result = await connector.get_futures_positions()
                    if positions_result.get('success', True):
                        positions = positions_result.get('positions', [])
                        # Create map: symbol -> position data
                        for pos in positions:
                            symbol = pos.get('symbol')
                            if symbol:
                                binance_positions[symbol] = pos

                    logger.info(f"📊 Fetched {len(binance_positions)} positions from Binance API")

            except Exception as e:
                logger.error(f"Error fetching Binance positions: {e}")
                # Continue without real-time data

            # Build trades list with real Binance data
            trades_list = []
            for trade in trades:
                symbol = trade["symbol"]

                # Get position data from Binance if available
                binance_pos = binance_positions.get(symbol, {})

                # Extract real data from Binance position
                leverage = int(binance_pos.get('leverage', 1))
                position_amt = float(binance_pos.get('positionAmt', 0))
                unrealized_pnl = float(binance_pos.get('unRealizedProfit', 0))
                entry_price = float(binance_pos.get('entryPrice', 0))

                # Determine if position is open (has positionAmt != 0)
                is_open = position_amt != 0

                # Calculate margin in USDT
                # margin = (entry_price * quantity) / leverage
                quantity = float(trade["filled_quantity"]) if trade["filled_quantity"] else float(trade["quantity"])
                price = float(trade["average_price"]) if trade["average_price"] else (float(trade["price"]) if trade["price"] else 0)

                # Use entry_price from Binance if available, otherwise use order price
                calc_price = entry_price if entry_price > 0 else price
                margin_usd = (calc_price * abs(quantity) / leverage) if leverage > 0 else 0

                trades_list.append({
                    "id": trade["id"],
                    "date": trade["created_at"].isoformat() if trade["created_at"] else None,
                    "symbol": symbol,
                    "side": trade["side"],
                    "price": price,
                    "quantity": quantity,
                    "filled_quantity": float(trade["filled_quantity"]) if trade["filled_quantity"] else 0,
                    "leverage": leverage,  # ✅ Real leverage from Binance
                    "margin_usd": round(margin_usd, 2),  # ✅ NEW: Margin in USDT
                    "status": "open" if is_open else "closed",  # ✅ Real status from Binance
                    "order_status": trade["status"],
                    "pnl": round(unrealized_pnl, 2),  # ✅ Real P&L from Binance
                    "exchange_order_id": trade["exchange_order_id"],
                    "error": trade["error_message"]
                })

            logger.info("Webhook trades retrieved", webhook_id=webhook_id, count=len(trades_list))
            return {
                "success": True,
                "data": {
                    "webhook_name": webhook["name"],
                    "trades": trades_list,
                    "total": len(trades_list)
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error retrieving webhook trades", webhook_id=webhook_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve webhook trades")

    return router