"""Dashboard Controller - API endpoints for home dashboard metrics"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import structlog
from datetime import datetime, timedelta
from decimal import Decimal

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.cache import get_positions_cache
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.exchanges.bybit_connector import BybitConnector
from infrastructure.exchanges.bingx_connector import BingXConnector
from infrastructure.exchanges.bitget_connector import BitgetConnector
from infrastructure.pricing.binance_price_service import BinancePriceService

logger = structlog.get_logger(__name__)
cache = get_positions_cache()

def create_dashboard_router() -> APIRouter:
    """Create and configure the dashboard router"""
    router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])

    @router.get("/metrics")
    async def get_dashboard_metrics(request: Request):
        """Get comprehensive dashboard metrics for home page"""
        try:
            logger.info("🏠 Getting dashboard metrics")
            
            # Calculate date range for last 7 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # Get P&L from positions (futures/spot)
            positions_pnl = await transaction_db.fetchrow("""
                SELECT 
                    COALESCE(SUM(p.unrealized_pnl), 0) as total_unrealized_pnl,
                    COALESCE(SUM(p.realized_pnl), 0) as total_realized_pnl,
                    COUNT(*) FILTER (WHERE p.status = 'open') as open_positions,
                    COUNT(*) FILTER (WHERE p.status = 'closed') as closed_positions,
                    COALESCE(SUM(p.total_fees), 0) as total_fees_paid
                FROM positions p
                LEFT JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE ea.testnet = false 
                  AND ea.is_active = true
                  AND p.updated_at >= $1
            """, start_date)
            
            # Get P&L from completed orders (last 7 days)
            orders_pnl = await transaction_db.fetchrow("""
                SELECT 
                    COUNT(*) as total_orders,
                    COUNT(*) FILTER (WHERE o.status IN ('filled', 'partially_filled')) as executed_orders,
                    COUNT(*) FILTER (WHERE o.status = 'canceled') as canceled_orders,
                    COALESCE(SUM(o.fees_paid), 0) as total_fees_from_orders,
                    COALESCE(SUM(
                        CASE 
                            WHEN o.side = 'sell' THEN (o.average_fill_price * o.filled_quantity) 
                            ELSE -(o.average_fill_price * o.filled_quantity)
                        END
                    ), 0) as orders_flow
                FROM orders o
                LEFT JOIN exchange_accounts ea ON o.exchange_account_id = ea.id
                WHERE ea.testnet = false 
                  AND ea.is_active = true
                  AND o.updated_at >= $1
                  AND o.status IN ('filled', 'partially_filled')
            """, start_date)
            
            # Get active accounts summary
            accounts_summary = await transaction_db.fetchrow("""
                SELECT 
                    COUNT(*) as total_accounts,
                    COUNT(*) FILTER (WHERE ea.is_active = true) as active_accounts
                FROM exchange_accounts ea
                WHERE ea.testnet = false
            """)
            
            # Calculate total P&L (7 days)
            total_unrealized_pnl = float(positions_pnl["total_unrealized_pnl"] or 0)
            total_realized_pnl = float(positions_pnl["total_realized_pnl"] or 0)
            total_pnl_7d = total_unrealized_pnl + total_realized_pnl
            
            # Get best and worst performing positions
            best_positions = await transaction_db.fetch("""
                SELECT 
                    p.symbol, p.side, p.unrealized_pnl, p.realized_pnl,
                    (p.unrealized_pnl + p.realized_pnl) as total_pnl,
                    ea.name as exchange_name
                FROM positions p
                LEFT JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE ea.testnet = false 
                  AND ea.is_active = true
                  AND p.updated_at >= $1
                  AND (p.unrealized_pnl + p.realized_pnl) != 0
                ORDER BY (p.unrealized_pnl + p.realized_pnl) DESC
                LIMIT 3
            """, start_date)
            
            worst_positions = await transaction_db.fetch("""
                SELECT 
                    p.symbol, p.side, p.unrealized_pnl, p.realized_pnl,
                    (p.unrealized_pnl + p.realized_pnl) as total_pnl,
                    ea.name as exchange_name
                FROM positions p
                LEFT JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE ea.testnet = false 
                  AND ea.is_active = true
                  AND p.updated_at >= $1
                  AND (p.unrealized_pnl + p.realized_pnl) != 0
                ORDER BY (p.unrealized_pnl + p.realized_pnl) ASC
                LIMIT 3
            """, start_date)
            
            # Build response
            metrics = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": 7
                },
                "pnl_summary": {
                    "total_pnl_7d": total_pnl_7d,
                    "unrealized_pnl": total_unrealized_pnl,
                    "realized_pnl": total_realized_pnl,
                    "total_fees_paid": float(positions_pnl["total_fees_paid"] or 0) + float(orders_pnl["total_fees_from_orders"] or 0),
                    "net_pnl": total_pnl_7d - (float(positions_pnl["total_fees_paid"] or 0) + float(orders_pnl["total_fees_from_orders"] or 0))
                },
                "positions_summary": {
                    "open_positions": positions_pnl["open_positions"],
                    "closed_positions": positions_pnl["closed_positions"],
                    "total_positions": positions_pnl["open_positions"] + positions_pnl["closed_positions"]
                },
                "orders_summary": {
                    "total_orders": orders_pnl["total_orders"],
                    "executed_orders": orders_pnl["executed_orders"],
                    "canceled_orders": orders_pnl["canceled_orders"],
                    "execution_rate": round((orders_pnl["executed_orders"] / max(orders_pnl["total_orders"], 1)) * 100, 2)
                },
                "accounts_summary": {
                    "total_accounts": accounts_summary["total_accounts"],
                    "active_accounts": accounts_summary["active_accounts"]
                },
                "top_performers": [
                    {
                        "symbol": pos["symbol"],
                        "side": pos["side"],
                        "pnl": float(pos["total_pnl"]),
                        "exchange": pos["exchange_name"]
                    }
                    for pos in best_positions
                ],
                "worst_performers": [
                    {
                        "symbol": pos["symbol"],
                        "side": pos["side"],
                        "pnl": float(pos["total_pnl"]),
                        "exchange": pos["exchange_name"]
                    }
                    for pos in worst_positions
                ]
            }
            
            logger.info(f"📊 Dashboard metrics calculated", 
                       total_pnl_7d=total_pnl_7d, 
                       open_positions=positions_pnl["open_positions"],
                       total_orders=orders_pnl["total_orders"])
            
            return {"success": True, "data": metrics}
            
        except Exception as e:
            logger.error("Error getting dashboard metrics", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to get dashboard metrics")

    @router.get("/pnl-chart")
    async def get_pnl_chart(request: Request, days: int = 7):
        """Get P&L chart data for specified period"""
        try:
            logger.info(f"📈 Getting P&L chart for {days} days")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get daily P&L aggregation
            daily_pnl = await transaction_db.fetch("""
                SELECT 
                    DATE(p.updated_at) as date,
                    COALESCE(SUM(p.unrealized_pnl + p.realized_pnl), 0) as daily_pnl,
                    COUNT(*) as positions_count
                FROM positions p
                LEFT JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE ea.testnet = false 
                  AND ea.is_active = true
                  AND p.updated_at >= $1
                GROUP BY DATE(p.updated_at)
                ORDER BY DATE(p.updated_at) DESC
                LIMIT $2
            """, start_date, days)
            
            chart_data = [
                {
                    "date": row["date"].isoformat(),
                    "pnl": float(row["daily_pnl"]),
                    "positions": row["positions_count"]
                }
                for row in daily_pnl
            ]
            
            return {"success": True, "data": chart_data}

        except Exception as e:
            logger.error("Error getting P&L chart", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to get P&L chart data")

    @router.get("/balances")
    async def get_balances_summary(request: Request):
        """Get futures and spot balances summary with cache"""
        try:
            # Try to get from cache first
            # For now, we use user_id=1 as default (single-user system)
            # TODO: Extract user_id from JWT when auth is fully implemented
            user_id = 1

            # Get main account FIRST to include in cache key
            main_account = await transaction_db.fetchrow("""
                SELECT id, name, exchange, api_key, secret_key, testnet, passphrase
                FROM exchange_accounts
                WHERE testnet = false AND is_active = true AND is_main = true
                LIMIT 1
            """)

            if not main_account:
                return {
                    "success": False,
                    "error": "No main exchange account configured"
                }

            # Cache key includes exchange account ID to differentiate between exchanges
            cache_key = f"balances_summary_{main_account['id']}"
            cached_data = await cache.get(user_id, cache_key)
            if cached_data is not None:
                logger.info(f"💰 Balances summary from CACHE (exchange={main_account['exchange']})")
                return {"success": True, "data": cached_data, "from_cache": True}

            logger.info(f"💰 Getting balances summary from {main_account['exchange'].upper()} API (real-time)")

            # Initialize variables
            futures_balance = 0
            spot_balance = 0
            futures_assets = []
            spot_assets = []
            futures_pnl = 0.0
            spot_pnl = 0.0

            try:
                # main_account already fetched above for cache key
                if main_account:
                    # Get API keys from database (plain text - Supabase encryption at rest)
                    api_key = main_account.get('api_key')
                    secret_key = main_account.get('secret_key')
                    passphrase = main_account.get('passphrase')
                    exchange_name = main_account.get('name')

                    # Validate that keys exist
                    if not api_key or not secret_key:
                        logger.error(f"❌ API keys are empty for main account {main_account['id']}")
                        raise HTTPException(
                            status_code=500,
                            detail="Exchange API keys are not configured correctly"
                        )

                    logger.info(f"✅ API keys retrieved for main account {main_account['id']}")

                    # Create connector based on exchange type (MULTI-EXCHANGE)
                    exchange = main_account['exchange'].lower()
                    testnet = main_account['testnet']

                    if exchange == 'binance':
                        connector = BinanceConnector(api_key=api_key, api_secret=secret_key, testnet=testnet)
                    elif exchange == 'bybit':
                        connector = BybitConnector(api_key=api_key, api_secret=secret_key, testnet=testnet)
                    elif exchange == 'bingx':
                        connector = BingXConnector(api_key=api_key, api_secret=secret_key, testnet=testnet)
                    elif exchange == 'bitget':
                        connector = BitgetConnector(api_key=api_key, api_secret=secret_key, passphrase=passphrase, testnet=testnet)
                    else:
                        raise HTTPException(status_code=400, detail=f"Exchange {exchange} not supported")

                    # Initialize price service for USD conversion
                    logger.info("💱 Initializing price service for USD conversion...")
                    price_service = BinancePriceService(testnet=testnet)
                    real_prices = await price_service.get_all_ticker_prices()
                    logger.info(f"✅ Loaded {len(real_prices)} price pairs from Binance")

                    # 1. GET SPOT BALANCES IN REAL-TIME
                    logger.info("📊 Fetching SPOT balances from exchange...")
                    spot_result = await connector.get_account_info()
                    if spot_result.get('success'):
                        balances = spot_result.get('balances', [])
                        for balance in balances:
                            free = float(balance.get('free', 0))
                            locked = float(balance.get('locked', 0))
                            total = free + locked

                            # Only include assets with balance
                            if total > 0:
                                asset = balance.get('asset')

                                # Calculate USD value using price service
                                usd_value = await price_service.calculate_usdt_value(asset, total, real_prices)

                                spot_assets.append({
                                    "asset": asset,
                                    "free": free,
                                    "locked": locked,
                                    "total": total,
                                    "usd_value": usd_value,
                                    "exchange": exchange_name
                                })
                                spot_balance += usd_value  # Sum in USD

                        logger.info(f"✅ SPOT: {len(spot_assets)} assets retrieved, Total: ${spot_balance:.2f}")

                    # 2. GET FUTURES ACCOUNT IN REAL-TIME
                    logger.info("🚀 Fetching FUTURES account from exchange...")
                    futures_result = await connector.get_futures_account()
                    if futures_result.get('success'):
                        # FIX: Assets estão dentro de 'account' na resposta
                        assets = futures_result.get('account', {}).get('assets', [])
                        for asset_data in assets:
                            wallet_balance = float(asset_data.get('walletBalance', 0))
                            unrealized_profit = float(asset_data.get('unrealizedProfit', 0))
                            available_balance = float(asset_data.get('availableBalance', 0))

                            # Only include assets with balance (usar available ao invés de wallet)
                            if available_balance != 0:
                                asset = asset_data.get('asset')

                                # FIX: Usar availableBalance (saldo realizado) ao invés de walletBalance
                                # walletBalance = $357.70 (JÁ INCLUI P&L!)
                                # availableBalance = $305.15 (SALDO REAL sem P&L)
                                # O P&L ($53.95) é calculado separadamente em get_futures_positions
                                balance_usd = await price_service.calculate_usdt_value(asset, available_balance, real_prices)

                                futures_assets.append({
                                    "asset": asset,
                                    "free": available_balance,
                                    "locked": wallet_balance - available_balance,
                                    "total": wallet_balance,
                                    "usd_value": balance_usd,  # Apenas saldo realizado
                                    "exchange": exchange_name
                                })
                                futures_balance += balance_usd  # Apenas saldo realizado

                        logger.info(f"✅ FUTURES: {len(futures_assets)} assets retrieved, Total: ${futures_balance:.2f}")

                    # 3. GET FUTURES POSITIONS P&L IN REAL-TIME
                    logger.info("📈 Fetching FUTURES positions P&L...")
                    positions_result = await connector.get_futures_positions()
                    if positions_result.get('success', True):
                        positions = positions_result.get('positions', [])
                        for position in positions:
                            try:
                                # Calculate unrealized PnL from real Binance data
                                unrealized_pnl = float(position.get('unRealizedProfit', position.get('unrealizedPnl', 0)))
                                futures_pnl += unrealized_pnl
                            except (ValueError, TypeError):
                                continue

                    logger.info(f"✅ Real-time futures P&L: ${futures_pnl:.2f}")

            except Exception as e:
                logger.error(f"Error getting real-time P&L: {e}")
                # Fallback to database if API fails
                positions_pnl = await transaction_db.fetchrow("""
                    SELECT
                        COALESCE(SUM(CASE WHEN ea.account_type IN ('FUTURES', 'LINEAR', 'UNIFIED')
                                     THEN p.unrealized_pnl ELSE 0 END), 0) as futures_pnl,
                        COALESCE(SUM(CASE WHEN ea.account_type NOT IN ('FUTURES', 'LINEAR', 'UNIFIED')
                                     THEN p.unrealized_pnl ELSE 0 END), 0) as spot_pnl
                    FROM positions p
                    LEFT JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                    WHERE ea.testnet = false
                      AND ea.is_active = true
                      AND p.status = 'open'
                """)

                futures_pnl = float(positions_pnl["futures_pnl"] or 0)
                spot_pnl = float(positions_pnl["spot_pnl"] or 0)

            result = {
                "futures": {
                    "total_balance_usd": futures_balance,
                    "unrealized_pnl": futures_pnl,
                    "net_balance": futures_balance + futures_pnl,
                    "assets": futures_assets  # ALL assets (no limit)
                },
                "spot": {
                    "total_balance_usd": spot_balance,
                    "unrealized_pnl": spot_pnl,
                    "net_balance": spot_balance + spot_pnl,
                    "assets": spot_assets  # ALL assets (no limit)
                },
                "total": {
                    "balance_usd": futures_balance + spot_balance,
                    "pnl": futures_pnl + spot_pnl,
                    "net_worth": (futures_balance + spot_balance) + (futures_pnl + spot_pnl)
                }
            }

            logger.info(f"💰 Real-time balances from exchange API",
                       futures_balance=futures_balance,
                       futures_assets_count=len(futures_assets),
                       spot_balance=spot_balance,
                       spot_assets_count=len(spot_assets),
                       total_pnl=futures_pnl + spot_pnl)

            # Store in cache with 3s TTL (using exchange-specific cache key)
            await cache.set(user_id, cache_key, result, ttl=3)

            return {"success": True, "data": result, "from_cache": False}

        except Exception as e:
            logger.error("Error getting balances summary", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to get balances summary")

    @router.get("/cache/metrics")
    async def get_cache_metrics(request: Request):
        """Get cache performance metrics for monitoring"""
        try:
            metrics = cache.get_metrics()
            logger.info("📊 Cache metrics retrieved", **metrics)
            return {"success": True, "data": metrics}
        except Exception as e:
            logger.error("Error getting cache metrics", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to get cache metrics")

    @router.post("/cache/invalidate")
    async def invalidate_cache(request: Request):
        """Invalidate all cache entries (admin endpoint)"""
        try:
            # TODO: Add admin authentication
            user_id = 1
            count = await cache.invalidate(user_id)
            logger.warning(f"🗑️ Cache invalidated manually: {count} entries")
            return {"success": True, "data": {"invalidated_entries": count}}
        except Exception as e:
            logger.error("Error invalidating cache", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to invalidate cache")

    @router.get("/spot-balances/{exchange_account_id}")
    async def get_spot_balances(request: Request, exchange_account_id: str):
        """
        Get all SPOT balances (wallet assets) for a specific exchange account
        Returns ALL assets with balance > 0 + USD value calculated
        """
        try:
            logger.info(f"💰 Getting SPOT balances for account {exchange_account_id}")

            # Get SPOT balances from exchange API in real-time (MULTI-EXCHANGE SUPPORT)
            account_info = await transaction_db.fetchrow("""
                SELECT id, exchange, api_key, secret_key, testnet, passphrase
                FROM exchange_accounts
                WHERE id = $1 AND is_active = true
            """, exchange_account_id)

            if not account_info:
                raise HTTPException(status_code=404, detail="Exchange account not found or inactive")

            from infrastructure.pricing.binance_price_service import BinancePriceService

            # Get API keys from database (plain text - Supabase encryption at rest)
            api_key = account_info.get('api_key')
            secret_key = account_info.get('secret_key')
            passphrase = account_info.get('passphrase')

            # Validate that keys exist
            if not api_key or not secret_key:
                logger.error(f"❌ API keys are empty for account {exchange_account_id}")
                raise HTTPException(
                    status_code=500,
                    detail="Exchange API keys are not configured correctly"
                )

            logger.info(f"✅ API keys retrieved for account {exchange_account_id}")

            # Create connector based on exchange type (MULTI-EXCHANGE)
            exchange = account_info['exchange'].lower()
            testnet = account_info['testnet']

            if exchange == 'binance':
                connector = BinanceConnector(api_key=api_key, api_secret=secret_key, testnet=testnet)
            elif exchange == 'bybit':
                connector = BybitConnector(api_key=api_key, api_secret=secret_key, testnet=testnet)
            elif exchange == 'bingx':
                connector = BingXConnector(api_key=api_key, api_secret=secret_key, testnet=testnet)
            elif exchange == 'bitget':
                connector = BitgetConnector(api_key=api_key, api_secret=secret_key, passphrase=passphrase, testnet=testnet)
            else:
                raise HTTPException(status_code=400, detail=f"Exchange {exchange} not supported")

            # Get SPOT account info from Binance
            account_result = await connector.get_account_info()

            if not account_result.get('success', False):
                raise HTTPException(status_code=500, detail="Failed to fetch SPOT balances from exchange")

            balances = account_result.get('balances', [])

            # Initialize price service for USD conversion
            price_service = BinancePriceService(testnet=account_info['testnet'])
            real_prices = await price_service.get_all_ticker_prices()

            # Filter only balances with value > 0 and calculate USD value
            spot_assets = []
            total_usd_value = 0.0

            for balance in balances:
                free = float(balance.get('free', 0))
                locked = float(balance.get('locked', 0))
                total = free + locked

                if total > 0:
                    asset = balance['asset']

                    # Calculate USD value
                    usd_value = await price_service.calculate_usdt_value(asset, total, real_prices)
                    total_usd_value += usd_value

                    spot_assets.append({
                        "asset": asset,
                        "free": free,
                        "locked": locked,
                        "total": total,
                        "in_order": locked,  # Alias for locked (em ordens abertas)
                        "usd_value": usd_value
                    })

            # Sort by USD value descending
            spot_assets.sort(key=lambda x: x['usd_value'], reverse=True)

            logger.info(f"✅ Found {len(spot_assets)} SPOT assets, Total: ${total_usd_value:.2f}")

            return {
                "success": True,
                "data": {
                    "exchange_account_id": exchange_account_id,
                    "assets": spot_assets,
                    "total_assets": len(spot_assets),
                    "total_usd_value": total_usd_value
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting SPOT balances: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get SPOT balances: {str(e)}")

    return router