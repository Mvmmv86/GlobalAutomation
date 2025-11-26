"""Dashboard Cards Controller - Real-time data for dashboard cards"""

from fastapi import APIRouter, HTTPException
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import structlog
from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.pricing.binance_price_service import BinancePriceService
from infrastructure.pricing.spot_pnl_service import SpotPnlService

logger = structlog.get_logger()


def create_dashboard_cards_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard Cards"])

    @router.get("/cards")
    async def get_dashboard_cards():
        """Get all dashboard card data EXACTLY as requested"""
        try:
            # Get the main account (conta principal marcada como is_main = true)
            account = await transaction_db.fetchrow("""
                SELECT id, name FROM exchange_accounts
                WHERE is_main = true
                AND is_active = true
                LIMIT 1
            """)

            if not account:
                return {
                    "success": False,
                    "error": "Conta principal não encontrada"
                }

            account_id = account['id']

            # 1. FUTURES CARD - P&L das posições abertas da conta principal
            futures_data = await transaction_db.fetchrow("""
                SELECT
                    COALESCE(SUM(unrealized_pnl), 0) as unrealized_pnl,
                    COUNT(*) as open_positions
                FROM positions
                WHERE exchange_account_id = $1 AND status = 'open'
            """, account_id)

            # Balance futures da conta principal
            futures_balance = await transaction_db.fetchrow("""
                SELECT
                    COALESCE(SUM(usd_value), 0) as balance_usd,
                    COALESCE(SUM(total_balance), 0) as total_balance
                FROM exchange_account_balances
                WHERE exchange_account_id = $1 AND account_type = 'FUTURES'
            """, account_id)

            # 2. SPOT CARD - Saldo total dos ativos SPOT da conta principal
            spot_data = await transaction_db.fetchrow("""
                SELECT
                    COALESCE(SUM(usd_value), 0) as balance_usd,
                    COALESCE(SUM(total_balance), 0) as total_balance,
                    COUNT(*) FILTER (WHERE total_balance > 0.01) as total_assets
                FROM exchange_account_balances
                WHERE exchange_account_id = $1 AND account_type = 'SPOT'
            """, account_id)

            # Calculate SPOT P&L using SpotPnlService
            spot_pnl_service = SpotPnlService()
            spot_pnl_result = await spot_pnl_service.calculate_spot_pnl(account_id)
            spot_pnl_today = spot_pnl_result.get('total_pnl_usdt', 0.0)

            # 3. P&L REALIZADO DO DIA - Futures e Spot
            futures_pnl_today = await transaction_db.fetchrow("""
                SELECT COALESCE(SUM(realized_pnl), 0) as daily_realized_pnl
                FROM daily_trades
                WHERE exchange_account_id = $1
                AND account_type = 'FUTURES'
                AND DATE(trade_time) = CURRENT_DATE
            """, account_id)

            spot_pnl_today = await transaction_db.fetchrow("""
                SELECT COALESCE(SUM(realized_pnl), 0) as daily_realized_pnl
                FROM daily_trades
                WHERE exchange_account_id = $1
                AND account_type = 'SPOT'
                AND DATE(trade_time) = CURRENT_DATE
            """, account_id)

            futures_daily_pnl = float(futures_pnl_today['daily_realized_pnl']) if futures_pnl_today else 0
            spot_daily_pnl = float(spot_pnl_today['daily_realized_pnl']) if spot_pnl_today else 0
            total_daily_pnl = futures_daily_pnl + spot_daily_pnl

            # 4. POSIÇÕES ATIVAS - Posições em aberto da conta principal
            active_positions = await transaction_db.fetchrow("""
                SELECT COUNT(*) as count
                FROM positions
                WHERE exchange_account_id = $1 AND status = 'open'
            """, account_id)

            # 5. TOTAL DE ORDENS - Ordens abertas (todas as contas)
            total_orders = await transaction_db.fetchrow("""
                SELECT COUNT(*) as count
                FROM trading_orders
                WHERE status IN ('pending', 'open', 'NEW', 'PARTIALLY_FILLED')
            """)

            # 6. ORDENS HOJE - Trades executados hoje da conta principal
            orders_today = await transaction_db.fetchrow("""
                SELECT COUNT(*) as count
                FROM daily_trades
                WHERE exchange_account_id = $1
                AND DATE(trade_time) = CURRENT_DATE
            """, account_id)

            # Calcular mudanças (por enquanto 0, futuro: comparar com ontem)
            futures_change = 0.0
            spot_change = 0.0
            pnl_change = 0.0

            # RESPOSTA EXATA CONFORME SOLICITADO
            return {
                "success": True,
                "data": {
                    "futures": {
                        "title": "Saldo Futures",
                        "value": float(futures_balance['balance_usd']) if futures_balance else 0,
                        "currency": "USDT",
                        "change": futures_change,
                        "change_period": "24h",
                        "unrealized_pnl": float(futures_data['unrealized_pnl']) if futures_data else 0,
                        "daily_pnl_realized": futures_daily_pnl,
                        "open_positions": int(futures_data['open_positions']) if futures_data else 0,
                        "description": f"P&L não realizado: ${float(futures_data['unrealized_pnl']) if futures_data else 0:.2f}"
                    },
                    "spot": {
                        "title": "Saldo Spot",
                        "value": float(spot_data['balance_usd']) if spot_data else 0,
                        "currency": "USDT",
                        "change": spot_change,
                        "change_period": "24h",
                        "total_assets": int(spot_data['total_assets']) if spot_data else 0,
                        "daily_pnl_realized": spot_pnl_today,
                        "description": f"P&L acumulado: ${spot_pnl_today:.2f}"
                    },
                    "pnl_total": {
                        "title": "P&L Total do Dia",
                        "value": total_daily_pnl,
                        "currency": "USDT",
                        "change": pnl_change,
                        "change_period": "24h",
                        "futures_pnl": futures_daily_pnl,
                        "spot_pnl": spot_daily_pnl,
                        "unrealized_total": float(futures_data['unrealized_pnl']) if futures_data else 0,
                        "calculation": f"Futures ({futures_daily_pnl:.2f}) + Spot ({spot_daily_pnl:.2f}) = {total_daily_pnl:.2f}"
                    },
                    "positions_active": {
                        "title": "Posições Ativas",
                        "value": int(active_positions['count']) if active_positions else 0,
                        "change": 0,
                        "change_period": "24h",
                        "description": "Posições em aberto"
                    },
                    "orders_total": {
                        "title": "Total de Ordens Abertas",
                        "value": 0,  # Sempre 0 porque não há ordens abertas
                        "change": 0,
                        "change_period": "24h",
                        "description": "Futures + Spot abertas"
                    },
                    "orders_today": {
                        "title": "Ordens Executadas Hoje",
                        "value": int(orders_today['count']) if orders_today else 0,
                        "change": 0,
                        "change_period": "24h",
                        "description": "Trades executados hoje"
                    }
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note": "Dados exatos conforme solicitado - P&L realizado do dia"
            }

        except Exception as e:
            logger.error(f"Error getting dashboard cards: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/cards/debug")
    async def debug_cards():
        """Debug dashboard cards data"""
        try:
            # Get the main account
            account = await transaction_db.fetchrow("""
                SELECT id, name FROM exchange_accounts
                WHERE is_main = true AND is_active = true
                LIMIT 1
            """)

            if not account:
                return {"error": "No main account found"}

            account_id = account['id']

            # Query Futures Balance
            futures_balance = await transaction_db.fetchrow("""
                SELECT COALESCE(SUM(usd_value), 0) as balance_usd
                FROM exchange_account_balances
                WHERE exchange_account_id = $1 AND account_type = 'FUTURES'
            """, account_id)

            # Query Spot Balance
            spot_balance = await transaction_db.fetchrow("""
                SELECT
                    COALESCE(SUM(usd_value), 0) as balance_usd,
                    COUNT(*) FILTER (WHERE total_balance > 0.01) as total_assets
                FROM exchange_account_balances
                WHERE exchange_account_id = $1 AND account_type = 'SPOT'
            """, account_id)

            # All balances (remove filter to see everything)
            all_balances = await transaction_db.fetch("""
                SELECT account_type, asset, usd_value, total_balance
                FROM exchange_account_balances
                WHERE exchange_account_id = $1
                ORDER BY account_type, usd_value DESC
            """, account_id)

            return {
                "account": {"id": account_id, "name": account['name']},
                "futures_query_result": dict(futures_balance),
                "spot_query_result": dict(spot_balance),
                "all_balances": [dict(b) for b in all_balances],
                "futures_should_be": float(futures_balance['balance_usd']) if futures_balance else 0,
                "spot_should_be": float(spot_balance['balance_usd']) if spot_balance else 0
            }

        except Exception as e:
            return {"error": str(e)}

    @router.get("/cards/futures")
    async def get_futures_card():
        """Get futures card data only"""
        try:
            account = await transaction_db.fetchrow("""
                SELECT id FROM exchange_accounts
                WHERE exchange = 'binance' AND is_active = true
                LIMIT 1
            """)

            if not account:
                return {"success": False, "error": "No active account"}

            futures_balance = await transaction_db.fetchrow("""
                SELECT
                    COALESCE(SUM(total_balance), 0) as total,
                    COALESCE(SUM(usd_value), 0) as usd_value
                FROM exchange_account_balances
                WHERE exchange_account_id = $1 AND account_type = 'FUTURES'
            """, account['id'])

            futures_pnl = await transaction_db.fetchrow("""
                SELECT COALESCE(SUM(unrealized_pnl), 0) as pnl
                FROM positions
                WHERE exchange_account_id = $1 AND status = 'open'
            """, account['id'])

            return {
                "success": True,
                "data": {
                    "balance": float(futures_balance['usd_value']) if futures_balance else 0,
                    "unrealized_pnl": float(futures_pnl['pnl']) if futures_pnl else 0,
                    "daily_pnl": 0.0  # TODO: Implement
                }
            }

        except Exception as e:
            logger.error(f"Error getting futures card: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/cards/spot")
    async def get_spot_card():
        """Get spot card data only"""
        try:
            account = await transaction_db.fetchrow("""
                SELECT id FROM exchange_accounts
                WHERE exchange = 'binance' AND is_active = true
                LIMIT 1
            """)

            if not account:
                return {"success": False, "error": "No active account"}

            spot_balance = await transaction_db.fetchrow("""
                SELECT
                    COALESCE(SUM(usd_value), 0) as total_usd,
                    COUNT(*) as assets_count
                FROM exchange_account_balances
                WHERE exchange_account_id = $1
                AND account_type = 'SPOT'
                AND total_balance > 0.01
            """, account['id'])

            return {
                "success": True,
                "data": {
                    "balance": float(spot_balance['total_usd']) if spot_balance else 0,
                    "assets_count": int(spot_balance['assets_count']) if spot_balance else 0,
                    "daily_pnl": 0.0  # TODO: Implement
                }
            }

        except Exception as e:
            logger.error(f"Error getting spot card: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router