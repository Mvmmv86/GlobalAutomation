"""
Bitget Exchange Connector
Conecta com a API da Bitget para executar ordens e sincronizar dados
"""

import asyncio
import hashlib
import hmac
import time
import base64
import aiohttp
from decimal import Decimal
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class BitgetConnector:
    """Connector para Bitget API"""

    def __init__(
        self, api_key: str = None, api_secret: str = None, passphrase: str = None, testnet: bool = True
    ):
        """
        Initialize Bitget connector

        Args:
            api_key: Bitget API key
            api_secret: Bitget API secret
            passphrase: Bitget API passphrase
            testnet: Use testnet (default True for safety)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.testnet = testnet

        if testnet:
            self.base_url = "https://api.bitget.com"  # Bitget doesn't have separate testnet URL
        else:
            self.base_url = "https://api.bitget.com"

        self.session = None

    def is_demo_mode(self) -> bool:
        """Check if running in demo mode"""
        return not (self.api_key and self.api_secret and self.passphrase)

    async def _get_session(self):
        """Get or create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session

    def _generate_signature(self, method: str, endpoint: str, params: str, timestamp: str) -> str:
        """Generate signature for Bitget API"""
        if not self.api_secret:
            return ""
        
        message = timestamp + method + endpoint + params
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode()

    async def _make_request(
        self, method: str, endpoint: str, params: dict = None, signed: bool = False
    ) -> dict:
        """Make HTTP request to Bitget API"""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}

        headers = {
            "Content-Type": "application/json"
        }

        timestamp = str(int(time.time() * 1000))
        params_str = ""

        if signed and self.api_key:
            headers["ACCESS-KEY"] = self.api_key
            headers["ACCESS-TIMESTAMP"] = timestamp
            headers["ACCESS-PASSPHRASE"] = self.passphrase

            if method == "GET" and params:
                params_str = "&".join([f"{k}={v}" for k, v in params.items()])
                if params_str:
                    params_str = "?" + params_str
            elif method == "POST" and params:
                import json
                params_str = json.dumps(params)

            headers["ACCESS-SIGN"] = self._generate_signature(method, endpoint, params_str, timestamp)

        try:
            if method == "GET":
                async with session.get(url, params=params, headers=headers) as response:
                    return await response.json()
            elif method == "POST":
                async with session.post(url, json=params, headers=headers) as response:
                    return await response.json()
        except Exception as e:
            logger.error(f"Bitget API request failed: {e}")
            raise

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Bitget"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "message": "Demo mode - no real connection",
                    "testnet": True,
                    "demo": True,
                }

            # Test connection with account info
            result = await self._make_request("GET", "/api/v2/spot/account/info", signed=True)
            
            if result.get("code") == "00000":
                return {
                    "success": True,
                    "message": "Connected to Bitget",
                    "testnet": self.testnet,
                    "demo": False,
                    "account_type": "SPOT"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Unknown error"),
                    "testnet": self.testnet
                }

        except Exception as e:
            logger.error(f"Bitget connection test failed: {e}")
            return {"success": False, "error": str(e), "testnet": self.testnet}

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        try:
            if self.is_demo_mode():
                return {
                    "demo": True,
                    "account_type": "DEMO",
                    "balances": [
                        {"coin": "USDT", "available": "1000.00", "frozen": "0.00"},
                        {"coin": "BTC", "available": "0.02", "frozen": "0.00"},
                        {"coin": "ETH", "available": "0.5", "frozen": "0.00"},
                    ],
                }

            result = await self._make_request("GET", "/api/v2/spot/account/assets", signed=True)
            
            if result.get("code") == "00000":
                balances = result.get("data", [])
                
                # Filter only balances with value > 0
                active_balances = [
                    b for b in balances
                    if float(b.get("available", "0")) > 0 or float(b.get("frozen", "0")) > 0
                ]

                return {
                    "demo": False,
                    "account_type": "SPOT",
                    "balances": active_balances,
                }
            else:
                raise Exception(f"Bitget API error: {result.get('msg')}")

        except Exception as e:
            logger.error(f"Error getting Bitget account info: {e}")
            raise

    async def get_account_orders(
        self, 
        symbol: str = None, 
        limit: int = 100,
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
                            "orderId": "demo_bitget_12345",
                            "symbol": "BTCUSDT",
                            "status": "filled",
                            "side": "buy",
                            "orderType": "market",
                            "size": "0.001",
                            "fillSize": "0.001",
                            "price": "45000.00",
                            "fillPrice": "45000.00",
                            "cTime": "1640995200000",
                            "uTime": "1640995200000"
                        }
                    ],
                    "total": 1
                }

            params = {
                "limit": str(min(limit, 100))
            }
            
            if symbol:
                params["symbol"] = symbol.upper() + "_SPBL"  # Bitget spot format
            if order_id:
                params["orderId"] = order_id
            if start_time:
                params["startTime"] = str(start_time)
            if end_time:
                params["endTime"] = str(end_time)

            result = await self._make_request("GET", "/api/v2/spot/trade/history-orders", params, signed=True)
            
            if result.get("code") == "00000":
                orders = result.get("data", [])
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
            logger.error(f"Error getting Bitget account orders: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_account_trades(
        self, 
        symbol: str = None, 
        limit: int = 100,
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
                            "symbol": "BTCUSDT_SPBL",
                            "tradeId": "demo_trade_123",
                            "orderId": "demo_bitget_12345",
                            "side": "buy",
                            "price": "45000.00",
                            "size": "0.001",
                            "feeDetail": {
                                "deduction": "no",
                                "feeCoin": "USDT",
                                "totalFee": "0.045"
                            },
                            "cTime": "1640995200000"
                        }
                    ],
                    "total": 1
                }

            params = {
                "limit": str(min(limit, 100))
            }
            
            if symbol:
                params["symbol"] = symbol.upper() + "_SPBL"
            if start_time:
                params["startTime"] = str(start_time)
            if end_time:
                params["endTime"] = str(end_time)

            result = await self._make_request("GET", "/api/v2/spot/trade/fills", params, signed=True)
            
            if result.get("code") == "00000":
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
            logger.error(f"Error getting Bitget account trades: {e}")
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
                        {"coin": "USDT", "available": "1000.00", "frozen": "0.00", "total": "1000.00"},
                        {"coin": "BTC", "available": "0.02", "frozen": "0.00", "total": "0.02"},
                        {"coin": "ETH", "available": "0.5", "frozen": "0.00", "total": "0.5"},
                    ]
                }

            result = await self._make_request("GET", "/api/v2/spot/account/assets", signed=True)
            
            if result.get("code") == "00000":
                raw_balances = result.get("data", [])
                
                # Filter and format balances
                balances = []
                for balance in raw_balances:
                    available = float(balance.get("available", "0"))
                    frozen = float(balance.get("frozen", "0"))
                    total = available + frozen
                    
                    if total > 0:
                        balances.append({
                            "coin": balance.get("coin"),
                            "available": balance.get("available"),
                            "frozen": balance.get("frozen"),
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
            logger.error(f"Error getting Bitget account balances: {e}")
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
                            "side": "long",
                            "size": "0.001",
                            "averageOpenPrice": "45000.0",
                            "markPrice": "45100.0",
                            "unrealizedPL": "0.1",
                            "leverage": "10",
                            "notionalValue": "45.1",
                            "cTime": "1640995200000",
                            "uTime": "1640995200000"
                        }
                    ]
                }

            result = await self._make_request("GET", "/api/v2/mix/account/positions", {"productType": "USDT-FUTURES"}, signed=True)
            
            if result.get("code") == "00000":
                positions = result.get("data", [])
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
                    "error": result.get("msg", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error getting Bitget futures positions: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def create_market_order(
        self,
        symbol: str,
        side: str,  # 'buy' or 'sell'
        quantity: Decimal,
        test_order: bool = None,
    ) -> Dict[str, Any]:
        """Create market order on Bitget"""
        if test_order is None:
            test_order = self.is_demo_mode() or self.testnet

        try:
            symbol = symbol.upper() + "_SPBL"  # Bitget spot format
            side = side.lower()

            if self.is_demo_mode():
                demo_order = {
                    "success": True,
                    "demo": True,
                    "order_id": f"demo_bitget_{symbol}_{side}_{int(time.time())}",
                    "symbol": symbol,
                    "side": side,
                    "type": "market",
                    "quantity": str(quantity),
                    "status": "filled",
                    "filled_quantity": str(quantity),
                    "average_price": "45000.00" if "BTC" in symbol else "2500.00",
                    "timestamp": int(time.time() * 1000),
                }
                return demo_order

            # Real order for Bitget
            params = {
                "symbol": symbol,
                "side": side,
                "orderType": "market",
                "size": str(quantity),
                "force": "ioc"
            }

            result = await self._make_request("POST", "/api/v2/spot/trade/place-order", params, signed=True)
            
            if result.get("code") == "00000":
                order_data = result.get("data", {})
                return {
                    "success": True,
                    "demo": False,
                    "order_id": order_data.get("orderId"),
                    "symbol": symbol,
                    "side": side,
                    "type": "market",
                    "quantity": str(quantity),
                    "status": "new",
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
            logger.error(f"Error creating Bitget market order: {e}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()


# Factory function
def create_bitget_connector(
    api_key: str = None, api_secret: str = None, passphrase: str = None, testnet: bool = True
) -> BitgetConnector:
    """Create Bitget connector instance"""
    return BitgetConnector(api_key=api_key, api_secret=api_secret, passphrase=passphrase, testnet=testnet)