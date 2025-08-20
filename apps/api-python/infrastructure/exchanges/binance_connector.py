"""
Binance Exchange Connector
Conecta com a API da Binance para executar ordens reais
"""

import asyncio
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from decimal import Decimal
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class BinanceConnector:
    """Connector para Binance API"""

    def __init__(
        self, api_key: str = None, api_secret: str = None, testnet: bool = True
    ):
        """
        Initialize Binance connector

        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet (default True for safety)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        # Configurar client
        if api_key and api_secret:
            self.client = Client(
                api_key=api_key, api_secret=api_secret, testnet=testnet
            )
        else:
            # Modo demo (sem API keys)
            self.client = None
            logger.warning("Binance connector initialized in DEMO mode (no API keys)")

    def is_demo_mode(self) -> bool:
        """Check if running in demo mode"""
        return self.client is None

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Binance"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "message": "Demo mode - no real connection",
                    "testnet": True,
                    "demo": True,
                }

            # Test real connection
            status = self.client.get_system_status()
            account_info = self.client.get_account()

            return {
                "success": True,
                "message": "Connected to Binance",
                "status": status,
                "testnet": self.testnet,
                "demo": False,
                "balances_count": len(account_info.get("balances", [])),
            }

        except Exception as e:
            logger.error(f"Binance connection test failed: {e}")
            return {"success": False, "error": str(e), "testnet": self.testnet}

    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information"""
        try:
            if self.is_demo_mode():
                # Demo data
                return {
                    "symbol": symbol.upper(),
                    "status": "TRADING",
                    "base_asset": symbol[:-4],  # Remove USDT
                    "quote_asset": "USDT",
                    "min_qty": "0.00001000",
                    "step_size": "0.00001000",
                    "tick_size": "0.01000000",
                    "demo": True,
                }

            # Real symbol info
            info = self.client.get_symbol_info(symbol.upper())
            if not info:
                raise Exception(f"Symbol {symbol} not found")

            # Extract important filters
            filters = {f["filterType"]: f for f in info.get("filters", [])}

            return {
                "symbol": info["symbol"],
                "status": info["status"],
                "base_asset": info["baseAsset"],
                "quote_asset": info["quoteAsset"],
                "min_qty": filters.get("LOT_SIZE", {}).get("minQty", "0.00001"),
                "step_size": filters.get("LOT_SIZE", {}).get("stepSize", "0.00001"),
                "tick_size": filters.get("PRICE_FILTER", {}).get("tickSize", "0.01"),
                "demo": False,
            }

        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            raise

    async def get_current_price(self, symbol: str) -> Decimal:
        """Get current market price"""
        try:
            if self.is_demo_mode():
                # Demo prices
                demo_prices = {
                    "BTCUSDT": "45000.00",
                    "ETHUSDT": "2500.00",
                    "ADAUSDT": "0.35",
                    "SOLUSDT": "100.00",
                }
                price = demo_prices.get(symbol.upper(), "1.00")
                return Decimal(price)

            # Real price
            ticker = self.client.get_symbol_ticker(symbol=symbol.upper())
            return Decimal(ticker["price"])

        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            raise

    async def create_market_order(
        self,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        quantity: Decimal,
        test_order: bool = None,
    ) -> Dict[str, Any]:
        """
        Create market order

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            side: buy or sell
            quantity: Order quantity
            test_order: If True, only test the order (default: auto based on demo mode)
        """

        if test_order is None:
            test_order = self.is_demo_mode() or self.testnet

        try:
            symbol = symbol.upper()
            side = side.upper()

            # Validate inputs
            if side not in ["BUY", "SELL"]:
                raise ValueError(f"Invalid side: {side}. Must be 'buy' or 'sell'")

            if quantity <= 0:
                raise ValueError(f"Invalid quantity: {quantity}. Must be positive")

            # Format quantity (remove excessive decimals)
            quantity_str = f"{float(quantity):.8f}".rstrip("0").rstrip(".")

            if self.is_demo_mode():
                # Demo order simulation
                current_price = await self.get_current_price(symbol)

                demo_order = {
                    "success": True,
                    "demo": True,
                    "order_id": f"demo_{symbol}_{side}_{int(asyncio.get_event_loop().time())}",
                    "symbol": symbol,
                    "side": side,
                    "type": "MARKET",
                    "quantity": quantity_str,
                    "price": str(current_price),
                    "status": "FILLED",
                    "filled_quantity": quantity_str,
                    "average_price": str(current_price),
                    "commission": str(
                        Decimal(quantity_str) * Decimal("0.001")
                    ),  # 0.1% commission
                    "commission_asset": "USDT"
                    if side == "SELL"
                    else symbol.replace("USDT", ""),
                    "timestamp": int(asyncio.get_event_loop().time() * 1000),
                }

                logger.info(f"Demo order created: {demo_order['order_id']}")
                return demo_order

            # Real order
            if test_order:
                # Test order (não executa realmente)
                result = self.client.create_test_order(
                    symbol=symbol,
                    side=side,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=quantity_str,
                )

                # Test order returns empty dict on success
                current_price = await self.get_current_price(symbol)

                return {
                    "success": True,
                    "demo": False,
                    "test_order": True,
                    "order_id": f"test_{symbol}_{side}_{int(asyncio.get_event_loop().time())}",
                    "symbol": symbol,
                    "side": side,
                    "type": "MARKET",
                    "quantity": quantity_str,
                    "price": str(current_price),
                    "status": "TEST_ORDER",
                    "message": "Test order successful - would have been executed",
                }
            else:
                # Real order execution
                result = self.client.order_market(
                    symbol=symbol, side=side, quantity=quantity_str
                )

                return {
                    "success": True,
                    "demo": False,
                    "test_order": False,
                    "order_id": str(result["orderId"]),
                    "symbol": result["symbol"],
                    "side": result["side"],
                    "type": result["type"],
                    "quantity": result["origQty"],
                    "price": result.get("price", "0"),
                    "status": result["status"],
                    "filled_quantity": result.get("executedQty", "0"),
                    "average_price": result.get("avgPrice", "0"),
                    "commission": result.get("commission", "0"),
                    "timestamp": result["transactTime"],
                    "raw_response": result,
                }

        except BinanceAPIException as e:
            logger.error(f"Binance API error: {e}")
            return {
                "success": False,
                "error": f"Binance API error: {e.message}",
                "code": e.code,
            }
        except BinanceOrderException as e:
            logger.error(f"Binance order error: {e}")
            return {
                "success": False,
                "error": f"Order error: {e.message}",
                "code": e.code,
            }
        except Exception as e:
            logger.error(f"Unexpected error creating order: {e}")
            return {"success": False, "error": str(e)}

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            if self.is_demo_mode():
                return {
                    "demo": True,
                    "account_type": "DEMO",
                    "balances": [
                        {"asset": "USDT", "free": "1000.00", "locked": "0.00"},
                        {"asset": "BTC", "free": "0.02", "locked": "0.00"},
                        {"asset": "ETH", "free": "0.5", "locked": "0.00"},
                    ],
                }

            account = self.client.get_account()

            # Filter only balances with value > 0
            active_balances = [
                b
                for b in account.get("balances", [])
                if float(b["free"]) > 0 or float(b["locked"]) > 0
            ]

            return {
                "demo": False,
                "account_type": account.get("accountType", "SPOT"),
                "can_trade": account.get("canTrade", False),
                "can_withdraw": account.get("canWithdraw", False),
                "can_deposit": account.get("canDeposit", False),
                "balances": active_balances,
            }

        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            raise


# Factory function para criar connector
def create_binance_connector(
    api_key: str = None, api_secret: str = None, testnet: bool = True
) -> BinanceConnector:
    """Create Binance connector instance"""
    return BinanceConnector(api_key=api_key, api_secret=api_secret, testnet=testnet)
