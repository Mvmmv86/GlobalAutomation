"""
Spot P&L Service - Calculates profit and loss for spot positions
Sistema definitivo para calcular P&L de posições spot em tempo real
Usando histórico REAL de trades da exchange (BingX/Binance)
"""

import time
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
import structlog
from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.pricing.binance_price_service import BinancePriceService

logger = structlog.get_logger(__name__)

# Cache para trades históricos (evita rate limits)
# Estrutura: {account_id: {asset: {"trades": [...], "timestamp": float, "avg_price": float}}}
_trades_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
TRADES_CACHE_TTL = 300  # 5 minutos de cache


class SpotPnlService:
    """Service para calcular P&L de posições SPOT em tempo real usando histórico de trades"""

    def __init__(self, connector=None):
        """
        Args:
            connector: Exchange connector (BingXConnector, BinanceConnector, etc.)
                      Se não fornecido, será criado baseado na conta
        """
        self.price_service = BinancePriceService(testnet=False)
        self.connector = connector

    async def calculate_spot_pnl(self, account_id: str, connector=None) -> Dict[str, Any]:
        """
        Calcula P&L total de todas as posições SPOT de uma conta
        USANDO HISTÓRICO REAL DE TRADES DA EXCHANGE

        Args:
            account_id: ID da conta exchange
            connector: Exchange connector (opcional, será criado se não fornecido)

        Returns:
            Dict com P&L total e detalhes por ativo
        """
        try:
            logger.info(f"📊 Calculating SPOT P&L for account {account_id} (using real trade history)")

            # Usar connector fornecido ou criar um novo
            exchange_connector = connector or self.connector

            # Se não tiver connector, buscar dados da conta e criar
            if not exchange_connector:
                exchange_connector = await self._create_connector_for_account(account_id)

            # 1. Buscar todos os assets SPOT ativos (com saldo > 0)
            active_assets = await self._get_active_spot_assets(account_id)

            if not active_assets:
                return {
                    "success": True,
                    "total_pnl_usdt": 0.0,
                    "active_assets_count": 0,
                    "assets_pnl": [],
                    "message": "No active SPOT assets found"
                }

            # 2. Obter preços atuais
            current_prices = await self.price_service.get_all_ticker_prices()

            # 3. Calcular P&L para cada ativo
            assets_pnl = []
            total_pnl_usdt = 0.0

            for asset in active_assets:
                asset_pnl = await self._calculate_asset_pnl(
                    account_id, asset, current_prices, exchange_connector
                )
                if asset_pnl:
                    assets_pnl.append(asset_pnl)
                    total_pnl_usdt += asset_pnl['pnl_usdt']

            # 4. Contar apenas assets com posição ativa (não zerados)
            active_count = len([a for a in assets_pnl if a['current_balance'] > 0.01])

            logger.info(f"✅ SPOT P&L calculated: ${total_pnl_usdt:.2f} USDT ({active_count} active assets)")

            return {
                "success": True,
                "total_pnl_usdt": total_pnl_usdt,
                "active_assets_count": active_count,
                "assets_pnl": assets_pnl,
                "calculation_time": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating SPOT P&L: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_pnl_usdt": 0.0,
                "active_assets_count": 0,
                "assets_pnl": []
            }

    async def _create_connector_for_account(self, account_id: str):
        """Cria um connector baseado nos dados da conta"""
        try:
            account = await transaction_db.fetchrow("""
                SELECT exchange, api_key, secret_key, testnet, passphrase
                FROM exchange_accounts
                WHERE id = $1 AND is_active = true
            """, account_id)

            if not account:
                logger.warning(f"Account {account_id} not found")
                return None

            exchange = account['exchange'].lower()

            if exchange == 'bingx':
                from infrastructure.exchanges.bingx_connector import BingXConnector
                return BingXConnector(
                    api_key=account['api_key'],
                    api_secret=account['secret_key'],
                    testnet=account['testnet']
                )
            elif exchange == 'binance':
                from infrastructure.exchanges.binance_connector import BinanceConnector
                return BinanceConnector(
                    api_key=account['api_key'],
                    api_secret=account['secret_key'],
                    testnet=account['testnet']
                )
            else:
                logger.warning(f"Unsupported exchange for spot P&L: {exchange}")
                return None

        except Exception as e:
            logger.error(f"Error creating connector for account {account_id}: {e}")
            return None

    async def _get_active_spot_assets(self, account_id: str) -> List[Dict]:
        """Busca todos os assets SPOT com saldo > 0"""
        try:
            assets = await transaction_db.fetch("""
                SELECT asset, total_balance, usd_value
                FROM exchange_account_balances
                WHERE exchange_account_id = $1
                AND account_type = 'SPOT'
                AND total_balance > 0.001
                ORDER BY usd_value DESC
            """, account_id)

            return [dict(asset) for asset in assets]

        except Exception as e:
            logger.error(f"Error fetching active SPOT assets: {e}")
            return []

    async def _calculate_asset_pnl(
        self,
        account_id: str,
        asset_data: Dict,
        current_prices: Dict[str, float],
        connector=None
    ) -> Optional[Dict[str, Any]]:
        """
        Calcula P&L de um ativo específico usando histórico REAL de trades

        Método:
        1. Buscar trades do ativo via API da exchange (myTrades)
        2. Calcular preço médio ponderado dos BUY trades
        3. Comparar com preço atual
        4. Calcular: (preço_atual - preço_médio) × quantidade
        """
        try:
            asset = asset_data['asset']
            current_balance = float(asset_data['total_balance'])
            current_usd_value = float(asset_data['usd_value'])

            # Se for USDT ou stablecoin, P&L é zero
            if asset in ['USDT', 'USDC', 'BUSD', 'FDUSD', 'DAI', 'TUSD']:
                return {
                    "asset": asset,
                    "current_balance": current_balance,
                    "current_usd_value": current_usd_value,
                    "avg_buy_price_usdt": 1.0,
                    "current_price_usdt": 1.0,
                    "pnl_usdt": 0.0,
                    "pnl_percentage": 0.0,
                    "is_stablecoin": True,
                    "is_profitable": False,
                    "avg_price_source": "stablecoin",
                    "current_price_source": "stablecoin"
                }

            # 1. Buscar preço médio de compra do histórico de trades (API)
            avg_buy_price, source = await self._get_average_buy_price_from_exchange(
                account_id, asset, connector
            )

            # 2. Calcular preço atual em USDT (COM FALLBACK BINANCE → BINGX)
            current_price_usdt = 0.0
            price_source = "unknown"

            # Primeiro tenta Binance via price_service
            current_price_usdt = await self.price_service.calculate_usdt_value(
                asset, 1.0, current_prices
            )

            if current_price_usdt > 0:
                price_source = "binance"
            else:
                # FALLBACK: Se Binance não tiver o preço, buscar do BingX via connector
                if connector and hasattr(connector, '_get_asset_price_in_usdt'):
                    try:
                        bingx_price, source = await connector._get_asset_price_in_usdt(asset)
                        if bingx_price and bingx_price > 0:
                            current_price_usdt = bingx_price
                            price_source = source.lower()  # "binance" or "bingx"
                            logger.info(f"💱 {asset}: Got price ${current_price_usdt:.4f} from {price_source} (fallback)")
                    except Exception as price_err:
                        logger.warning(f"⚠️ {asset}: Fallback price fetch failed: {price_err}")

                # Se ainda não tiver preço, usar valor do banco (usd_value / balance)
                if current_price_usdt == 0:
                    if current_balance > 0 and current_usd_value > 0:
                        current_price_usdt = current_usd_value / current_balance
                        price_source = "db_calculated"

            # Se não conseguir obter preço de compra, usar estimativa
            if avg_buy_price == 0:
                # Fallback: estimar como 95% do preço atual (conservador)
                if current_price_usdt > 0:
                    avg_buy_price = current_price_usdt * 0.95
                    source = "estimated_95%"
                    logger.info(f"📊 {asset}: Using estimated buy price ${avg_buy_price:.4f} (95% of current)")

            # 3. Calcular P&L
            if avg_buy_price > 0 and current_price_usdt > 0:
                pnl_usdt = (current_price_usdt - avg_buy_price) * current_balance
                pnl_percentage = ((current_price_usdt - avg_buy_price) / avg_buy_price * 100)
            else:
                pnl_usdt = 0.0
                pnl_percentage = 0.0

            return {
                "asset": asset,
                "current_balance": current_balance,
                "current_usd_value": current_usd_value,
                "avg_buy_price_usdt": avg_buy_price,
                "current_price_usdt": current_price_usdt,
                "pnl_usdt": pnl_usdt,
                "pnl_percentage": pnl_percentage,
                "is_profitable": pnl_usdt > 0,
                "avg_price_source": source,  # "exchange_trades", "db_orders", "estimated_95%"
                "current_price_source": price_source  # "binance", "bingx", "db_calculated"
            }

        except Exception as e:
            logger.error(f"Error calculating P&L for asset {asset_data.get('asset')}: {e}")
            return None

    async def _get_average_buy_price_from_exchange(
        self,
        account_id: str,
        asset: str,
        connector=None
    ) -> tuple[float, str]:
        """
        Busca preço médio de compra REAL usando API da exchange

        Prioridade:
        1. Cache (se válido)
        2. API da exchange (myTrades)
        3. Tabela orders do nosso DB
        4. Estimativa

        Returns:
            tuple: (avg_price, source)
        """
        try:
            # 1. Verificar cache
            cache_key = f"{account_id}_{asset}"
            if account_id in _trades_cache and asset in _trades_cache[account_id]:
                cached = _trades_cache[account_id][asset]
                if time.time() - cached.get('timestamp', 0) < TRADES_CACHE_TTL:
                    logger.debug(f"📦 {asset}: Using cached avg price ${cached['avg_price']:.4f}")
                    return cached['avg_price'], "cache"

            # 2. Tentar buscar da API da exchange
            if connector and hasattr(connector, 'get_account_trades'):
                try:
                    symbol = f"{asset}-USDT"  # BingX format
                    trades_result = await connector.get_account_trades(symbol=symbol, limit=500)

                    if trades_result.get('success') and trades_result.get('trades'):
                        trades = trades_result['trades']

                        # Filtrar apenas BUY trades
                        buy_trades = [t for t in trades if str(t.get('side', '')).upper() == 'BUY']

                        if buy_trades:
                            # Calcular preço médio ponderado
                            total_qty = 0.0
                            total_cost = 0.0

                            for trade in buy_trades:
                                qty = float(trade.get('qty', trade.get('quantity', 0)))
                                price = float(trade.get('price', 0))

                                if qty > 0 and price > 0:
                                    total_qty += qty
                                    total_cost += qty * price

                            if total_qty > 0:
                                avg_price = total_cost / total_qty

                                # Salvar no cache
                                if account_id not in _trades_cache:
                                    _trades_cache[account_id] = {}
                                _trades_cache[account_id][asset] = {
                                    'avg_price': avg_price,
                                    'timestamp': time.time(),
                                    'trades_count': len(buy_trades)
                                }

                                logger.info(f"✅ {asset}: Real avg buy price ${avg_price:.4f} (from {len(buy_trades)} trades)")
                                return avg_price, "exchange_trades"

                except Exception as api_err:
                    logger.warning(f"⚠️ Error fetching trades from exchange for {asset}: {api_err}")

            # 3. Fallback: Buscar da tabela orders do nosso DB
            avg_price_db = await self._get_avg_price_from_db_orders(account_id, asset)
            if avg_price_db > 0:
                return avg_price_db, "db_orders"

            # 4. Não encontrou nenhum trade
            return 0.0, "not_found"

        except Exception as e:
            logger.error(f"Error getting average buy price for {asset}: {e}")
            return 0.0, "error"

    async def _get_avg_price_from_db_orders(self, account_id: str, asset: str) -> float:
        """
        Busca preço médio de compra da tabela orders (compras feitas pelo sistema)
        """
        try:
            # Buscar ordens BUY preenchidas para este ativo
            orders = await transaction_db.fetch("""
                SELECT quantity, price, filled_quantity, average_fill_price
                FROM orders
                WHERE exchange_account_id = $1
                AND (symbol LIKE $2 OR symbol LIKE $3)
                AND LOWER(side::text) = 'buy'
                AND status = 'filled'
                ORDER BY created_at DESC
                LIMIT 100
            """, account_id, f"{asset}USDT", f"{asset}-USDT")

            if not orders:
                return 0.0

            total_qty = 0.0
            total_cost = 0.0

            for order in orders:
                # Usar filled_quantity e average_fill_price se disponíveis
                qty = float(order.get('filled_quantity') or order.get('quantity') or 0)
                price = float(order.get('average_fill_price') or order.get('price') or 0)

                if qty > 0 and price > 0:
                    total_qty += qty
                    total_cost += qty * price

            if total_qty > 0:
                avg_price = total_cost / total_qty
                logger.info(f"📊 {asset}: Avg buy price from DB orders: ${avg_price:.4f} ({len(orders)} orders)")
                return avg_price

            return 0.0

        except Exception as e:
            logger.error(f"Error getting avg price from DB orders for {asset}: {e}")
            return 0.0
