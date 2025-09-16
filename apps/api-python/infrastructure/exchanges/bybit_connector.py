"""
Bybit Exchange Connector
Conecta com a API da Bybit para executar ordens e sincronizar dados
"""

import asyncio
import hashlib
import hmac
import time
import aiohttp
from decimal import Decimal
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class BybitConnector:
    """Connector para Bybit API"""

    def __init__(
        self, api_key: str = None, api_secret: str = None, testnet: bool = True
    ):
        """
        Initialize Bybit connector

        Args:
            api_key: Bybit API key
            api_secret: Bybit API secret
            testnet: Use testnet (default True for safety)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        if testnet:
            self.base_url = "https://api-testnet.bybit.com"
        else:
            self.base_url = "https://api.bybit.com"

        self.session = None

    def is_demo_mode(self) -> bool:
        """Check if running in demo mode"""
        return not (self.api_key and self.api_secret)

    async def _get_session(self):
        """Get or create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    def _generate_signature(self, params: dict, timestamp: int) -> str:
        """Generate signature for Bybit API"""
        if not self.api_secret:
            return ""
        
        query_string = f"timestamp={timestamp}"
        for key in sorted(params.keys()):
            query_string += f"&{key}={params[key]}"
        
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    async def _make_request(
        self, method: str, endpoint: str, params: dict = None, signed: bool = False
    ) -> dict:
        """Make HTTP request to Bybit API"""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}

        headers = {
            "Content-Type": "application/json"
        }

        if signed and self.api_key:
            timestamp = int(time.time() * 1000)
            headers["X-BAPI-API-KEY"] = self.api_key
            headers["X-BAPI-TIMESTAMP"] = str(timestamp)
            headers["X-BAPI-SIGN"] = self._generate_signature(params, timestamp)

        try:
            if method == "GET":
                async with session.get(url, params=params, headers=headers) as response:
                    return await response.json()
            elif method == "POST":
                async with session.post(url, json=params, headers=headers) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Bybit API request failed: {e}")
            raise

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Bybit"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "message": "Demo mode - no real connection",
                    "testnet": True,
                    "demo": True,
                }

            # Test connection with account info
            result = await self._make_request("GET", "/v5/account/info", signed=True)
            
            if result.get("retCode") == 0:
                return {
                    "success": True,
                    "message": "Connected to Bybit",
                    "testnet": self.testnet,
                    "demo": False,
                    "account_type": result.get("result", {}).get("accountType", "UNIFIED")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("retMsg", "Unknown error"),
                    "testnet": self.testnet
                }

        except Exception as e:
            logger.error(f"Bybit connection test failed: {e}")
            return {"success": False, "error": str(e), "testnet": self.testnet}

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            if self.is_demo_mode():
                return {
                    "demo": True,
                    "account_type": "DEMO",
                    "balances": [
                        {"coin": "USDT", "walletBalance": "1000.00", "availableBalance": "1000.00"},
                        {"coin": "BTC", "walletBalance": "0.02", "availableBalance": "0.02"},
                        {"coin": "ETH", "walletBalance": "0.5", "availableBalance": "0.5"},
                    ],
                }

            result = await self._make_request("GET", "/v5/account/wallet-balance", {"accountType": "UNIFIED"}, signed=True)
            
            if result.get("retCode") == 0:
                wallet_data = result.get("result", {}).get("list", [])
                balances = []
                
                for wallet in wallet_data:
                    for coin_data in wallet.get("coin", []):
                        balance = float(coin_data.get("walletBalance", "0"))
                        if balance > 0:
                            balances.append({
                                "coin": coin_data.get("coin"),
                                "walletBalance": coin_data.get("walletBalance"),
                                "availableBalance": coin_data.get("availableToWithdraw", "0")
                            })

                return {
                    "demo": False,
                    "account_type": "UNIFIED",
                    "balances": balances,
                }
            else:
                raise Exception(f"Bybit API error: {result.get('retMsg')}")

        except Exception as e:
            logger.error(f"Error getting Bybit account info: {e}")
            raise

    async def get_account_orders(
        self, 
        symbol: str = None, 
        limit: int = 50,
        order_id: str = None,
        start_time: int = None,
        end_time: int = None
    ) -> Dict[str, Any]:
        """Get account order history"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "orders": [
                        {
                            "orderId": "demo_bybit_12345",
                            "symbol": "BTCUSDT",
                            "orderStatus": "Filled",
                            "side": "Buy",
                            "orderType": "Market",
                            "qty": "0.001",
                            "price": "45000.00",
                            "cumExecQty": "0.001",
                            "avgPrice": "45000.00",
                            "createdTime": "1640995200000",
                            "updatedTime": "1640995200000"
                        }
                    ],
                    "total": 1
                }

            params = {
                "category": "spot",
                "limit": min(limit, 50)
            }
            
            if symbol:
                params["symbol"] = symbol.upper()
            if order_id:
                params["orderId"] = order_id
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time

            result = await self._make_request("GET", "/v5/order/history", params, signed=True)
            
            if result.get("retCode") == 0:
                orders = result.get("result", {}).get("list", [])
                return {
                    "success": True,
                    "demo": False,
                    "orders": orders,
                    "total": len(orders)
                }
            else:
                return {
                    "success": False,
                    "error": result.get("retMsg", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error getting Bybit account orders: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_account_trades(
        self, 
        symbol: str = None, 
        limit: int = 50,
        start_time: int = None,
        end_time: int = None
    ) -> Dict[str, Any]:
        """Get account trade history"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "trades": [
                        {
                            "symbol": "BTCUSDT",
                            "execId": "demo_trade_123",
                            "orderId": "demo_bybit_12345",
                            "side": "Buy",
                            "execPrice": "45000.00",
                            "execQty": "0.001",
                            "execValue": "45.00",
                            "feeRate": "0.001",
                            "execFee": "0.045",
                            "execTime": "1640995200000"
                        }
                    ],
                    "total": 1
                }

            params = {
                "category": "spot",
                "limit": min(limit, 50)
            }
            
            if symbol:
                params["symbol"] = symbol.upper()
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time

            result = await self._make_request("GET", "/v5/execution/list", params, signed=True)
            
            if result.get("retCode") == 0:
                trades = result.get("result", {}).get("list", [])
                return {
                    "success": True,
                    "demo": False,
                    "trades": trades,
                    "total": len(trades)
                }
            else:
                return {
                    "success": False,
                    "error": result.get("retMsg", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error getting Bybit account trades: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_account_balances(self) -> Dict[str, Any]:
        """Get account balances"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "balances": [
                        {"coin": "USDT", "walletBalance": "1000.00", "availableBalance": "1000.00"},
                        {"coin": "BTC", "walletBalance": "0.02", "availableBalance": "0.02"},
                        {"coin": "ETH", "walletBalance": "0.5", "availableBalance": "0.5"},
                    ]
                }

            result = await self._make_request("GET", "/v5/account/wallet-balance", {"accountType": "UNIFIED"}, signed=True)
            
            if result.get("retCode") == 0:
                wallet_data = result.get("result", {}).get("list", [])
                balances = []
                
                for wallet in wallet_data:
                    for coin_data in wallet.get("coin", []):
                        balance = float(coin_data.get("walletBalance", "0"))
                        if balance > 0:
                            balances.append({
                                "coin": coin_data.get("coin"),
                                "walletBalance": coin_data.get("walletBalance"),
                                "availableBalance": coin_data.get("availableToWithdraw", "0")
                            })

                return {
                    "success": True,
                    "demo": False,
                    "balances": balances
                }
            else:
                return {
                    "success": False,
                    "error": result.get("retMsg", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error getting Bybit account balances: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_futures_positions(self) -> Dict[str, Any]:
        """Get futures positions"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "positions": [
                        {
                            "symbol": "BTCUSDT",
                            "side": "Buy",
                            "size": "0.001",
                            "avgPrice": "45000.0",
                            "markPrice": "45100.0",
                            "unrealisedPnl": "0.1",
                            "leverage": "10",
                            "positionValue": "45.1",
                            "createdTime": "1640995200000",
                            "updatedTime": "1640995200000"
                        }
                    ]
                }

            params = {
                "category": "linear",  # USDT perpetual
                "settleCoin": "USDT"
            }

            result = await self._make_request("GET", "/v5/position/list", params, signed=True)
            
            if result.get("retCode") == 0:
                positions = result.get("result", {}).get("list", [])
                # Filter only positions with size > 0
                active_positions = [p for p in positions if float(p.get("size", "0")) > 0]
                
                return {
                    "success": True,
                    "demo": False,
                    "positions": active_positions
                }
            else:
                return {
                    "success": False,
                    "error": result.get("retMsg", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error getting Bybit futures positions: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def create_market_order(
        self,
        symbol: str,
        side: str,  # 'Buy' or 'Sell'
        quantity: Decimal,
        test_order: bool = None,
    ) -> Dict[str, Any]:
        """Create market order on Bybit"""
        if test_order is None:
            test_order = self.is_demo_mode() or self.testnet

        try:
            symbol = symbol.upper()
            side = side.capitalize()  # 'Buy' or 'Sell'

            if self.is_demo_mode():
                demo_order = {
                    "success": True,
                    "demo": True,
                    "order_id": f"demo_bybit_{symbol}_{side}_{int(time.time())}",
                    "symbol": symbol,
                    "side": side,
                    "type": "Market",
                    "quantity": str(quantity),
                    "status": "Filled",
                    "filled_quantity": str(quantity),
                    "average_price": "45000.00" if "BTC" in symbol else "2500.00",
                    "timestamp": int(time.time() * 1000),
                }
                return demo_order

            # Real order for Bybit
            params = {
                "category": "spot",
                "symbol": symbol,
                "side": side,
                "orderType": "Market",
                "qty": str(quantity),
                "timeInForce": "IOC"
            }

            result = await self._make_request("POST", "/v5/order/create", params, signed=True)
            
            if result.get("retCode") == 0:
                order_data = result.get("result", {})
                return {
                    "success": True,
                    "demo": False,
                    "order_id": order_data.get("orderId"),
                    "symbol": symbol,
                    "side": side,
                    "type": "Market",
                    "quantity": str(quantity),
                    "status": "Created",
                    "timestamp": int(time.time() * 1000),
                    "raw_response": result
                }
            else:
                return {
                    "success": False,
                    "error": result.get("retMsg", "Unknown error"),
                    "code": result.get("retCode")
                }

        except Exception as e:
            logger.error(f"Error creating Bybit market order: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()


# Factory function
def create_bybit_connector(
    api_key: str = None, api_secret: str = None, testnet: bool = True
) -> BybitConnector:
    """Create Bybit connector instance"""
    return BybitConnector(api_key=api_key, api_secret=api_secret, testnet=testnet)