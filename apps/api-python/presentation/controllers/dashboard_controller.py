"""Dashboard Controller - API endpoints for home dashboard metrics"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Optional
import structlog
from datetime import datetime, timedelta
from decimal import Decimal
import jwt
import uuid as uuid_module

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.cache import get_positions_cache
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.exchanges.bybit_connector import BybitConnector
from infrastructure.exchanges.bingx_connector import BingXConnector
from infrastructure.exchanges.bitget_connector import BitgetConnector
from infrastructure.pricing.binance_price_service import BinancePriceService
import os

logger = structlog.get_logger(__name__)
cache = get_positions_cache()

# JWT Secret Key from environment
JWT_SECRET_KEY = os.getenv("SECRET_KEY", "trading_platform_secret_key_2024")


def get_user_id_from_request(request: Request) -> Optional[str]:
    """Extract user_id from JWT token in Authorization header"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload.get("user_id")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_user_uuid_from_request(request: Request) -> Optional[uuid_module.UUID]:
    """Extract user_id from JWT and convert to UUID"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return None
    try:
        return uuid_module.UUID(user_id) if isinstance(user_id, str) else user_id
    except ValueError:
        return None

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
        """Get futures and spot balances summary with cache - filtered by authenticated user"""
        connector = None  # Initialize connector at function level for cleanup in finally
        try:
            # Extract user_id from JWT token
            user_uuid = get_user_uuid_from_request(request)

            # If no user authenticated, return empty data
            if not user_uuid:
                return {
                    "success": True,
                    "data": {
                        "futures": {"total_balance_usd": 0, "unrealized_pnl": 0, "net_balance": 0, "assets": []},
                        "spot": {"total_balance_usd": 0, "unrealized_pnl": 0, "net_balance": 0, "assets": []},
                        "total": {"balance_usd": 0, "pnl": 0, "net_worth": 0}
                    },
                    "message": "No authenticated user"
                }

            # Use user_id for cache key
            user_id = str(user_uuid)

            # Get main account FIRST - FILTERED BY USER_ID
            main_account = await transaction_db.fetchrow("""
                SELECT id, name, exchange, api_key, secret_key, testnet, passphrase
                FROM exchange_accounts
                WHERE testnet = false AND is_active = true AND is_main = true AND user_id = $1
                LIMIT 1
            """, user_uuid)

            if not main_account:
                # User has no main exchange account - return empty balances
                return {
                    "success": True,
                    "data": {
                        "futures": {"total_balance_usd": 0, "unrealized_pnl": 0, "net_balance": 0, "assets": []},
                        "spot": {"total_balance_usd": 0, "unrealized_pnl": 0, "net_balance": 0, "assets": []},
                        "total": {"balance_usd": 0, "pnl": 0, "net_worth": 0}
                    },
                    "message": "No main exchange account configured. Please add an exchange account."
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
            futures_pnl = 0.0  # Unrealized P&L (open positions)
            spot_pnl = 0.0
            futures_realized_pnl = 0.0  # Realized P&L (closed positions today)

            try:
                # main_account already fetched above for cache key
                connector = None  # Re-initialize here to ensure it's defined in this scope
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

                    # 1. GET SPOT AND FUTURES BALANCES IN REAL-TIME
                    # BingX requires special handling with get_balances_separated()
                    if exchange == 'bingx':
                        logger.info("📊 Fetching BingX balances (SPOT + FUTURES) using separated method...")
                        balances_result = await connector.get_balances_separated()

                        if balances_result.get('success'):
                            # Get SPOT balance (already in USD from BingX connector)
                            spot_balance = balances_result.get('spot_usdt', 0)
                            spot_assets.append({
                                "asset": "USDT",
                                "free": spot_balance,
                                "locked": 0,
                                "total": spot_balance,
                                "usd_value": spot_balance,
                                "exchange": exchange_name
                            })
                            logger.info(f"✅ SPOT: ${spot_balance:.2f} (calculated from wallet)")

                            # Get FUTURES balance (already in USD from BingX connector)
                            futures_balance = balances_result.get('futures_usdt', 0)
                            futures_assets.append({
                                "asset": "USDT",
                                "free": futures_balance,
                                "locked": 0,
                                "total": futures_balance,
                                "usd_value": futures_balance,
                                "exchange": exchange_name
                            })
                            logger.info(f"✅ FUTURES: ${futures_balance:.2f}")

                            # Calculate SPOT P&L for BingX using order history
                            logger.info("📊 Calculating BingX SPOT P&L from order history...")
                            try:
                                # Get all spot balances (individual assets like LINK, AERO, etc.)
                                spot_balances_result = await connector.get_account_balances()
                                if spot_balances_result.get('success'):
                                    raw_balances = spot_balances_result.get('balances', [])

                                    # Get all BUY orders for this account to calculate average cost
                                    buy_orders_query = await transaction_db.fetch("""
                                        SELECT symbol, quantity, price, created_at
                                        FROM orders
                                        WHERE exchange_account_id = $1
                                          AND LOWER(side::text) = 'buy'
                                          AND status = 'filled'
                                        ORDER BY created_at ASC
                                    """, str(main_account['id']))

                                    # Calculate average buy price for each asset
                                    avg_buy_prices = {}
                                    last_buy_prices = {}

                                    for order in buy_orders_query:
                                        symbol = order['symbol']
                                        asset = symbol.replace('USDT', '').replace('-', '')

                                        if asset not in avg_buy_prices:
                                            avg_buy_prices[asset] = {'total_qty': 0, 'total_cost': 0}

                                        qty = float(order['quantity'])
                                        price = float(order['price'])
                                        avg_buy_prices[asset]['total_qty'] += qty
                                        avg_buy_prices[asset]['total_cost'] += (qty * price)
                                        last_buy_prices[asset] = price

                                    for asset in avg_buy_prices:
                                        if avg_buy_prices[asset]['total_qty'] > 0:
                                            avg_buy_prices[asset]['avg_price'] = avg_buy_prices[asset]['total_cost'] / avg_buy_prices[asset]['total_qty']

                                    # Get current prices from BingX
                                    price_cache = {'USDT': 1.0, 'USDC': 1.0}
                                    all_prices_result = await connector.get_all_ticker_prices()
                                    if all_prices_result.get('success'):
                                        for ticker in all_prices_result.get('data', []):
                                            symbol = ticker.get('symbol', '')
                                            if 'USDT' in symbol:
                                                asset = symbol.replace('-USDT', '').replace('USDT', '')
                                                price = float(ticker.get('lastPrice', 0))
                                                if price > 0:
                                                    price_cache[asset] = price

                                    # Calculate P&L for each spot asset
                                    for bal in raw_balances:
                                        asset = bal['asset']
                                        if asset in ['USDT', 'USDC']:
                                            continue

                                        total = float(bal['total'])
                                        if total <= 0:
                                            continue

                                        current_price = price_cache.get(asset, 0)

                                        # Get average buy price
                                        avg_buy_price = 0
                                        if asset in avg_buy_prices and 'avg_price' in avg_buy_prices[asset]:
                                            avg_buy_price = avg_buy_prices[asset]['avg_price']
                                        elif asset in last_buy_prices:
                                            avg_buy_price = last_buy_prices[asset]

                                        # Calculate P&L
                                        if avg_buy_price > 0 and current_price > 0:
                                            asset_pnl = (current_price - avg_buy_price) * total
                                            spot_pnl += asset_pnl

                                    logger.info(f"✅ BingX SPOT P&L calculated: ${spot_pnl:.2f}")
                            except Exception as spot_calc_err:
                                logger.warning(f"⚠️ Error calculating BingX spot P&L: {spot_calc_err}")
                        else:
                            logger.error(f"❌ Failed to get BingX balances: {balances_result.get('error')}")

                    else:
                        # For other exchanges (Binance, Bybit, Bitget), use normal methods
                        # Initialize price service for USD conversion (only for non-BingX exchanges)
                        logger.info("💱 Initializing price service for USD conversion...")
                        price_service = BinancePriceService(testnet=testnet)
                        real_prices = await price_service.get_all_ticker_prices()
                        logger.info(f"✅ Loaded {len(real_prices)} price pairs from Binance")

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
                                # Calculate unrealized PnL from real exchange data
                                # BingX uses 'unrealizedProfit', Binance uses 'unRealizedProfit'
                                unrealized_pnl = float(position.get('unrealizedProfit', position.get('unRealizedProfit', position.get('unrealizedPnl', 0))))
                                futures_pnl += unrealized_pnl
                            except (ValueError, TypeError):
                                continue

                    logger.info(f"✅ Real-time futures P&L: ${futures_pnl:.2f}")

                    # 4. GET SPOT P&L - Use SpotPnlService with real trade history from exchange
                    logger.info("📊 Calculating SPOT P&L using SpotPnlService (real trade history)...")
                    try:
                        from infrastructure.pricing.spot_pnl_service import SpotPnlService
                        spot_pnl_service = SpotPnlService(connector=connector)
                        spot_pnl_result = await spot_pnl_service.calculate_spot_pnl(str(main_account['id']), connector=connector)
                        if spot_pnl_result.get('success'):
                            spot_pnl = spot_pnl_result.get('total_pnl_usdt', 0.0)
                            logger.info(f"✅ Real-time spot P&L: ${spot_pnl:.2f} ({spot_pnl_result.get('active_assets_count', 0)} assets)")
                    except Exception as spot_err:
                        logger.warning(f"⚠️ Error calculating spot P&L: {spot_err}")

                    # 5. GET REALIZED P&L FROM CLOSED POSITIONS TODAY
                    logger.info("💰 Calculating realized P&L from closed positions today...")
                    try:
                        from datetime import datetime, timezone
                        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

                        realized_pnl_result = await transaction_db.fetchrow("""
                            SELECT COALESCE(SUM(realized_pnl), 0) as total_realized_pnl
                            FROM positions
                            WHERE exchange_account_id = $1
                              AND status = 'closed'
                              AND closed_at >= $2
                        """, str(main_account['id']), today_start)

                        if realized_pnl_result:
                            futures_realized_pnl = float(realized_pnl_result['total_realized_pnl'] or 0)
                            logger.info(f"✅ Realized P&L today: ${futures_realized_pnl:.2f}")
                    except Exception as realized_err:
                        logger.warning(f"⚠️ Error calculating realized P&L: {realized_err}")

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
                    "realized_pnl_today": futures_realized_pnl,
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
                    "pnl": futures_pnl + spot_pnl,  # Unrealized only
                    "realized_pnl_today": futures_realized_pnl,  # Realized P&L today
                    "total_pnl_today": (futures_pnl + spot_pnl) + futures_realized_pnl,  # Unrealized + Realized
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

        finally:
            # Always close the connector to prevent memory leaks
            if connector is not None:
                try:
                    await connector.close()
                    logger.debug("✅ Connector session closed")
                except Exception as close_error:
                    logger.warning(f"⚠️ Error closing connector: {close_error}")

    @router.get("/balances/{account_id}")
    async def get_account_balances(request: Request, account_id: str):
        """Get futures and spot balances for a specific account (works with all exchanges) - filtered by user"""
        try:
            # Extract user_id from JWT token
            user_uuid = get_user_uuid_from_request(request)
            connector = None

            # If no user authenticated, return error
            if not user_uuid:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Get account info - FILTERED BY USER_ID
            account = await transaction_db.fetchrow("""
                SELECT id, name, exchange, api_key, secret_key, testnet, passphrase
                FROM exchange_accounts
                WHERE id = $1 AND is_active = true AND user_id = $2
            """, account_id, user_uuid)

            if not account:
                raise HTTPException(status_code=404, detail="Exchange account not found")

            # Get API keys
            api_key = account.get('api_key')
            secret_key = account.get('secret_key')
            passphrase = account.get('passphrase')
            exchange = account['exchange'].lower()
            testnet = account['testnet']

            if not api_key or not secret_key:
                raise HTTPException(status_code=500, detail="API keys not configured")

            # Create connector based on exchange
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

            # Get balances based on exchange
            futures_balance = 0
            spot_balance = 0

            if exchange == 'bingx':
                # BingX: Use get_balances_separated()
                balances_result = await connector.get_balances_separated()
                if balances_result.get('success'):
                    spot_balance = balances_result.get('spot_usdt', 0)
                    futures_balance = balances_result.get('futures_usdt', 0)
            else:
                # Other exchanges: Use standard methods
                # Get FUTURES balance
                futures_result = await connector.get_futures_account()
                if futures_result.get('success'):
                    assets = futures_result.get('account', {}).get('assets', [])
                    for asset_data in assets:
                        available_balance = float(asset_data.get('availableBalance', 0))
                        if available_balance != 0:
                            futures_balance += available_balance

                # Get SPOT balance (simplified - just return 0 for now)
                spot_balance = 0

            result = {
                "futures_balance_usdt": futures_balance,
                "spot_balance_usdt": spot_balance,
                "total_balance_usdt": futures_balance + spot_balance
            }

            logger.info(f"💰 Balances for account {account_id} ({exchange}): FUTURES=${futures_balance:.2f}, SPOT=${spot_balance:.2f}")

            return {"success": True, "data": result}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting account balances: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get account balances: {str(e)}")
        finally:
            if connector is not None:
                try:
                    await connector.close()
                except Exception as close_error:
                    logger.warning(f"⚠️ Error closing connector: {close_error}")

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
        Filtered by authenticated user
        """
        try:
            # Extract user_id from JWT token
            user_uuid = get_user_uuid_from_request(request)

            # If no user authenticated, return error
            if not user_uuid:
                raise HTTPException(status_code=401, detail="Authentication required")

            logger.info(f"💰 Getting SPOT balances for account {exchange_account_id}")

            # Get SPOT balances from exchange API in real-time (MULTI-EXCHANGE SUPPORT)
            # FILTERED BY USER_ID
            account_info = await transaction_db.fetchrow("""
                SELECT id, exchange, api_key, secret_key, testnet, passphrase
                FROM exchange_accounts
                WHERE id = $1 AND is_active = true AND user_id = $2
            """, exchange_account_id, user_uuid)

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

            # BingX: Use get_account_balances() to get ALL individual assets (LINK, AERO, DRIFT, etc.)
            if exchange == 'bingx':
                balances_result = await connector.get_account_balances()

                if not balances_result.get('success'):
                    raise HTTPException(status_code=500, detail="Failed to fetch BingX balances")

                raw_balances = balances_result.get('balances', [])

                # Get all BUY orders for this account to calculate average cost
                buy_orders_query = await transaction_db.fetch("""
                    SELECT symbol, quantity, price, created_at
                    FROM orders
                    WHERE exchange_account_id = $1
                      AND LOWER(side::text) = 'buy'
                      AND status = 'filled'
                    ORDER BY created_at ASC
                """, exchange_account_id)

                # Calculate average buy price for each asset + store last buy price
                avg_buy_prices = {}
                last_buy_prices = {}  # Store the most recent buy price as fallback

                for order in buy_orders_query:
                    symbol = order['symbol']
                    # Extract asset from symbol (e.g., LINKUSDT -> LINK)
                    asset = symbol.replace('USDT', '').replace('-', '')

                    if asset not in avg_buy_prices:
                        avg_buy_prices[asset] = {'total_qty': 0, 'total_cost': 0}

                    qty = float(order['quantity'])
                    price = float(order['price'])
                    avg_buy_prices[asset]['total_qty'] += qty
                    avg_buy_prices[asset]['total_cost'] += (qty * price)

                    # Store last buy price (will be overwritten with most recent)
                    last_buy_prices[asset] = price

                # Calculate average prices
                for asset in avg_buy_prices:
                    if avg_buy_prices[asset]['total_qty'] > 0:
                        avg_buy_prices[asset]['avg_price'] = avg_buy_prices[asset]['total_cost'] / avg_buy_prices[asset]['total_qty']

                # PERFORMANCE OPTIMIZATION: Fetch all prices in batch (1 API call instead of N)
                # Extract unique assets that need price lookup
                assets_needing_prices = [bal['asset'] for bal in raw_balances if bal['asset'] not in ['USDT', 'USDC']]

                # Fetch all prices at once from BingX (much faster than individual calls)
                price_cache = {}
                if assets_needing_prices:
                    try:
                        # Get all BingX ticker prices in ONE call
                        all_prices_result = await connector.get_all_ticker_prices()
                        if all_prices_result.get('success'):
                            for ticker in all_prices_result.get('data', []):
                                symbol = ticker.get('symbol', '')
                                # Extract base asset (e.g., AERO-USDT -> AERO)
                                if 'USDT' in symbol:
                                    asset = symbol.replace('-USDT', '').replace('USDT', '')
                                    price = float(ticker.get('lastPrice', 0))
                                    if price > 0:
                                        price_cache[asset] = price
                    except Exception as e:
                        logger.warning(f"Failed to fetch batch prices from BingX: {e}")

                # Stablecoins always $1
                price_cache['USDT'] = 1.0
                price_cache['USDC'] = 1.0

                assets_list = []
                total_usd_value = 0
                total_pnl = 0

                for bal in raw_balances:
                    asset = bal['asset']
                    free = float(bal['free'])
                    locked = float(bal['locked'])
                    total = float(bal['total'])

                    # Get price from cache (instant lookup, no API call)
                    current_price = price_cache.get(asset, 0)
                    usd_value = current_price * total
                    total_usd_value += usd_value

                    # Calculate P&L with fallback logic:
                    # 1st: Try average buy price (from all orders)
                    # 2nd: Try last buy price (most recent order)
                    # 3rd: No P&L if no historical orders
                    pnl = 0
                    pnl_percent = 0
                    avg_buy_price = 0

                    # Try average buy price first
                    if asset in avg_buy_prices and 'avg_price' in avg_buy_prices[asset]:
                        avg_buy_price = avg_buy_prices[asset]['avg_price']
                    # Fallback to last buy price if no average available
                    elif asset in last_buy_prices:
                        avg_buy_price = last_buy_prices[asset]

                    # Calculate P&L if we have a cost basis (either avg or last)
                    if avg_buy_price > 0 and current_price > 0:
                        pnl = (current_price - avg_buy_price) * total
                        pnl_percent = ((current_price - avg_buy_price) / avg_buy_price) * 100
                        total_pnl += pnl

                    assets_list.append({
                        "asset": asset,
                        "free": free,
                        "locked": locked,
                        "total": total,
                        "in_order": 0,  # BingX API doesn't provide this separately
                        "usd_value": round(usd_value, 2),
                        "avg_buy_price": round(avg_buy_price, 4),
                        "pnl": round(pnl, 2),
                        "pnl_percent": round(pnl_percent, 2)
                    })

                await connector.close()

                return {
                    "success": True,
                    "data": {
                        "exchange_account_id": exchange_account_id,
                        "assets": assets_list,
                        "total_assets": len(assets_list),
                        "total_usd_value": round(total_usd_value, 2)
                    }
                }

            # Other exchanges: Get SPOT account info
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

    @router.get("/stats")
    async def get_dashboard_stats(request: Request):
        """
        Get aggregated stats for dashboard cards:
        - active_positions: Total open positions from exchange (Futures + Spot)
        - orders_today: Number of orders executed today
        - orders_3_months: Total orders in last 3 months

        All data comes from the MAIN exchange account
        """
        try:
            user_uuid = get_user_uuid_from_request(request)

            if not user_uuid:
                return {
                    "success": True,
                    "data": {
                        "active_positions": 0,
                        "orders_today": 0,
                        "orders_3_months": 0
                    },
                    "message": "No authenticated user"
                }

            # Get main account for this user
            main_account = await transaction_db.fetchrow("""
                SELECT id, name, exchange, api_key, secret_key, testnet, passphrase
                FROM exchange_accounts
                WHERE testnet = false AND is_active = true AND is_main = true AND user_id = $1
                LIMIT 1
            """, user_uuid)

            if not main_account:
                return {
                    "success": True,
                    "data": {
                        "active_positions": 0,
                        "orders_today": 0,
                        "orders_3_months": 0
                    },
                    "message": "No main exchange account configured"
                }

            logger.info(f"📊 Getting dashboard stats from {main_account['exchange'].upper()}")

            # Create connector based on exchange
            api_key = main_account.get('api_key')
            secret_key = main_account.get('secret_key')
            passphrase = main_account.get('passphrase')
            exchange = main_account['exchange'].lower()
            testnet = main_account['testnet']
            connector = None

            try:
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

                # 1. Get active positions count from exchange API (Futures + Spot)
                active_positions_count = 0

                # Get Futures positions
                positions_result = await connector.get_futures_positions()
                if positions_result.get('success'):
                    active_positions_count = len(positions_result.get('positions', []))

                # Get Spot holdings (altcoins > $1) for BingX
                if exchange == 'bingx' and hasattr(connector, 'get_spot_holdings_as_positions'):
                    spot_result = await connector.get_spot_holdings_as_positions(min_value_usd=1.0)
                    if spot_result.get('success'):
                        active_positions_count += len(spot_result.get('positions', []))

                # 2. Get orders count - today and 3 months
                # IMPORTANT: BingX uses UTC timestamps, so we must use UTC for comparison
                from datetime import timezone
                now = datetime.now(timezone.utc)
                today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
                three_months_ago = now - timedelta(days=90)

                today_start_ms = int(today_start.timestamp() * 1000)
                three_months_ago_ms = int(three_months_ago.timestamp() * 1000)
                now_ms = int(now.timestamp() * 1000)

                orders_today = 0
                orders_3_months = 0

                # Try to fetch orders from exchange API
                try:
                    orders_result = await connector.get_futures_orders(
                        start_time=three_months_ago_ms,
                        end_time=now_ms,
                        limit=500
                    )
                    if orders_result.get('success'):
                        all_orders = orders_result.get('orders', [])
                        orders_3_months = len(all_orders)

                        # Filter orders from today using updateTime (more reliable than time)
                        for order in all_orders:
                            # BingX uses 'updateTime' in milliseconds
                            order_time = int(order.get('updateTime', order.get('time', 0)))
                            if order_time >= today_start_ms:
                                orders_today += 1

                        logger.info(f"📊 Stats: Orders API returned {orders_3_months} total, {orders_today} today")
                except Exception as e:
                    logger.warning(f"Could not fetch orders from exchange API: {e}")

                # If no orders from API, try database as fallback
                if orders_3_months == 0:
                    try:
                        # Count from database (orders table)
                        db_orders_3m = await transaction_db.fetchval("""
                            SELECT COUNT(*) FROM orders o
                            JOIN exchange_accounts ea ON o.exchange_account_id = ea.id
                            WHERE ea.user_id = $1 AND ea.is_main = true
                            AND o.created_at >= $2
                        """, user_uuid, three_months_ago)
                        orders_3_months = db_orders_3m or 0

                        db_orders_today = await transaction_db.fetchval("""
                            SELECT COUNT(*) FROM orders o
                            JOIN exchange_accounts ea ON o.exchange_account_id = ea.id
                            WHERE ea.user_id = $1 AND ea.is_main = true
                            AND o.created_at >= $2
                        """, user_uuid, today_start)
                        orders_today = db_orders_today or 0

                        logger.info(f"📊 Orders from DB fallback: today={orders_today}, 3m={orders_3_months}")
                    except Exception as e:
                        logger.warning(f"Could not fetch orders from database: {e}")

                logger.info(f"📊 Stats: positions={active_positions_count}, orders_today={orders_today}, orders_3m={orders_3_months}")

                return {
                    "success": True,
                    "data": {
                        "active_positions": active_positions_count,
                        "orders_today": orders_today,
                        "orders_3_months": orders_3_months
                    }
                }

            finally:
                if connector:
                    try:
                        await connector.close()
                    except:
                        pass

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")

    @router.get("/recent-orders")
    async def get_recent_orders(request: Request, days: int = 7):
        """
        Get recent orders from the last N days (default 7)
        Returns: tipo operação, ativo, data, volume, margem USDT, P&L

        All data comes from the MAIN exchange account
        """
        try:
            user_uuid = get_user_uuid_from_request(request)

            if not user_uuid:
                return {"success": True, "data": [], "message": "No authenticated user"}

            # Get main account
            main_account = await transaction_db.fetchrow("""
                SELECT id, name, exchange, api_key, secret_key, testnet, passphrase
                FROM exchange_accounts
                WHERE testnet = false AND is_active = true AND is_main = true AND user_id = $1
                LIMIT 1
            """, user_uuid)

            if not main_account:
                return {"success": True, "data": [], "message": "No main exchange account"}

            logger.info(f"📋 Getting recent orders ({days} days) from {main_account['exchange'].upper()}")

            api_key = main_account.get('api_key')
            secret_key = main_account.get('secret_key')
            passphrase = main_account.get('passphrase')
            exchange = main_account['exchange'].lower()
            testnet = main_account['testnet']
            connector = None

            try:
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

                # Calculate time range
                now = datetime.now()
                start_date = now - timedelta(days=days)
                start_time_ms = int(start_date.timestamp() * 1000)
                end_time_ms = int(now.timestamp() * 1000)

                normalized_orders = []

                # =====================================================
                # STEP 1: Fetch P&L from income history (REALIZED_PNL)
                # This is the authoritative source for P&L values
                # =====================================================
                pnl_by_symbol_time = {}  # key: (symbol, timestamp_minute) -> pnl
                try:
                    income_result = await connector.get_futures_income_history(
                        income_type="REALIZED_PNL",
                        start_time=start_time_ms,
                        end_time=end_time_ms,
                        limit=500
                    )
                    if income_result.get('success'):
                        for record in income_result.get('income_history', []):
                            symbol_raw = record.get('symbol', '')
                            # Normalize symbol (BingX uses AAVE-USDT, we want AAVEUSDT)
                            symbol_normalized = symbol_raw.replace('-', '')
                            income_amount = float(record.get('income', 0))
                            timestamp_ms = record.get('time', 0)
                            # Round to minute for matching with orders
                            timestamp_minute = (timestamp_ms // 60000) * 60000

                            # Store P&L by symbol and time window
                            key = (symbol_normalized, timestamp_minute)
                            if key not in pnl_by_symbol_time:
                                pnl_by_symbol_time[key] = 0
                            pnl_by_symbol_time[key] += income_amount

                        logger.info(f"📊 Fetched {len(income_result.get('income_history', []))} P&L records from income history")
                except Exception as e:
                    logger.warning(f"Could not fetch income history for P&L: {e}")

                # =====================================================
                # STEP 2: Get futures orders from exchange API
                # =====================================================
                try:
                    orders_result = await connector.get_futures_orders(
                        start_time=start_time_ms,
                        end_time=end_time_ms,
                        limit=100
                    )

                    if orders_result.get('success'):
                        raw_orders = orders_result.get('orders', [])

                        for order in raw_orders:
                            # Normalize based on exchange format
                            if exchange == 'bingx':
                                symbol = order.get('symbol', '').replace('-', '')
                                side = order.get('side', 'UNKNOWN')
                                position_side = order.get('positionSide', 'UNKNOWN')
                                order_type = order.get('type', 'UNKNOWN')
                                status = order.get('status', 'UNKNOWN')
                                quantity = float(order.get('executedQty', order.get('origQty', 0)))
                                price = float(order.get('avgPrice', order.get('price', 0)))
                                timestamp = int(order.get('time', 0))
                                # Try to get P&L from income history first
                                timestamp_minute = (timestamp // 60000) * 60000
                                pnl_key = (symbol, timestamp_minute)
                                pnl = pnl_by_symbol_time.get(pnl_key, float(order.get('profit', 0)))
                            else:
                                symbol = order.get('symbol', '')
                                side = order.get('side', 'UNKNOWN')
                                position_side = order.get('positionSide', 'UNKNOWN')
                                order_type = order.get('type', 'UNKNOWN')
                                status = order.get('status', 'UNKNOWN')
                                quantity = float(order.get('executedQty', order.get('origQty', 0)))
                                price = float(order.get('avgPrice', order.get('price', 0)))
                                timestamp = int(order.get('time', order.get('updateTime', 0)))
                                pnl = float(order.get('realizedPnl', 0))

                            volume_usdt = quantity * price if price > 0 else 0

                            # Determine trade_direction (ENTRADA/SAÍDA)
                            # LONG + BUY = ENTRADA (opening long)
                            # LONG + SELL = SAÍDA (closing long)
                            # SHORT + SELL = ENTRADA (opening short)
                            # SHORT + BUY = SAÍDA (closing short)
                            side_upper = side.upper()
                            position_side_upper = position_side.upper()
                            if position_side_upper == 'LONG':
                                trade_direction = 'ENTRADA' if side_upper == 'BUY' else 'SAÍDA'
                            elif position_side_upper == 'SHORT':
                                trade_direction = 'ENTRADA' if side_upper == 'SELL' else 'SAÍDA'
                            else:
                                # For one-way mode or unknown
                                trade_direction = 'ENTRADA' if side_upper == 'BUY' else 'SAÍDA'

                            # Include filled or partially filled orders
                            if status in ['FILLED', 'filled', 'PARTIALLY_FILLED', 'NEW', 'CANCELED']:
                                normalized_orders.append({
                                    "id": str(order.get('orderId', '')),
                                    "symbol": symbol,
                                    "side": side_upper,
                                    "position_side": position_side_upper,
                                    "trade_direction": trade_direction,
                                    "type": order_type.upper(),
                                    "status": status.upper(),
                                    "quantity": quantity,
                                    "price": price,
                                    "volume_usdt": round(volume_usdt, 2),
                                    "margin_usdt": round(volume_usdt / 10, 2),
                                    "pnl": round(pnl, 2),
                                    "market_type": "FUTURES",
                                    "operation_type": "futures",
                                    "created_at": datetime.fromtimestamp(timestamp / 1000).isoformat() if timestamp > 0 else None,
                                    "exchange": exchange
                                })
                except Exception as e:
                    logger.warning(f"Could not fetch orders from exchange API: {e}")

                # If no orders from API, try database as fallback
                if len(normalized_orders) == 0:
                    try:
                        db_orders = await transaction_db.fetch("""
                            SELECT o.id, o.symbol, o.side, o.type, o.status,
                                   o.quantity, o.price, o.average_fill_price,
                                   o.realized_pnl, o.created_at, ea.exchange
                            FROM orders o
                            JOIN exchange_accounts ea ON o.exchange_account_id = ea.id
                            WHERE ea.user_id = $1 AND ea.is_main = true
                            AND o.created_at >= $2
                            ORDER BY o.created_at DESC
                            LIMIT 100
                        """, user_uuid, start_date)

                        for order in db_orders:
                            quantity = float(order['quantity']) if order['quantity'] else 0
                            price = float(order['average_fill_price'] or order['price'] or 0)
                            volume_usdt = quantity * price if price > 0 else 0
                            side_upper = (order['side'] or 'UNKNOWN').upper()
                            # DB fallback - default to ENTRADA for BUY, SAÍDA for SELL
                            trade_direction = 'ENTRADA' if side_upper == 'BUY' else 'SAÍDA'

                            normalized_orders.append({
                                "id": str(order['id']),
                                "symbol": order['symbol'],
                                "side": side_upper,
                                "position_side": "UNKNOWN",
                                "trade_direction": trade_direction,
                                "type": (order['type'] or 'UNKNOWN').upper(),
                                "status": (order['status'] or 'UNKNOWN').upper(),
                                "quantity": quantity,
                                "price": price,
                                "volume_usdt": round(volume_usdt, 2),
                                "margin_usdt": round(volume_usdt / 10, 2),
                                "pnl": round(float(order['realized_pnl'] or 0), 2),
                                "market_type": "FUTURES",
                                "operation_type": "futures",
                                "created_at": order['created_at'].isoformat() if order['created_at'] else None,
                                "exchange": order['exchange']
                            })

                        logger.info(f"📋 Found {len(normalized_orders)} orders from DB fallback")
                    except Exception as e:
                        logger.warning(f"Could not fetch orders from database: {e}")

                # Sort by date descending
                normalized_orders.sort(key=lambda x: x['created_at'] or '', reverse=True)

                logger.info(f"📋 Found {len(normalized_orders)} recent orders total")

                return {
                    "success": True,
                    "data": normalized_orders,
                    "total": len(normalized_orders)
                }

            finally:
                if connector:
                    try:
                        await connector.close()
                    except:
                        pass

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting recent orders: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get recent orders: {str(e)}")

    @router.get("/active-positions")
    async def get_active_positions(request: Request):
        """
        Get active/open positions in real-time from exchange API
        Returns BOTH Futures positions AND Spot holdings (altcoins > $1)

        All data comes from the MAIN exchange account
        """
        try:
            user_uuid = get_user_uuid_from_request(request)

            if not user_uuid:
                return {"success": True, "data": [], "message": "No authenticated user"}

            # Get main account
            main_account = await transaction_db.fetchrow("""
                SELECT id, name, exchange, api_key, secret_key, testnet, passphrase
                FROM exchange_accounts
                WHERE testnet = false AND is_active = true AND is_main = true AND user_id = $1
                LIMIT 1
            """, user_uuid)

            if not main_account:
                return {"success": True, "data": [], "message": "No main exchange account"}

            logger.info(f"🎯 Getting active positions (Futures + Spot) from {main_account['exchange'].upper()}")

            api_key = main_account.get('api_key')
            secret_key = main_account.get('secret_key')
            passphrase = main_account.get('passphrase')
            exchange = main_account['exchange'].lower()
            testnet = main_account['testnet']
            account_id = str(main_account['id'])
            connector = None

            try:
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

                normalized_positions = []

                # 1. Get FUTURES positions from exchange API
                positions_result = await connector.get_futures_positions()

                if positions_result.get('success'):
                    raw_positions = positions_result.get('positions', [])

                    for pos in raw_positions:
                        # Normalize based on exchange format
                        if exchange == 'bingx':
                            symbol = pos.get('symbol', '').replace('-', '')
                            position_side = pos.get('positionSide', 'BOTH')
                            position_amt = float(pos.get('positionAmt', 0))
                            side = 'LONG' if position_amt > 0 else 'SHORT'
                            size = abs(position_amt)
                            entry_price = float(pos.get('avgPrice', pos.get('entryPrice', 0)))
                            mark_price = float(pos.get('markPrice', 0))
                            unrealized_pnl = float(pos.get('unrealizedProfit', pos.get('unRealizedProfit', 0)))
                            leverage = int(pos.get('leverage', 1))
                            margin = float(pos.get('isolatedMargin', pos.get('initialMargin', 0)))
                            liquidation_price = float(pos.get('liquidationPrice', 0))
                        else:
                            symbol = pos.get('symbol', '')
                            position_side = pos.get('positionSide', 'BOTH')
                            position_amt = float(pos.get('positionAmt', 0))
                            side = 'LONG' if position_amt > 0 else 'SHORT'
                            size = abs(position_amt)
                            entry_price = float(pos.get('entryPrice', 0))
                            mark_price = float(pos.get('markPrice', 0))
                            unrealized_pnl = float(pos.get('unRealizedProfit', pos.get('unrealizedProfit', 0)))
                            leverage = int(pos.get('leverage', 1))
                            margin = float(pos.get('isolatedMargin', pos.get('initialMargin', 0)))
                            liquidation_price = float(pos.get('liquidationPrice', 0))

                        notional = size * entry_price if entry_price > 0 else 0
                        initial_margin = notional / leverage if leverage > 0 else notional
                        pnl_percentage = (unrealized_pnl / initial_margin * 100) if initial_margin > 0 else 0

                        if size > 0:
                            normalized_positions.append({
                                "id": f"{account_id}_{symbol}_{side}_futures",
                                "symbol": symbol,
                                "side": side,
                                "position_side": position_side,
                                "size": size,
                                "entry_price": round(entry_price, 4),
                                "mark_price": round(mark_price, 4),
                                "unrealized_pnl": round(unrealized_pnl, 2),
                                "pnl_percentage": round(pnl_percentage, 2),
                                "margin": round(margin, 2),
                                "leverage": leverage,
                                "liquidation_price": round(liquidation_price, 4),
                                "notional": round(notional, 2),
                                "market_type": "FUTURES",
                                "operation_type": "futures",
                                "exchange": exchange,
                                "exchange_account_id": account_id
                            })

                futures_count = len(normalized_positions)
                logger.info(f"🎯 Found {futures_count} Futures positions")

                # 2. Get SPOT holdings as positions (altcoins > $1)
                if exchange == 'bingx' and hasattr(connector, 'get_spot_holdings_as_positions'):
                    spot_result = await connector.get_spot_holdings_as_positions(min_value_usd=1.0)
                    if spot_result.get('success'):
                        for spot_pos in spot_result.get('positions', []):
                            spot_pos['id'] = f"{account_id}_{spot_pos['symbol']}_LONG_spot"
                            spot_pos['exchange'] = exchange
                            spot_pos['exchange_account_id'] = account_id
                            normalized_positions.append(spot_pos)

                        spot_count = len(spot_result.get('positions', []))
                        logger.info(f"🎯 Found {spot_count} Spot holdings (> $1)")

                total_count = len(normalized_positions)
                logger.info(f"🎯 Total positions: {total_count} (Futures: {futures_count}, Spot: {total_count - futures_count})")

                return {
                    "success": True,
                    "data": normalized_positions,
                    "total": total_count,
                    "futures_count": futures_count,
                    "spot_count": total_count - futures_count
                }

            finally:
                if connector:
                    try:
                        await connector.close()
                    except:
                        pass

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting active positions: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to get active positions: {str(e)}")

    @router.post("/close-position")
    async def close_position(request: Request):
        """
        Close an active position by creating a market order in the opposite direction.

        Request body:
        {
            "symbol": "BTCUSDT",
            "side": "LONG" or "SHORT",
            "size": 0.001,  // Quantity to close
            "exchange_account_id": "uuid"  // Optional - uses main account if not provided
        }

        For LONG positions: Creates a SELL order
        For SHORT positions: Creates a BUY order
        """
        try:
            user_uuid = get_user_uuid_from_request(request)

            if not user_uuid:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Parse request body
            body = await request.json()
            symbol = body.get('symbol')
            side = body.get('side', '').upper()  # LONG or SHORT
            size = body.get('size')
            exchange_account_id = body.get('exchange_account_id')

            if not symbol:
                raise HTTPException(status_code=400, detail="Symbol is required")
            if not side or side not in ['LONG', 'SHORT']:
                raise HTTPException(status_code=400, detail="Side must be LONG or SHORT")
            if not size or float(size) <= 0:
                raise HTTPException(status_code=400, detail="Size must be a positive number")

            size = float(size)

            # Get exchange account (specific or main)
            if exchange_account_id:
                account = await transaction_db.fetchrow("""
                    SELECT id, name, exchange, api_key, secret_key, testnet, passphrase
                    FROM exchange_accounts
                    WHERE id = $1 AND is_active = true AND user_id = $2
                """, exchange_account_id, user_uuid)
            else:
                # Use main account
                account = await transaction_db.fetchrow("""
                    SELECT id, name, exchange, api_key, secret_key, testnet, passphrase
                    FROM exchange_accounts
                    WHERE testnet = false AND is_active = true AND is_main = true AND user_id = $1
                    LIMIT 1
                """, user_uuid)

            if not account:
                raise HTTPException(status_code=404, detail="Exchange account not found")

            logger.info(f"🔴 Closing {side} position on {symbol} ({size} qty) via {account['exchange'].upper()}")

            api_key = account.get('api_key')
            secret_key = account.get('secret_key')
            passphrase = account.get('passphrase')
            exchange = account['exchange'].lower()
            testnet = account['testnet']
            connector = None

            try:
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

                # Determine order side (opposite of position side)
                # LONG position -> SELL to close
                # SHORT position -> BUY to close
                order_side = 'SELL' if side == 'LONG' else 'BUY'

                # Create market order to close position
                if exchange == 'bingx':
                    # BingX: Use create_futures_order with reduce_only=True
                    # In Hedge Mode, we need to specify position_side
                    order_result = await connector.create_futures_order(
                        symbol=symbol,
                        side=order_side,
                        order_type='MARKET',
                        quantity=size,
                        reduce_only=True,
                        position_side=side  # LONG or SHORT for hedge mode
                    )
                elif exchange == 'binance':
                    # Binance: Use create_futures_order with reduceOnly=True
                    order_result = await connector.create_futures_order(
                        symbol=symbol,
                        side=order_side,
                        order_type='MARKET',
                        quantity=size
                    )
                else:
                    # Other exchanges: Try generic create_futures_order
                    order_result = await connector.create_futures_order(
                        symbol=symbol,
                        side=order_side,
                        order_type='MARKET',
                        quantity=size
                    )

                if order_result.get('success'):
                    logger.info(f"✅ Position closed successfully: {symbol} {side} {size}")
                    return {
                        "success": True,
                        "message": f"Position {symbol} {side} closed successfully",
                        "data": {
                            "symbol": symbol,
                            "side": side,
                            "size": size,
                            "order_side": order_side,
                            "order_id": order_result.get('order_id', order_result.get('orderId')),
                            "exchange": exchange
                        }
                    }
                else:
                    error_msg = order_result.get('error', 'Unknown error')
                    logger.error(f"❌ Failed to close position: {error_msg}")
                    raise HTTPException(status_code=500, detail=f"Failed to close position: {error_msg}")

            finally:
                if connector:
                    try:
                        await connector.close()
                    except:
                        pass

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error closing position: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to close position: {str(e)}")

    return router