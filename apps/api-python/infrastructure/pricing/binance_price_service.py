"""
Binance Price Service - Real-time price conversion to USDT
"""

import structlog
from typing import Dict, Any
import requests

logger = structlog.get_logger(__name__)


class BinancePriceService:
    """Service for real-time price conversion using Binance API"""

    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.base_url = "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        self._price_cache = {}

    async def get_all_ticker_prices(self) -> Dict[str, float]:
        """Get all ticker prices from Binance API"""
        try:
            url = f"{self.base_url}/api/v3/ticker/price"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                ticker_data = response.json()
                prices = {item['symbol']: float(item['price']) for item in ticker_data}
                logger.info(f"✅ Fetched {len(prices)} ticker prices from Binance")
                return prices
            else:
                logger.error(f"❌ Failed to fetch prices: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"❌ Error fetching Binance prices: {e}")
            return {}

    async def calculate_usdt_value(self, asset: str, amount: float, prices: Dict[str, float]) -> float:
        """
        Calculate USDT value for a given asset and amount
        Uses the same logic as show_binance_balances.py
        """
        if amount <= 0:
            return 0.0

        # Direct USDT assets
        if asset in ['USDT', 'USDC', 'BUSD', 'FDUSD']:
            return amount

        # BRL special case (approximate conversion)
        if asset == 'BRL':
            return amount * 0.18  # 1 BRL ≈ 0.18 USD

        # Try to find price in different pair formats
        usdt_value = 0.0

        # Try {ASSET}USDT pair
        symbol_usdt = f"{asset}USDT"
        if symbol_usdt in prices:
            usdt_value = amount * prices[symbol_usdt]
            logger.debug(f"💰 {asset}: {amount} * {prices[symbol_usdt]} = ${usdt_value:.2f}")
            return usdt_value

        # Try {ASSET}BUSD pair with BUSD/USDT conversion
        symbol_busd = f"{asset}BUSD"
        busd_usdt = "BUSDUSDT"
        if symbol_busd in prices and busd_usdt in prices:
            usdt_value = amount * prices[symbol_busd] * prices[busd_usdt]
            logger.debug(f"💰 {asset}: {amount} * {prices[symbol_busd]} * {prices[busd_usdt]} = ${usdt_value:.2f}")
            return usdt_value

        # Try {ASSET}USDC pair with USDC/USDT conversion
        symbol_usdc = f"{asset}USDC"
        usdc_usdt = "USDCUSDT"
        if symbol_usdc in prices and usdc_usdt in prices:
            usdt_value = amount * prices[symbol_usdc] * prices[usdc_usdt]
            logger.debug(f"💰 {asset}: {amount} * {prices[symbol_usdc]} * {prices[usdc_usdt]} = ${usdt_value:.2f}")
            return usdt_value

        # If no price found, log and return 0
        logger.warning(f"⚠️ No price found for {asset}, setting value to $0")
        return 0.0

    async def convert_balances_to_usdt(self, balances: list, account_type: str = "SPOT") -> Dict[str, Any]:
        """
        Convert a list of balances to USDT values
        Returns summary with total value and detailed breakdown
        """
        logger.info(f"🔄 Converting {len(balances)} {account_type} balances to USDT")

        # Get current prices
        prices = await self.get_all_ticker_prices()
        if not prices:
            logger.error("❌ Cannot convert balances - no price data available")
            return {"total_usdt": 0.0, "converted_balances": [], "error": "No price data"}

        total_usdt_value = 0.0
        converted_balances = []

        for balance in balances:
            asset = balance.get('asset', '')

            # Handle different balance formats
            if 'total' in balance:
                amount = float(balance['total'])
            elif 'walletBalance' in balance:  # Futures format
                amount = float(balance['walletBalance'])
            else:
                free = float(balance.get('free', 0))
                locked = float(balance.get('locked', 0))
                amount = free + locked

            if amount > 0:
                usdt_value = await self.calculate_usdt_value(asset, amount, prices)

                converted_balance = {
                    'asset': asset,
                    'amount': amount,
                    'usdt_value': usdt_value,
                    'account_type': account_type
                }

                converted_balances.append(converted_balance)
                total_usdt_value += usdt_value

                if usdt_value > 0.01:  # Log only significant values
                    logger.info(f"💰 {account_type} {asset}: {amount:.8f} = ${usdt_value:.2f}")

        # Sort by USDT value (highest first)
        converted_balances.sort(key=lambda x: x['usdt_value'], reverse=True)

        logger.info(f"✅ {account_type} total: ${total_usdt_value:.2f} USDT from {len(converted_balances)} assets")

        return {
            "total_usdt": total_usdt_value,
            "converted_balances": converted_balances,
            "prices_count": len(prices),
            "account_type": account_type
        }