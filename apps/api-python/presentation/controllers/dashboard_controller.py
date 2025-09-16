"""Dashboard Controller - API endpoints for home dashboard metrics"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
import structlog
from datetime import datetime, timedelta
from decimal import Decimal

from infrastructure.database.connection_transaction_mode import transaction_db

logger = structlog.get_logger(__name__)

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

    return router