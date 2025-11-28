"""Positions Controller - API endpoints for managing trading positions"""

from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
import structlog
from decimal import Decimal
from datetime import datetime

from infrastructure.database.connection_transaction_mode import transaction_db

logger = structlog.get_logger(__name__)

def create_positions_router() -> APIRouter:
    """Create and configure the positions router"""
    router = APIRouter(prefix="/api/v1/positions", tags=["Positions"])

    @router.get("")
    async def get_positions(
        request: Request,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        exchange_account_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: Optional[int] = None,
        include_closed_from_api: Optional[bool] = False  # NOVO: buscar fechadas da API
    ):
        """
        Get all positions with optional filtering

        Se include_closed_from_api=true, busca posições fechadas diretamente da Binance API
        e combina com as posições do banco de dados.
        """
        try:
            # Build query with optional filters
            where_conditions = []
            params = []
            param_count = 1

            if status:
                where_conditions.append(f"p.status = ${param_count}")
                params.append(status)
                param_count += 1

            if symbol:
                where_conditions.append(f"p.symbol ILIKE ${param_count}")
                params.append(f"%{symbol}%")
                param_count += 1

            if exchange_account_id:
                where_conditions.append(f"p.exchange_account_id = ${param_count}")
                params.append(exchange_account_id)
                param_count += 1

            # Note: operation_type filter ignored - positions table only contains FUTURES
            # SPOT positions are not stored in this table

            if date_from:
                where_conditions.append(f"p.created_at >= ${param_count}")
                # Convert string to datetime object
                date_obj = datetime.strptime(date_from, "%Y-%m-%d")
                params.append(date_obj)
                param_count += 1

            if date_to:
                where_conditions.append(f"p.created_at <= ${param_count}")
                # Convert string to datetime object
                date_obj = datetime.strptime(date_to, "%Y-%m-%d")
                params.append(date_obj)
                param_count += 1

            # Base WHERE clause - only check if account is active
            base_conditions = ["ea.is_active = true"]
            all_conditions = base_conditions + where_conditions

            # Add LIMIT clause if specified
            limit_clause = ""
            if limit:
                limit_clause = f"LIMIT {limit}"

            query = f"""
                SELECT
                    p.id, p.external_id, p.symbol, p.side, p.status,
                    p.size, p.entry_price, p.mark_price,
                    p.unrealized_pnl, p.realized_pnl,
                    p.initial_margin, p.maintenance_margin, p.leverage,
                    p.liquidation_price, p.bankruptcy_price,
                    p.opened_at, p.closed_at, p.last_update_at,
                    p.total_fees, p.funding_fees,
                    p.exchange_account_id, p.created_at, p.updated_at,
                    ea.name as exchange_account_name, ea.exchange
                FROM positions p
                LEFT JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE {' AND '.join(all_conditions)}
                ORDER BY p.created_at DESC
                {limit_clause}
            """
            
            positions = await transaction_db.fetch(query, *params)
            
            positions_list = []
            for position in positions:
                # Calcular P&L %
                size = float(position["size"]) if position["size"] else 0
                entry_price = float(position["entry_price"]) if position["entry_price"] else 0
                unrealized_pnl = float(position["unrealized_pnl"]) if position["unrealized_pnl"] else 0
                leverage = float(position["leverage"]) if position["leverage"] else 1

                # Valor inicial da posição (sem alavancagem)
                position_value = size * entry_price
                # Capital inicial investido (com alavancagem)
                initial_capital = position_value / leverage if leverage > 0 else position_value

                # P&L % = (unrealized_pnl / initial_capital) * 100
                pnl_percentage = (unrealized_pnl / initial_capital * 100) if initial_capital > 0 else 0

                positions_list.append({
                    "id": position["id"],
                    "external_id": position["external_id"],
                    "symbol": position["symbol"],
                    "side": position["side"].upper() if position["side"] else "LONG",
                    "status": position["status"],
                    "size": size,
                    "entry_price": entry_price,
                    "mark_price": float(position["mark_price"]) if position["mark_price"] else 0,
                    "exit_price": None,  # Campo não disponível na tabela atual
                    "unrealized_pnl": unrealized_pnl,
                    "unrealized_pnl_percentage": round(pnl_percentage, 2),  # Novo campo P&L %
                    "realized_pnl": float(position["realized_pnl"]) if position["realized_pnl"] else 0,
                    "initial_margin": float(position["initial_margin"]) if position["initial_margin"] else 0,
                    "maintenance_margin": float(position["maintenance_margin"]) if position["maintenance_margin"] else 0,
                    "leverage": leverage,
                    "liquidation_price": float(position["liquidation_price"]) if position["liquidation_price"] else 0,
                    "bankruptcy_price": float(position["bankruptcy_price"]) if position["bankruptcy_price"] else 0,
                    "opened_at": position["opened_at"].isoformat() if position["opened_at"] else None,
                    "closed_at": position["closed_at"].isoformat() if position["closed_at"] else None,
                    "last_update_at": position["last_update_at"].isoformat() if position["last_update_at"] else None,
                    "total_fees": float(position["total_fees"]) if position["total_fees"] else 0,
                    "funding_fees": float(position["funding_fees"]) if position["funding_fees"] else 0,
                    "exchange_account_id": position["exchange_account_id"],
                    "exchange_account_name": position["exchange_account_name"],
                    "exchange": position["exchange"],
                    "created_at": position["created_at"].isoformat() if position["created_at"] else None,
                    "updated_at": position["updated_at"].isoformat() if position["updated_at"] else None
                })
            
            # NOVO: Se solicitado, buscar posições fechadas da API Binance
            closed_from_api = []
            if include_closed_from_api and (status == 'closed' or status is None):
                try:
                    # Se exchange_account_id especificado, buscar só dele
                    if exchange_account_id:
                        accounts_to_fetch = [exchange_account_id]
                    else:
                        # Buscar todas as contas ativas
                        accounts_result = await transaction_db.fetch("""
                            SELECT id, exchange, api_key, secret_key, testnet
                            FROM exchange_accounts
                            WHERE is_active = true
                        """)
                        accounts_to_fetch = [acc['id'] for acc in accounts_result]

                    # Buscar posições fechadas de cada conta
                    for account_id in accounts_to_fetch:
                        account_data = await transaction_db.fetchrow("""
                            SELECT id, exchange, api_key, secret_key, testnet, name
                            FROM exchange_accounts
                            WHERE id = $1
                        """, account_id)

                        if not account_data or account_data['exchange'].lower() != 'binance':
                            continue

                        # Criar connector
                        from infrastructure.exchanges.binance_connector import BinanceConnector

                        connector = BinanceConnector(
                            api_key=account_data['api_key'],
                            api_secret=account_data['secret_key'],
                            testnet=account_data['testnet']
                        )

                        # Buscar posições fechadas
                        closed_result = await connector.get_closed_positions_from_orders(
                            symbol=symbol,
                            limit=limit or 100
                        )

                        if closed_result['success']:
                            for pos in closed_result['closed_positions']:
                                # Converter timestamp de ms para datetime (usando datetime já importado no topo)
                                closed_from_api.append({
                                    "id": f"api_{pos['symbol']}_{pos['entry_time']}",  # ID temporário
                                    "external_id": None,
                                    "symbol": pos['symbol'],
                                    "side": pos['side'],
                                    "status": "closed",
                                    "size": pos['quantity'],
                                    "entry_price": pos['entry_price'],
                                    "mark_price": pos['exit_price'],
                                    "exit_price": pos['exit_price'],
                                    "unrealized_pnl": 0,
                                    "realized_pnl": pos['realized_pnl'],
                                    "initial_margin": 0,
                                    "maintenance_margin": 0,
                                    "leverage": 1,
                                    "liquidation_price": 0,
                                    "bankruptcy_price": 0,
                                    "opened_at": datetime.fromtimestamp(pos['entry_time'] / 1000).isoformat(),
                                    "closed_at": datetime.fromtimestamp(pos['close_time'] / 1000).isoformat(),
                                    "last_update_at": datetime.fromtimestamp(pos['close_time'] / 1000).isoformat(),
                                    "total_fees": 0,
                                    "funding_fees": 0,
                                    "exchange_account_id": account_id,
                                    "exchange_account_name": account_data['name'],
                                    "exchange": "binance",
                                    "created_at": datetime.fromtimestamp(pos['entry_time'] / 1000).isoformat(),
                                    "updated_at": datetime.fromtimestamp(pos['close_time'] / 1000).isoformat(),
                                    "source": "api"  # Indicador de que veio da API
                                })

                    logger.info(f"✅ Retrieved {len(closed_from_api)} closed positions from Binance API")

                except Exception as e:
                    logger.error(f"Error fetching closed positions from API: {e}")
                    # Continuar mesmo se falhar - retornar só as do banco

            # Combinar posições do banco + API
            all_positions = positions_list + closed_from_api

            # Ordenar por data de criação (mais recentes primeiro)
            all_positions.sort(key=lambda x: x.get('created_at') or '', reverse=True)

            # Aplicar limit se especificado
            if limit and len(all_positions) > limit:
                all_positions = all_positions[:limit]

            logger.info("Positions retrieved",
                       count=len(all_positions),
                       from_db=len(positions_list),
                       from_api=len(closed_from_api),
                       status=status,
                       symbol=symbol,
                       exchange_account_id=exchange_account_id,
                       date_from=date_from,
                       date_to=date_to,
                       limit=limit)

            return {
                "success": True,
                "data": all_positions,
                "metadata": {
                    "total": len(all_positions),
                    "from_database": len(positions_list),
                    "from_api": len(closed_from_api)
                }
            }
            
        except Exception as e:
            logger.error("Error retrieving positions", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve positions")

    @router.get("/metrics")
    async def get_positions_metrics(request: Request):
        """Get positions metrics and statistics"""
        try:
            # Get positions summary
            summary = await transaction_db.fetchrow("""
                SELECT 
                    COUNT(*) as total_positions,
                    COUNT(*) FILTER (WHERE p.status = 'open') as open_positions,
                    COUNT(*) FILTER (WHERE p.status = 'closed') as closed_positions,
                    COALESCE(SUM(p.unrealized_pnl) FILTER (WHERE p.status = 'open'), 0) as total_unrealized_pnl,
                    COALESCE(SUM(p.realized_pnl) FILTER (WHERE p.status = 'closed'), 0) as total_realized_pnl,
                    COALESCE(SUM(p.total_fees), 0) as total_fees_paid,
                    COALESCE(AVG(p.leverage) FILTER (WHERE p.status = 'open'), 0) as avg_leverage
                FROM positions p
                LEFT JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE ea.testnet = false AND ea.is_active = true
            """)
            
            # Get positions by symbol
            by_symbol = await transaction_db.fetch("""
                SELECT 
                    p.symbol,
                    COUNT(*) as count,
                    COUNT(*) FILTER (WHERE p.status = 'open') as open_count,
                    COALESCE(SUM(p.unrealized_pnl) FILTER (WHERE p.status = 'open'), 0) as unrealized_pnl,
                    COALESCE(SUM(p.realized_pnl), 0) as realized_pnl
                FROM positions p
                LEFT JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE ea.testnet = false AND ea.is_active = true
                GROUP BY p.symbol
                ORDER BY count DESC
                LIMIT 10
            """)
            
            # Get positions by exchange
            by_exchange = await transaction_db.fetch("""
                SELECT 
                    ea.exchange,
                    COUNT(p.*) as count,
                    COUNT(p.*) FILTER (WHERE p.status = 'open') as open_count,
                    COALESCE(SUM(p.unrealized_pnl) FILTER (WHERE p.status = 'open'), 0) as unrealized_pnl,
                    COALESCE(SUM(p.realized_pnl), 0) as realized_pnl
                FROM positions p
                LEFT JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE ea.testnet = false AND ea.is_active = true
                GROUP BY ea.exchange
                ORDER BY count DESC
            """)
            
            # Get recent activity
            recent_activity = await transaction_db.fetch("""
                SELECT 
                    p.symbol, p.side, p.status, 
                    p.unrealized_pnl, p.realized_pnl,
                    p.created_at, p.updated_at
                FROM positions p
                LEFT JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE ea.testnet = false AND ea.is_active = true
                ORDER BY p.updated_at DESC
                LIMIT 10
            """)
            
            metrics = {
                "summary": {
                    "total_positions": summary["total_positions"],
                    "open_positions": summary["open_positions"],
                    "closed_positions": summary["closed_positions"],
                    "total_unrealized_pnl": float(summary["total_unrealized_pnl"]),
                    "total_realized_pnl": float(summary["total_realized_pnl"]),
                    "total_fees_paid": float(summary["total_fees_paid"]),
                    "avg_leverage": float(summary["avg_leverage"]) if summary["avg_leverage"] else 0
                },
                "by_symbol": [
                    {
                        "symbol": row["symbol"],
                        "count": row["count"],
                        "open_count": row["open_count"],
                        "unrealized_pnl": float(row["unrealized_pnl"]),
                        "realized_pnl": float(row["realized_pnl"])
                    }
                    for row in by_symbol
                ],
                "by_exchange": [
                    {
                        "exchange": row["exchange"],
                        "count": row["count"],
                        "open_count": row["open_count"],
                        "unrealized_pnl": float(row["unrealized_pnl"]),
                        "realized_pnl": float(row["realized_pnl"])
                    }
                    for row in by_exchange
                ],
                "recent_activity": [
                    {
                        "symbol": row["symbol"],
                        "side": row["side"],
                        "status": row["status"],
                        "unrealized_pnl": float(row["unrealized_pnl"]) if row["unrealized_pnl"] else 0,
                        "realized_pnl": float(row["realized_pnl"]) if row["realized_pnl"] else 0,
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None
                    }
                    for row in recent_activity
                ]
            }
            
            logger.info("Positions metrics retrieved")
            return {"success": True, "data": metrics}
            
        except Exception as e:
            logger.error("Error retrieving positions metrics", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve positions metrics")

    @router.get("/{position_id}")
    async def get_position(position_id: str, request: Request):
        """Get a specific position by ID"""
        try:
            position = await transaction_db.fetchrow("""
                SELECT 
                    p.id, p.external_id, p.symbol, p.side, p.status,
                    p.size, p.entry_price, p.mark_price, 
                    p.unrealized_pnl, p.realized_pnl,
                    p.initial_margin, p.maintenance_margin, p.leverage,
                    p.liquidation_price, p.bankruptcy_price,
                    p.opened_at, p.closed_at, p.last_update_at,
                    p.total_fees, p.funding_fees, p.exchange_data,
                    p.exchange_account_id, p.created_at, p.updated_at,
                    ea.name as exchange_account_name, ea.exchange
                FROM positions p
                LEFT JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE p.id = $1
            """, position_id)
            
            if not position:
                raise HTTPException(status_code=404, detail="Position not found")

            # Calcular P&L %
            size = float(position["size"]) if position["size"] else 0
            entry_price = float(position["entry_price"]) if position["entry_price"] else 0
            unrealized_pnl = float(position["unrealized_pnl"]) if position["unrealized_pnl"] else 0
            leverage = float(position["leverage"]) if position["leverage"] else 1

            # Valor inicial da posição (sem alavancagem)
            position_value = size * entry_price
            # Capital inicial investido (com alavancagem)
            initial_capital = position_value / leverage if leverage > 0 else position_value

            # P&L % = (unrealized_pnl / initial_capital) * 100
            pnl_percentage = (unrealized_pnl / initial_capital * 100) if initial_capital > 0 else 0

            position_data = {
                "id": position["id"],
                "external_id": position["external_id"],
                "symbol": position["symbol"],
                "side": position["side"].upper() if position["side"] else "LONG",
                "status": position["status"],
                "size": size,
                "entry_price": entry_price,
                "mark_price": float(position["mark_price"]) if position["mark_price"] else 0,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_percentage": round(pnl_percentage, 2),  # Novo campo P&L %
                "realized_pnl": float(position["realized_pnl"]) if position["realized_pnl"] else 0,
                "initial_margin": float(position["initial_margin"]) if position["initial_margin"] else 0,
                "maintenance_margin": float(position["maintenance_margin"]) if position["maintenance_margin"] else 0,
                "leverage": leverage,
                "liquidation_price": float(position["liquidation_price"]) if position["liquidation_price"] else 0,
                "bankruptcy_price": float(position["bankruptcy_price"]) if position["bankruptcy_price"] else 0,
                "opened_at": position["opened_at"].isoformat() if position["opened_at"] else None,
                "closed_at": position["closed_at"].isoformat() if position["closed_at"] else None,
                "last_update_at": position["last_update_at"].isoformat() if position["last_update_at"] else None,
                "total_fees": float(position["total_fees"]) if position["total_fees"] else 0,
                "funding_fees": float(position["funding_fees"]) if position["funding_fees"] else 0,
                "exchange_data": position["exchange_data"],
                "exchange_account_id": position["exchange_account_id"],
                "exchange_account_name": position["exchange_account_name"],
                "exchange": position["exchange"],
                "created_at": position["created_at"].isoformat() if position["created_at"] else None,
                "updated_at": position["updated_at"].isoformat() if position["updated_at"] else None
            }
            
            logger.info("Position retrieved", position_id=position_id)
            return {"success": True, "data": position_data}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error retrieving position", position_id=position_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve position")

    return router