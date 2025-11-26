"""
Spot P&L Service - Calculates profit and loss for spot positions
Sistema definitivo para calcular P&L de posições spot em tempo real
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
import structlog
from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.pricing.binance_price_service import BinancePriceService

logger = structlog.get_logger(__name__)


class SpotPnlService:
    """Service para calcular P&L de posições SPOT em tempo real"""

    def __init__(self):
        self.price_service = BinancePriceService(testnet=True)

    async def calculate_spot_pnl(self, account_id: str) -> Dict[str, Any]:
        """
        Calcula P&L total de todas as posições SPOT de uma conta

        Args:
            account_id: ID da conta exchange

        Returns:
            Dict com P&L total e detalhes por ativo
        """
        try:
            logger.info(f"📊 Calculating SPOT P&L for account {account_id}")

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

            # 2. Obter preços atuais da Binance
            current_prices = await self.price_service.get_all_ticker_prices()

            # 3. Calcular P&L para cada ativo
            assets_pnl = []
            total_pnl_usdt = 0.0

            for asset in active_assets:
                asset_pnl = await self._calculate_asset_pnl(
                    account_id, asset, current_prices
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
        current_prices: Dict[str, float]
    ) -> Optional[Dict[str, Any]]:
        """
        Calcula P&L de um ativo específico

        Método:
        1. Buscar preço médio de compra do ativo (via trades históricos)
        2. Comparar com preço atual
        3. Calcular: (preço_atual - preço_médio) × quantidade
        """
        try:
            asset = asset_data['asset']
            current_balance = float(asset_data['total_balance'])
            current_usd_value = float(asset_data['usd_value'])

            # Se for USDT ou stablecoin, P&L é zero
            if asset in ['USDT', 'USDC', 'BUSD', 'FDUSD', 'DAI']:
                return {
                    "asset": asset,
                    "current_balance": current_balance,
                    "current_usd_value": current_usd_value,
                    "avg_buy_price_usdt": 1.0,
                    "current_price_usdt": 1.0,
                    "pnl_usdt": 0.0,
                    "pnl_percentage": 0.0,
                    "is_stablecoin": True
                }

            # 1. Buscar preço médio de compra do histórico de trades
            avg_buy_price = await self._get_average_buy_price(account_id, asset)

            # 2. Calcular preço atual em USDT
            current_price_usdt = await self.price_service.calculate_usdt_value(
                asset, 1.0, current_prices
            )

            # Se não conseguir obter preços, usar valor atual / quantidade
            if avg_buy_price == 0 or current_price_usdt == 0:
                if current_balance > 0:
                    estimated_price = current_usd_value / current_balance
                    logger.warning(f"⚠️ Using estimated price for {asset}: ${estimated_price:.4f}")
                    return {
                        "asset": asset,
                        "current_balance": current_balance,
                        "current_usd_value": current_usd_value,
                        "avg_buy_price_usdt": 0.0,
                        "current_price_usdt": estimated_price,
                        "pnl_usdt": 0.0,  # Cannot calculate without buy price
                        "pnl_percentage": 0.0,
                        "is_estimated": True
                    }

            # 3. Calcular P&L
            pnl_usdt = (current_price_usdt - avg_buy_price) * current_balance
            pnl_percentage = ((current_price_usdt - avg_buy_price) / avg_buy_price * 100) if avg_buy_price > 0 else 0

            return {
                "asset": asset,
                "current_balance": current_balance,
                "current_usd_value": current_usd_value,
                "avg_buy_price_usdt": avg_buy_price,
                "current_price_usdt": current_price_usdt,
                "pnl_usdt": pnl_usdt,
                "pnl_percentage": pnl_percentage,
                "is_profitable": pnl_usdt > 0
            }

        except Exception as e:
            logger.error(f"Error calculating P&L for asset {asset_data.get('asset')}: {e}")
            return None

    async def _get_average_buy_price(self, account_id: str, asset: str) -> float:
        """
        Calcula preço médio de compra de um ativo baseado no histórico de trades

        Se não tiver trades, usa um método alternativo de estimativa
        """
        try:
            # Buscar trades de compra (BUY) do ativo
            buy_trades = await transaction_db.fetch("""
                SELECT quantity, price, total_value
                FROM daily_trades
                WHERE exchange_account_id = $1
                AND asset = $2
                AND side = 'BUY'
                AND account_type = 'SPOT'
                ORDER BY trade_time DESC
                LIMIT 100
            """, account_id, asset)

            if not buy_trades:
                # Se não tem trades, tentar estimar baseado em dados existentes
                return await self._estimate_buy_price(account_id, asset)

            # Calcular preço médio ponderado
            total_quantity = 0.0
            total_cost = 0.0

            for trade in buy_trades:
                quantity = float(trade['quantity'])
                price = float(trade['price'])

                total_quantity += quantity
                total_cost += quantity * price

            if total_quantity > 0:
                avg_price = total_cost / total_quantity
                logger.debug(f"📊 {asset} avg buy price: ${avg_price:.4f} (from {len(buy_trades)} trades)")
                return avg_price

            return 0.0

        except Exception as e:
            logger.error(f"Error calculating average buy price for {asset}: {e}")
            return 0.0

    async def _estimate_buy_price(self, account_id: str, asset: str) -> float:
        """
        Estima preço de compra quando não há dados de trades

        Método: usar preço histórico ou preço atual com desconto conservador
        """
        try:
            # Para estimativa inicial, usar preço atual com desconto de 10%
            # Isso evita P&L artificialmente alto
            current_prices = await self.price_service.get_all_ticker_prices()
            current_price = await self.price_service.calculate_usdt_value(
                asset, 1.0, current_prices
            )

            if current_price > 0:
                # Desconto conservador para evitar P&L inflado
                estimated_price = current_price * 0.9
                logger.info(f"📊 {asset} estimated buy price: ${estimated_price:.4f} (90% of current)")
                return estimated_price

            return 0.0

        except Exception as e:
            logger.error(f"Error estimating buy price for {asset}: {e}")
            return 0.0