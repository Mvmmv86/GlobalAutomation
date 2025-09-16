"""
Sync Controller - Endpoints para sincronização de dados das exchanges
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional, Dict, Any
import structlog
import json
from datetime import datetime, timedelta

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.exchanges.bybit_connector import BybitConnector
from infrastructure.exchanges.bingx_connector import BingXConnector
from infrastructure.exchanges.bitget_connector import BitgetConnector
from infrastructure.security.encryption_service import EncryptionService

logger = structlog.get_logger(__name__)


def create_sync_router() -> APIRouter:
    """Create and configure the sync router"""
    router = APIRouter(prefix="/api/v1/sync", tags=["Sync"])
    encryption_service = EncryptionService()

    def _calculate_unrealized_pnl(position, side):
        """Calculate unrealized PnL based on entry price, mark price, and position size"""
        try:
            entry_price = float(position.get('entryPrice', position.get('averageOpenPrice', 0)))
            mark_price = float(position.get('markPrice', 0))
            size = abs(float(position.get('size', position.get('positionAmt', 0))))
            
            if entry_price <= 0 or mark_price <= 0 or size <= 0:
                return 0.0
            
            # Calculate PnL: (mark_price - entry_price) * size * direction
            price_diff = mark_price - entry_price
            direction = 1 if side.lower() == 'long' else -1
            unrealized_pnl = price_diff * size * direction
            
            return round(unrealized_pnl, 4)
        except (ValueError, TypeError):
            return 0.0

    async def get_exchange_connector(account_id: str):
        """Get exchange connector for account"""
        try:
            # Get account from database
            account = await transaction_db.fetchrow("""
                SELECT id, name, exchange, api_key, secret_key, passphrase, 
                       COALESCE(testnet, false) as testnet,
                       COALESCE(is_active, true) as is_active
                FROM exchange_accounts 
                WHERE id = $1 AND COALESCE(is_active, true) = true
            """, account_id)
            
            if not account:
                raise HTTPException(status_code=404, detail="Exchange account not found")
            
            exchange = account['exchange'].lower()
            api_key = account.get('api_key')
            secret_key = account.get('secret_key')
            passphrase = account.get('passphrase')
            testnet = account.get('testnet', True)

            # Try to decrypt credentials if they exist
            if api_key and secret_key:
                try:
                    api_key = encryption_service.decrypt_string(api_key)
                    secret_key = encryption_service.decrypt_string(secret_key)
                    if passphrase:
                        passphrase = encryption_service.decrypt_string(passphrase)
                except Exception:
                    # Fallback to plain text (backward compatibility)
                    pass

            # Create appropriate connector
            if exchange == 'binance':
                return BinanceConnector(api_key=api_key, api_secret=secret_key, testnet=testnet)
            elif exchange == 'bybit':
                return BybitConnector(api_key=api_key, api_secret=secret_key, testnet=testnet)
            elif exchange == 'bingx':
                return BingXConnector(api_key=api_key, api_secret=secret_key, testnet=testnet)
            elif exchange == 'bitget':
                return BitgetConnector(api_key=api_key, api_secret=secret_key, passphrase=passphrase, testnet=testnet)
            else:
                raise HTTPException(status_code=400, detail=f"Exchange {exchange} not supported")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting exchange connector: {e}")
            raise HTTPException(status_code=500, detail="Failed to create exchange connector")

    @router.post("/orders/{account_id}")
    async def sync_orders(
        account_id: str, 
        request: Request,
        symbol: Optional[str] = None,
        limit: Optional[int] = 100,
        days_back: Optional[int] = 30
    ):
        """Sync orders from exchange to database"""
        try:
            logger.info(f"🔄 Syncing orders for account {account_id}")
            
            # Get connector
            connector = await get_exchange_connector(account_id)
            
            # Calculate time range
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
            
            # Fetch orders from exchange with smaller limit for faster processing
            fetch_limit = min(limit, 50)  # Process max 50 orders at a time
            result = await connector.get_account_orders(
                symbol=symbol,
                limit=fetch_limit,
                start_time=start_time,
                end_time=end_time
            )
            
            if not result.get('success', True):
                return {
                    "success": False,
                    "error": result.get('error', 'Failed to fetch orders'),
                    "synced_count": 0
                }

            orders = result.get('orders', [])
            synced_count = 0
            errors = []

            # Insert/update orders in database (batch processing)
            logger.info(f"Processing {len(orders)} orders...")
            
            for i, order in enumerate(orders):
                try:
                    if i % 10 == 0:  # Log progress every 10 orders
                        logger.info(f"Processing order {i+1}/{len(orders)}")
                    
                    # Check if order already exists
                    existing = await transaction_db.fetchrow("""
                        SELECT id FROM trading_orders 
                        WHERE exchange_order_id = $1 AND exchange = $2
                    """, str(order.get('orderId', order.get('id'))), connector.__class__.__name__.replace('Connector', '').lower())
                    
                    if existing:
                        # Update existing order
                        await transaction_db.execute("""
                            UPDATE trading_orders SET
                                status = $1,
                                filled_quantity = $2,
                                average_price = $3,
                                updated_at = CURRENT_TIMESTAMP,
                                raw_response = $4
                            WHERE id = $5
                        """, 
                        order.get('status', 'unknown').lower(),
                        float(order.get('executedQty', order.get('fillSize', order.get('cumExecQty', 0)))),
                        float(order.get('avgPrice', order.get('fillPrice', order.get('price', 0)))) if order.get('avgPrice', order.get('fillPrice', order.get('price'))) else None,
                        json.dumps(order),
                        existing['id']
                        )
                    else:
                        # Insert new order
                        await transaction_db.execute("""
                            INSERT INTO trading_orders (
                                exchange_order_id, symbol, side, order_type, quantity, price,
                                status, exchange, filled_quantity, average_price,
                                created_at, updated_at, raw_response
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        """,
                        str(order.get('orderId', order.get('id'))),
                        order.get('symbol', '').replace('-', '').replace('_SPBL', ''),
                        order.get('side', '').lower(),
                        order.get('type', order.get('orderType', 'market')).lower(),
                        float(order.get('origQty', order.get('size', order.get('qty', 0)))),
                        float(order.get('price', 0)) if order.get('price') else None,
                        order.get('status', 'unknown').lower(),
                        connector.__class__.__name__.replace('Connector', '').lower(),
                        float(order.get('executedQty', order.get('fillSize', order.get('cumExecQty', 0)))),
                        float(order.get('avgPrice', order.get('fillPrice', order.get('price', 0)))) if order.get('avgPrice', order.get('fillPrice', order.get('price'))) else None,
                        datetime.fromtimestamp(int(order.get('time', order.get('cTime', order.get('updateTime', 0)))) / 1000) if order.get('time', order.get('cTime', order.get('updateTime'))) else datetime.now(),
                        datetime.fromtimestamp(int(order.get('updateTime', order.get('uTime', order.get('time', 0)))) / 1000) if order.get('updateTime', order.get('uTime', order.get('time'))) else datetime.now(),
                        json.dumps(order)
                        )
                    
                    synced_count += 1
                    
                except Exception as e:
                    error_msg = f"Failed to sync order {order.get('orderId', order.get('id'))}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            logger.info(f"✅ Synced {synced_count} orders for account {account_id}")
            
            return {
                "success": True,
                "message": f"Synced {synced_count} orders",
                "synced_count": synced_count,
                "total_orders": len(orders),
                "errors": errors,
                "demo": result.get('demo', False)
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error syncing orders: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to sync orders: {str(e)}")

    @router.post("/trades/{account_id}")
    async def sync_trades(
        account_id: str, 
        request: Request,
        symbol: Optional[str] = None,
        limit: Optional[int] = 100,
        days_back: Optional[int] = 30
    ):
        """Sync trades from exchange to database"""
        try:
            logger.info(f"🔄 Syncing trades for account {account_id}")
            
            connector = await get_exchange_connector(account_id)
            
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
            
            result = await connector.get_account_trades(
                symbol=symbol,
                limit=limit,
                start_time=start_time,
                end_time=end_time
            )
            
            if not result.get('success', True):
                return {
                    "success": False,
                    "error": result.get('error', 'Failed to fetch trades'),
                    "synced_count": 0
                }

            trades = result.get('trades', [])
            synced_count = 0
            errors = []

            # Note: We'll need to create a trades table for this
            # For now, just return the count
            logger.info(f"📊 Found {len(trades)} trades (not stored yet - need trades table)")
            
            return {
                "success": True,
                "message": f"Found {len(trades)} trades (storage pending - need trades table)",
                "synced_count": 0,
                "total_trades": len(trades),
                "trades_preview": trades[:5] if trades else [],
                "demo": result.get('demo', False)
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error syncing trades: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to sync trades: {str(e)}")

    @router.post("/balances/{account_id}")
    async def sync_balances(account_id: str, request: Request):
        """Sync balances from exchange"""
        try:
            logger.info(f"💰 Syncing balances for account {account_id}")
            
            connector = await get_exchange_connector(account_id)
            result = await connector.get_account_balances()
            
            if not result.get('success', True):
                return {
                    "success": False,
                    "error": result.get('error', 'Failed to fetch balances')
                }

            balances = result.get('balances', [])
            
            # Store balances in database (we'll need to create balances table)
            # For now, just return the balances
            
            logger.info(f"💰 Found {len(balances)} balances")
            
            return {
                "success": True,
                "message": f"Found {len(balances)} balances",
                "balances": balances,
                "demo": result.get('demo', False)
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error syncing balances: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to sync balances: {str(e)}")

    @router.post("/positions/{account_id}")
    async def sync_positions(account_id: str, request: Request):
        """Sync futures positions from exchange"""
        try:
            logger.info(f"📊 Syncing positions for account {account_id}")
            
            connector = await get_exchange_connector(account_id)
            result = await connector.get_futures_positions()
            
            if not result.get('success', True):
                return {
                    "success": False,
                    "error": result.get('error', 'Failed to fetch positions')
                }

            positions = result.get('positions', [])
            
            # Store positions in database (positions table already exists)
            synced_count = 0
            errors = []
            
            for position in positions:
                try:
                    # Insert/update position in database
                    # This is a simplified version - you may need to adjust based on your positions table schema
                    # Check if position already exists
                    existing = await transaction_db.fetchrow("""
                        SELECT id FROM positions 
                        WHERE symbol = $1 AND exchange_account_id = $2
                    """, position.get('symbol', '').replace('-', ''), account_id)
                    
                    if existing:
                        # Update existing position
                        await transaction_db.execute("""
                            UPDATE positions SET
                                side = $1, size = $2, entry_price = $3, mark_price = $4,
                                unrealized_pnl = $5, leverage = $6, liquidation_price = $7,
                                last_update_at = $8, updated_at = $9
                            WHERE id = $10
                        """,
                        'long' if float(position.get('positionAmt', position.get('size', 0))) > 0 else 'short',
                        abs(float(position.get('size', position.get('positionAmt', 0)))),
                        float(position.get('entryPrice', position.get('averageOpenPrice', 0))) if position.get('entryPrice', position.get('averageOpenPrice')) else 0,
                        float(position.get('markPrice', 0)) if position.get('markPrice') else None,
                        # Calculate unrealized PnL = (mark_price - entry_price) * size * (1 if long else -1)
                        _calculate_unrealized_pnl(position, 'long' if float(position.get('positionAmt', position.get('size', 0))) > 0 else 'short'),
                        float(position.get('leverage', '1')),
                        float(position.get('liquidationPrice', 0)) if position.get('liquidationPrice') else None,
                        datetime.now(),  # last_update_at
                        datetime.now(),  # updated_at
                        existing['id']
                        )
                    else:
                        # Insert new position
                        await transaction_db.execute("""
                            INSERT INTO positions (
                                symbol, side, size, entry_price, mark_price,
                                unrealized_pnl, realized_pnl, initial_margin, maintenance_margin,
                                leverage, liquidation_price, bankruptcy_price, opened_at, 
                                last_update_at, total_fees, funding_fees, exchange_account_id,
                                status, created_at, updated_at
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
                        """,
                    position.get('symbol', '').replace('-', ''),
                    'long' if float(position.get('positionAmt', position.get('size', 0))) > 0 else 'short',
                    abs(float(position.get('size', position.get('positionAmt', 0)))),
                    float(position.get('entryPrice', position.get('averageOpenPrice', 0))) if position.get('entryPrice', position.get('averageOpenPrice')) else 0,
                    float(position.get('markPrice', 0)) if position.get('markPrice') else None,
                    _calculate_unrealized_pnl(position, 'long' if float(position.get('positionAmt', position.get('size', 0))) > 0 else 'short'),
                    0.0,  # realized_pnl
                    0.0,  # initial_margin  
                    0.0,  # maintenance_margin
                    float(position.get('leverage', '1')),
                    float(position.get('liquidationPrice', 0)) if position.get('liquidationPrice') else None,
                    None,  # bankruptcy_price
                    datetime.now(),  # opened_at
                    datetime.now(),  # last_update_at 
                    0.0,  # total_fees
                    0.0,  # funding_fees
                    account_id,
                    'open',  # status
                    datetime.now(),  # created_at
                    datetime.now()   # updated_at
                    )
                    synced_count += 1
                except Exception as e:
                    error_msg = f"Failed to sync position {position.get('symbol')}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            logger.info(f"📊 Synced {synced_count} positions")
            
            return {
                "success": True,
                "message": f"Synced {synced_count} positions",
                "synced_count": synced_count,
                "total_positions": len(positions),
                "errors": errors,
                "demo": result.get('demo', False)
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error syncing positions: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to sync positions: {str(e)}")

    @router.post("/all/{account_id}")
    async def sync_all(account_id: str, request: Request):
        """Sync all data (orders, balances, positions) from exchange"""
        try:
            logger.info(f"🔄 Full sync for account {account_id}")
            
            results = {}
            
            # Sync orders
            try:
                orders_result = await sync_orders(account_id, request)
                results['orders'] = orders_result
            except Exception as e:
                results['orders'] = {"success": False, "error": str(e)}
            
            # Sync balances
            try:
                balances_result = await sync_balances(account_id, request)
                results['balances'] = balances_result
            except Exception as e:
                results['balances'] = {"success": False, "error": str(e)}
            
            # Sync positions
            try:
                positions_result = await sync_positions(account_id, request)
                results['positions'] = positions_result
            except Exception as e:
                results['positions'] = {"success": False, "error": str(e)}
            
            success_count = sum(1 for r in results.values() if r.get('success', False))
            
            logger.info(f"✅ Full sync completed: {success_count}/3 successful")
            
            return {
                "success": success_count > 0,
                "message": f"Full sync completed: {success_count}/3 successful",
                "results": results
            }

        except Exception as e:
            logger.error(f"Error in full sync: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to perform full sync: {str(e)}")

    @router.get("/test/{account_id}")
    async def test_connection(account_id: str, request: Request):
        """Test connection to exchange"""
        try:
            connector = await get_exchange_connector(account_id)
            result = await connector.test_connection()
            
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error testing connection: {e}")
            raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")

    return router