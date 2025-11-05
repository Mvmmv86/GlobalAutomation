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
from infrastructure.pricing.binance_price_service import BinancePriceService

logger = structlog.get_logger(__name__)


def create_sync_router() -> APIRouter:
    """Create and configure the sync router"""
    router = APIRouter(prefix="/api/v1/sync", tags=["Sync"])

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

            # API keys are stored in plain text (Supabase encryption at rest)
            # No decryption needed

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
        """Sync balances from exchange (SPOT + FUTURES)"""
        try:
            logger.info(f"💰 Syncing balances for account {account_id}")

            connector = await get_exchange_connector(account_id)

            # Get SPOT balances
            spot_result = await connector.get_account_info()
            spot_balances = spot_result.get('balances', []) if spot_result.get('success', True) else []

            # Get FUTURES balances (exchange-specific parsing)
            futures_result = await connector.get_futures_account()
            futures_balances = []

            if futures_result.get('success', True):
                # Binance format: has 'account' wrapper with 'assets' array
                if 'account' in futures_result:
                    futures_account = futures_result.get('account', {})
                    # Extract assets from futures account
                    for asset_data in futures_account.get('assets', []):
                        wallet_balance = float(asset_data.get('walletBalance', 0))
                        available_balance = float(asset_data.get('availableBalance', 0))
                        if wallet_balance > 0:
                            futures_balances.append({
                                'asset': asset_data.get('asset'),
                                'free': available_balance,
                                'locked': wallet_balance - available_balance,
                                'total': wallet_balance
                            })
                # BingX format: has 'balance' object directly
                elif 'balance' in futures_result:
                    balance_data = futures_result.get('balance', {})
                    logger.info(f"🐛 DEBUG BingX balance_data: {balance_data}")

                    # BingX returns: {"balance": {"asset": "USDT", "balance": "16.69", "availableMargin": "16.69", ...}}
                    if isinstance(balance_data, dict):
                        asset = balance_data.get('asset', 'USDT')
                        balance_str = balance_data.get('balance', '0')
                        equity_str = balance_data.get('equity', balance_str)
                        available_str = balance_data.get('availableMargin', balance_str)

                        # Convert strings to floats
                        try:
                            balance = float(balance_str)
                            equity = float(equity_str)
                            available = float(available_str)
                        except (ValueError, TypeError) as e:
                            logger.error(f"❌ Error converting BingX futures values: balance={balance_str}, equity={equity_str}, available={available_str}, error={e}")
                            balance = 0.0
                            equity = 0.0
                            available = 0.0

                        if balance > 0:
                            futures_balances.append({
                                'asset': asset,
                                'free': available,
                                'locked': balance - available,
                                'total': balance
                            })
                            logger.info(f"✅ BingX FUTURES: {asset} = {balance} (available={available})")
                    else:
                        logger.error(f"❌ BingX balance_data is not a dict: {type(balance_data)}")

            # Combine all balances
            all_balances = [
                *[(balance, 'SPOT') for balance in spot_balances],
                *[(balance, 'FUTURES') for balance in futures_balances]
            ]

            # Store balances in database
            synced_count = 0
            errors = []

            # Track which assets we've seen from exchange for cleanup
            exchange_assets = set()
            for balance_data, account_type in all_balances:
                asset = balance_data.get('asset')
                if asset:
                    exchange_assets.add((asset, account_type))

            # Initialize real-time price service (use Binance for prices across all exchanges)
            # Note: We use Binance prices as the reference market price for all exchanges
            price_service = BinancePriceService(testnet=False)  # Always use real prices

            # Get real-time prices from Binance API
            logger.info("🔄 Fetching real-time prices from Binance (reference market)...")
            real_prices = await price_service.get_all_ticker_prices()

            if not real_prices:
                logger.error("❌ Failed to fetch real prices, sync cancelled")
                raise HTTPException(status_code=500, detail="Failed to fetch price data from Binance")

            logger.info(f"✅ Fetched {len(real_prices)} real prices from Binance")

            for balance_data, account_type in all_balances:
                try:
                    asset = balance_data.get('asset')

                    if account_type == 'SPOT':
                        free = float(balance_data.get('free', 0))
                        locked = float(balance_data.get('locked', 0))
                        total = free + locked
                    else:  # FUTURES
                        free = float(balance_data.get('free', 0))
                        locked = float(balance_data.get('locked', 0))
                        total = float(balance_data.get('total', free + locked))

                    # Debug: log all balances before filtering
                    logger.info(f"🔍 Processing {account_type} balance: {asset} = {total} (raw data: {balance_data})")

                    if total <= 0:
                        logger.info(f"⏭️ Skipping {asset} - total balance <= 0")
                        continue

                    # Calculate USD value using real-time prices
                    usd_value = await price_service.calculate_usdt_value(asset, total, real_prices)

                    # Check if balance already exists for this account type
                    existing = await transaction_db.fetchrow("""
                        SELECT id FROM exchange_account_balances
                        WHERE exchange_account_id = $1 AND asset = $2 AND account_type = $3
                    """, account_id, asset, account_type)

                    if existing:
                        # Update existing balance
                        logger.info(f"🔄 Updating existing balance for {asset} ({account_type})")
                        await transaction_db.execute("""
                            UPDATE exchange_account_balances SET
                                free_balance = $1,
                                locked_balance = $2,
                                total_balance = $3,
                                usd_value = $4
                            WHERE id = $5
                        """, free, locked, total, usd_value, existing['id'])
                        logger.info(f"✅ Updated balance for {asset} ({account_type})")
                    else:
                        # Insert new balance
                        logger.info(f"➕ Inserting new balance for {asset} ({account_type})")
                        await transaction_db.execute("""
                            INSERT INTO exchange_account_balances (
                                exchange_account_id, asset, free_balance, locked_balance,
                                total_balance, usd_value, account_type
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """, account_id, asset, free, locked, total, usd_value, account_type)
                        logger.info(f"✅ Inserted balance for {asset} ({account_type})")

                    synced_count += 1
                    logger.info(f"💰 Synced {account_type} balance: {asset} = {total} (${usd_value:.2f}) for account {account_id}")

                except Exception as e:
                    error_msg = f"Failed to sync {account_type} balance {balance_data.get('asset')}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # Clean up old balances that no longer exist in exchange
            logger.info("🧹 Cleaning up old balances not found in exchange...")

            # Get all existing assets in database for this account
            existing_assets = await transaction_db.fetch("""
                SELECT asset, account_type FROM exchange_account_balances
                WHERE exchange_account_id = $1
            """, account_id)

            # Remove assets that are no longer in exchange
            removed_count = 0
            for db_asset in existing_assets:
                asset_key = (db_asset['asset'], db_asset['account_type'])
                if asset_key not in exchange_assets:
                    # This asset is in DB but not in exchange anymore - remove it
                    await transaction_db.execute("""
                        DELETE FROM exchange_account_balances
                        WHERE exchange_account_id = $1 AND asset = $2 AND account_type = $3
                    """, account_id, db_asset['asset'], db_asset['account_type'])

                    removed_count += 1
                    logger.info(f"🗑️ Removed old balance: {db_asset['asset']} ({db_asset['account_type']})")

            if removed_count > 0:
                logger.info(f"🧹 Cleaned up {removed_count} old balances")
            else:
                logger.info("✅ No old balances to clean up")

            logger.info(f"💰 Synced {synced_count} balances to database (SPOT + FUTURES)")

            return {
                "success": True,
                "message": f"Synced {synced_count} balances to database",
                "synced_count": synced_count,
                "total_balances": len(all_balances),
                "spot_balances": len(spot_balances),
                "futures_balances": len(futures_balances),
                "errors": errors,
                "demo": futures_result.get('demo', False)
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error syncing balances: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to sync balances: {str(e)}")

    @router.get("/balances/debug/{account_id}")
    async def debug_balances_sync(account_id: str):
        """Debug balances sync to see what's being returned by Binance"""
        try:
            connector = await get_exchange_connector(account_id)

            # Get SPOT data
            spot_result = await connector.get_account_info()

            # Get FUTURES data
            futures_result = await connector.get_futures_account()

            return {
                "account_id": account_id,
                "spot_api_response": spot_result,
                "futures_api_response": futures_result,
                "spot_success": spot_result.get('success', False),
                "futures_success": futures_result.get('success', False),
                "spot_balances_count": len(spot_result.get('balances', [])) if spot_result.get('success') else 0,
                "futures_assets_count": len(futures_result.get('account', {}).get('assets', [])) if futures_result.get('success') else 0
            }

        except Exception as e:
            return {"error": str(e)}

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

            # 🔍 DEBUG: Log detalhado das posições retornadas pela API
            logger.info(f"🔍 DEBUG POSITIONS: Total retornado = {len(positions)}")
            for i, pos in enumerate(positions):
                symbol = pos.get('symbol', 'N/A')
                amount = pos.get('positionAmt', pos.get('size', '0'))
                logger.info(f"   [{i+1}] {symbol}: amount={amount}")
                # Log ALL fields from first position to see structure
                if i == 0:
                    logger.info(f"   📋 CAMPOS DA POSIÇÃO: {list(pos.keys())}")
                    for key, value in pos.items():
                        logger.info(f"      {key} = {value}")

            # Track which symbols we've seen from Binance for cleanup
            binance_symbols = set()
            for position in positions:
                symbol = position.get('symbol', '').replace('-', '')
                if symbol:
                    binance_symbols.add(symbol)

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
                        # Update existing position (set status='open' since API returned it)
                        # BingX FUTURES uses: avgPrice, positionAmt, unrealizedProfit
                        # Binance FUTURES uses: entryPrice, positionAmt, unrealizedProfit
                        entry_price = float(position.get('avgPrice', position.get('entryPrice', position.get('averageOpenPrice', 0))))
                        size_amt = float(position.get('positionAmt', position.get('size', 0)))
                        side = 'long' if size_amt > 0 else 'short'
                        mark_price = float(position.get('markPrice', 0)) if position.get('markPrice') else None
                        unrealized_pnl = float(position.get('unrealizedProfit', position.get('unRealizedProfit', 0)))

                        await transaction_db.execute("""
                            UPDATE positions SET
                                side = $1, size = $2, entry_price = $3, mark_price = $4,
                                unrealized_pnl = $5, leverage = $6, liquidation_price = $7,
                                last_update_at = $8, updated_at = $9, status = 'open'
                            WHERE id = $10
                        """,
                        side,
                        abs(size_amt),
                        entry_price,
                        mark_price,
                        unrealized_pnl,
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

            # Clean up old positions that no longer exist in Binance
            # 🚨 CONSERVATIVE CLEANUP: Only close positions if they haven't been seen
            # in multiple consecutive syncs to avoid false positives due to API issues
            logger.info("🧹 Checking for positions that may need cleanup...")

            # Get all existing positions in database for this account
            existing_positions = await transaction_db.fetch("""
                SELECT symbol, updated_at FROM positions
                WHERE exchange_account_id = $1 AND status = 'open'
            """, account_id)

            # Only consider closing positions that:
            # 1. Are not in current Binance response
            # 2. Haven't been updated in the last 5 minutes (multiple sync cycles)
            closed_count = 0
            from datetime import timezone
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)

            for db_position in existing_positions:
                if db_position['symbol'] not in binance_symbols:
                    # Check if position is old enough to be considered stale
                    if db_position['updated_at'] < cutoff_time:
                        # This position hasn't been seen for a while - close it
                        await transaction_db.execute("""
                            UPDATE positions SET
                                status = 'closed',
                                updated_at = $1
                            WHERE exchange_account_id = $2 AND symbol = $3 AND status = 'open'
                        """, datetime.now(timezone.utc), account_id, db_position['symbol'])

                        closed_count += 1
                        logger.info(f"🗑️ Closed stale position: {db_position['symbol']} (not updated for >5min)")
                    else:
                        logger.info(f"⏳ Position {db_position['symbol']} not in Binance response but recently updated - keeping open")

            if closed_count > 0:
                logger.info(f"🧹 Closed {closed_count} stale positions")
            else:
                logger.info("✅ No stale positions found to close")

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

    @router.get("/check-database/{account_id}")
    async def check_database_balances(account_id: str):
        """Check what's actually in the database"""
        try:
            # Count total balances for this account
            total_count = await transaction_db.fetchval("""
                SELECT COUNT(*) FROM exchange_account_balances
                WHERE exchange_account_id = $1
            """, account_id)

            # Count by account type
            spot_count = await transaction_db.fetchval("""
                SELECT COUNT(*) FROM exchange_account_balances
                WHERE exchange_account_id = $1 AND account_type = 'SPOT'
            """, account_id)

            futures_count = await transaction_db.fetchval("""
                SELECT COUNT(*) FROM exchange_account_balances
                WHERE exchange_account_id = $1 AND account_type = 'FUTURES'
            """, account_id)

            # Get all balances
            all_balances = await transaction_db.fetch("""
                SELECT account_type, asset, total_balance, usd_value, free_balance, locked_balance, created_at
                FROM exchange_account_balances
                WHERE exchange_account_id = $1
                ORDER BY account_type, usd_value DESC
            """, account_id)

            # Sum USD values
            total_usd = await transaction_db.fetchval("""
                SELECT COALESCE(SUM(usd_value), 0) FROM exchange_account_balances
                WHERE exchange_account_id = $1
            """, account_id)

            spot_usd = await transaction_db.fetchval("""
                SELECT COALESCE(SUM(usd_value), 0) FROM exchange_account_balances
                WHERE exchange_account_id = $1 AND account_type = 'SPOT'
            """, account_id)

            futures_usd = await transaction_db.fetchval("""
                SELECT COALESCE(SUM(usd_value), 0) FROM exchange_account_balances
                WHERE exchange_account_id = $1 AND account_type = 'FUTURES'
            """, account_id)

            return {
                "account_id": account_id,
                "total_balances": total_count,
                "spot_balances": spot_count,
                "futures_balances": futures_count,
                "total_usd": float(total_usd),
                "spot_usd": float(spot_usd),
                "futures_usd": float(futures_usd),
                "balances": [dict(b) for b in all_balances]
            }

        except Exception as e:
            return {"error": str(e)}

    @router.post("/spot-orders-history/{account_id}")
    async def sync_spot_orders_history(
        account_id: str,
        request: Request,
        days_back: Optional[int] = 90,
        min_usd_value: Optional[float] = 1.0
    ):
        """
        Sync historical SPOT orders from exchange for P&L calculation
        - Only imports BUY orders that are FILLED (needed for average cost basis)
        - Filters out orders with value < $1 USD (dust)
        - Saves to 'orders' table (NOT 'trading_orders')
        - Multi-exchange support (Binance, BingX, Bybit, Bitget)
        """
        try:
            logger.info(f"📦 Syncing SPOT order history for account {account_id} (last {days_back} days, min ${min_usd_value})")

            # Get account info from database
            account = await transaction_db.fetchrow("""
                SELECT id, name, exchange, api_key, secret_key, testnet
                FROM exchange_accounts
                WHERE id = $1
            """, account_id)

            if not account:
                raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

            exchange_name = account['exchange'].upper()
            logger.info(f"🏦 Exchange: {exchange_name}")

            # Create connector for the exchange
            connector = await get_exchange_connector(account_id)

            # Calculate time range (last N days)
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)

            # Fetch orders from exchange
            result = await connector.get_account_orders(
                symbol=None,  # All symbols
                limit=500,    # Max orders
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
            logger.info(f"📊 Fetched {len(orders)} orders from {exchange_name}")

            # Filter: Only BUY + FILLED orders
            buy_filled_orders = []
            for order in orders:
                side = order.get('side', '').upper()
                status = order.get('status', '').upper()

                # Check if it's a BUY order and FILLED
                if side == 'BUY' and status == 'FILLED':
                    buy_filled_orders.append(order)

            logger.info(f"✅ Filtered to {len(buy_filled_orders)} BUY+FILLED orders")

            # Filter: Minimum USD value ($1+)
            price_service = BinancePriceService(testnet=False)
            real_prices = await price_service.get_all_ticker_prices()

            filtered_orders = []
            for order in buy_filled_orders:
                symbol = order.get('symbol', '').replace('-', '').replace('_SPBL', '')
                quantity = float(order.get('executedQty', order.get('fillSize', order.get('cumExecQty', 0))))
                price = float(order.get('avgPrice', order.get('fillPrice', order.get('price', 0)))) if order.get('avgPrice', order.get('fillPrice', order.get('price'))) else 0

                # Calculate USD value of order
                usd_value = quantity * price

                # Only keep orders >= min_usd_value
                if usd_value >= min_usd_value:
                    filtered_orders.append(order)

            logger.info(f"💵 Filtered to {len(filtered_orders)} orders with value >= ${min_usd_value}")

            # Save to 'orders' table (NOT 'trading_orders')
            synced_count = 0
            skipped_count = 0
            errors = []

            for order in filtered_orders:
                try:
                    # Extract order data (exchange-specific parsing)
                    order_id = str(order.get('orderId', order.get('id', order.get('order_id'))))
                    symbol = order.get('symbol', '').replace('-', '').replace('_SPBL', '')
                    side = order.get('side', '').lower()
                    order_type = order.get('type', order.get('orderType', 'market')).lower()
                    quantity = float(order.get('origQty', order.get('size', order.get('qty', 0))))
                    price = float(order.get('price', 0)) if order.get('price') else None
                    filled_quantity = float(order.get('executedQty', order.get('fillSize', order.get('cumExecQty', 0))))
                    average_price = float(order.get('avgPrice', order.get('fillPrice', order.get('price', 0)))) if order.get('avgPrice', order.get('fillPrice', order.get('price'))) else None

                    # Timestamps
                    created_timestamp = int(order.get('time', order.get('cTime', order.get('createTime', 0))))
                    updated_timestamp = int(order.get('updateTime', order.get('uTime', order.get('time', 0))))

                    created_at = datetime.fromtimestamp(created_timestamp / 1000) if created_timestamp else datetime.now()
                    updated_at = datetime.fromtimestamp(updated_timestamp / 1000) if updated_timestamp else datetime.now()

                    # Generate client_order_id (unique identifier)
                    import uuid
                    client_order_id = f"{exchange_name}_{order_id}_{uuid.uuid4().hex[:8]}"

                    # Check if order already exists in 'orders' table
                    existing = await transaction_db.fetchrow("""
                        SELECT id FROM orders
                        WHERE external_id = $1 AND exchange_account_id = $2
                    """, order_id, account_id)

                    if existing:
                        logger.debug(f"⏭️  Order {order_id} already exists, skipping")
                        skipped_count += 1
                        continue

                    # Insert into 'orders' table
                    await transaction_db.execute("""
                        INSERT INTO orders (
                            external_id, client_order_id, symbol, side, type, status,
                            quantity, price, filled_quantity, average_fill_price,
                            submitted_at, completed_at, exchange_account_id,
                            source, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                    """,
                    order_id,                      # external_id
                    client_order_id,               # client_order_id
                    symbol,                        # symbol
                    side,                          # side (buy)
                    order_type,                    # type
                    'filled',                      # status
                    quantity,                      # quantity
                    price,                         # price
                    filled_quantity,               # filled_quantity
                    average_price,                 # average_fill_price
                    created_at,                    # submitted_at
                    updated_at,                    # completed_at
                    account_id,                    # exchange_account_id
                    'history_import',              # source
                    created_at,                    # created_at
                    updated_at                     # updated_at
                    )

                    synced_count += 1
                    logger.debug(f"✅ Imported order {order_id}: {symbol} {quantity} @ ${average_price}")

                except Exception as e:
                    error_msg = f"Failed to import order {order.get('orderId', order.get('id'))}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            logger.info(f"🎉 SPOT order history sync completed: {synced_count} imported, {skipped_count} skipped")

            return {
                "success": True,
                "message": f"Synced {synced_count} historical SPOT orders (BUY+FILLED, value >= ${min_usd_value})",
                "synced_count": synced_count,
                "skipped_count": skipped_count,
                "total_fetched": len(orders),
                "buy_filled_count": len(buy_filled_orders),
                "filtered_count": len(filtered_orders),
                "errors": errors[:10],  # Limit to first 10 errors
                "exchange": exchange_name,
                "days_back": days_back,
                "min_usd_value": min_usd_value
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error syncing SPOT order history: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to sync SPOT order history: {str(e)}")

    return router