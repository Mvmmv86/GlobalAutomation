"""
BingX Exchange Connector
Conecta com a API da BingX para executar ordens e sincronizar dados
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


class BingXConnector:
    """Connector para BingX API"""

    def __init__(
        self, api_key: str = None, api_secret: str = None, testnet: bool = True
    ):
        """
        Initialize BingX connector

        Args:
            api_key: BingX API key
            api_secret: BingX API secret
            testnet: Use testnet (default True for safety)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        if testnet:
            self.base_url = "https://open-api-test.bingx.com"
        else:
            self.base_url = "https://open-api.bingx.com"

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
        """Generate signature for BingX API"""
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
        """Make HTTP request to BingX API"""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}

        headers = {
            "Content-Type": "application/json"
        }

        if signed and self.api_key:
            timestamp = int(time.time() * 1000)
            params["timestamp"] = timestamp
            headers["X-BX-APIKEY"] = self.api_key
            
            # Generate signature
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            params["signature"] = signature

        try:
            if method == "GET":
                async with session.get(url, params=params, headers=headers) as response:
                    return await response.json()
            elif method == "POST":
                async with session.post(url, json=params, headers=headers) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"BingX API request failed: {e}")
            raise

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to BingX"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "message": "Demo mode - no real connection",
                    "testnet": True,
                    "demo": True,
                }

            # Test connection with account info
            result = await self._make_request("GET", "/openApi/spot/v1/account", signed=True)
            
            if result.get("code") == 0:
                return {
                    "success": True,
                    "message": "Connected to BingX",
                    "testnet": self.testnet,
                    "demo": False,
                    "balances_count": len(result.get("data", {}).get("balances", []))
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Unknown error"),
                    "testnet": self.testnet
                }

        except Exception as e:
            logger.error(f"BingX connection test failed: {e}")
            return {"success": False, "error": str(e), "testnet": self.testnet}

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

            result = await self._make_request("GET", "/openApi/spot/v1/account", signed=True)
            
            if result.get("code") == 0:
                account_data = result.get("data", {})
                balances = account_data.get("balances", [])
                
                # Filter only balances with value > 0
                active_balances = [
                    b for b in balances
                    if float(b.get("free", "0")) > 0 or float(b.get("locked", "0")) > 0
                ]

                return {
                    "demo": False,
                    "account_type": "SPOT",
                    "can_trade": account_data.get("canTrade", True),
                    "can_withdraw": account_data.get("canWithdraw", True),
                    "can_deposit": account_data.get("canDeposit", True),
                    "balances": active_balances,
                }
            else:
                raise Exception(f"BingX API error: {result.get('msg')}")

        except Exception as e:
            logger.error(f"Error getting BingX account info: {e}")
            raise

    async def get_account_orders(
        self, 
        symbol: str = None, 
        limit: int = 500,
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
                            "orderId": "demo_bingx_12345",
                            "symbol": "BTC-USDT",
                            "status": "FILLED",
                            "side": "BUY",
                            "type": "MARKET",
                            "origQty": "0.001",
                            "executedQty": "0.001",
                            "price": "45000.00",
                            "avgPrice": "45000.00",
                            "time": 1640995200000,
                            "updateTime": 1640995200000
                        }
                    ],
                    "total": 1
                }

            params = {
                "limit": min(limit, 500)
            }
            
            if symbol:
                params["symbol"] = symbol.replace("USDT", "-USDT")
            if order_id:
                params["orderId"] = order_id
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time

            result = await self._make_request("GET", "/openApi/spot/v1/order/history", params, signed=True)
            
            if result.get("code") == 0:
                orders = result.get("data", {}).get("orders", [])
                return {
                    "success": True,
                    "demo": False,
                    "orders": orders,
                    "total": len(orders)
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error getting BingX account orders: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_account_trades(
        self, 
        symbol: str = None, 
        limit: int = 500,
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
                            "symbol": "BTC-USDT",
                            "id": "demo_trade_123",
                            "orderId": "demo_bingx_12345",
                            "side": "BUY",
                            "price": "45000.00",
                            "qty": "0.001",
                            "quoteQty": "45.00",
                            "commission": "0.045",
                            "commissionAsset": "USDT",
                            "time": 1640995200000
                        }
                    ],
                    "total": 1
                }

            params = {
                "limit": min(limit, 500)
            }
            
            if symbol:
                params["symbol"] = symbol.replace("USDT", "-USDT")
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time

            result = await self._make_request("GET", "/openApi/spot/v1/myTrades", params, signed=True)
            
            if result.get("code") == 0:
                trades = result.get("data", [])
                return {
                    "success": True,
                    "demo": False,
                    "trades": trades,
                    "total": len(trades)
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error getting BingX account trades: {e}")
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
                        {"asset": "USDT", "free": "1000.00", "locked": "0.00", "total": "1000.00"},
                        {"asset": "BTC", "free": "0.02", "locked": "0.00", "total": "0.02"},
                        {"asset": "ETH", "free": "0.5", "locked": "0.00", "total": "0.5"},
                    ]
                }

            result = await self._make_request("GET", "/openApi/spot/v1/account", signed=True)
            
            if result.get("code") == 0:
                account_data = result.get("data", {})
                raw_balances = account_data.get("balances", [])
                
                # Filter and format balances
                balances = []
                for balance in raw_balances:
                    free = float(balance.get("free", "0"))
                    locked = float(balance.get("locked", "0"))
                    total = free + locked
                    
                    if total > 0:
                        balances.append({
                            "asset": balance.get("asset"),
                            "free": balance.get("free"),
                            "locked": balance.get("locked"),
                            "total": str(total)
                        })

                return {
                    "success": True,
                    "demo": False,
                    "balances": balances
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error getting BingX account balances: {e}")
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
                            "symbol": "BTC-USDT",
                            "side": "LONG",
                            "size": "0.001",
                            "entryPrice": "45000.0",
                            "markPrice": "45100.0",
                            "unrealizedProfit": "0.1",
                            "leverage": "10",
                            "notional": "45.1",
                            "updateTime": 1640995200000
                        }
                    ]
                }

            result = await self._make_request("GET", "/openApi/swap/v2/user/positions", signed=True)
            
            if result.get("code") == 0:
                positions = result.get("data", [])
                # Filter only positions with size > 0
                active_positions = [p for p in positions if float(p.get("positionAmt", "0")) != 0]
                
                return {
                    "success": True,
                    "demo": False,
                    "positions": active_positions
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error getting BingX futures positions: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def create_market_order(
        self,
        symbol: str,
        side: str,  # 'BUY' or 'SELL'
        quantity: Decimal,
        test_order: bool = None,
    ) -> Dict[str, Any]:
        """Create market order on BingX"""
        if test_order is None:
            test_order = self.is_demo_mode() or self.testnet

        try:
            symbol = symbol.replace("USDT", "-USDT")  # BingX format
            side = side.upper()

            if self.is_demo_mode():
                demo_order = {
                    "success": True,
                    "demo": True,
                    "order_id": f"demo_bingx_{symbol}_{side}_{int(time.time())}",
                    "symbol": symbol,
                    "side": side,
                    "type": "MARKET",
                    "quantity": str(quantity),
                    "status": "FILLED",
                    "filled_quantity": str(quantity),
                    "average_price": "45000.00" if "BTC" in symbol else "2500.00",
                    "timestamp": int(time.time() * 1000),
                }
                return demo_order

            # Real order for BingX
            params = {
                "symbol": symbol,
                "side": side,
                "type": "MARKET",
                "quantity": str(quantity),
                "timeInForce": "IOC"
            }

            result = await self._make_request("POST", "/openApi/spot/v1/order", params, signed=True)
            
            if result.get("code") == 0:
                order_data = result.get("data", {})
                return {
                    "success": True,
                    "demo": False,
                    "order_id": str(order_data.get("orderId")),
                    "symbol": symbol,
                    "side": side,
                    "type": "MARKET",
                    "quantity": str(quantity),
                    "status": order_data.get("status", "NEW"),
                    "timestamp": int(time.time() * 1000),
                    "raw_response": result
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Unknown error"),
                    "code": result.get("code")
                }

        except Exception as e:
            logger.error(f"Error creating BingX market order: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()


# Factory function
def create_bingx_connector(
    api_key: str = None, api_secret: str = None, testnet: bool = True
) -> BingXConnector:
    """Create BingX connector instance"""
    return BingXConnector(api_key=api_key, api_secret=api_secret, testnet=testnet)