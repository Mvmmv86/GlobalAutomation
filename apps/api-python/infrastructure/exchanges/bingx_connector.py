"""
BingX Exchange Connector
Conecta com a API da BingX para executar ordens e sincronizar dados
"""

import asyncio
import hashlib
import hmac
import time
import json
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
                    response_text = await response.text()
                    logger.info(f"BingX API Response (status={response.status}): {response_text[:500]}")
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        logger.error(f"BingX returned non-JSON response: {response_text[:200]}")
                        return {"success": False, "error": f"Invalid response: {response_text[:200]}"}
            elif method == "POST":
                async with session.post(url, json=params, headers=headers) as response:
                    response_text = await response.text()
                    logger.info(f"BingX API Response (status={response.status}): {response_text[:500]}")
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        logger.error(f"BingX returned non-JSON response: {response_text[:200]}")
                        return {"success": False, "error": f"Invalid response: {response_text[:200]}"}
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

            # Test connection with account balance
            result = await self._make_request("GET", "/openApi/spot/v1/account/balance", signed=True)
            
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
        """
        Get wallet account information (FUND + SPOT combined)

        NOTE: BingX API endpoint /openApi/spot/v1/account/balance returns the total
        wallet balance which includes both FUND and SPOT accounts combined.
        As of 2025, BingX has not provided a separate API endpoint to query SPOT
        trading account separately from FUND account.

        Returns:
            dict: Account information with balances
                - success: bool
                - demo: bool
                - account_type: "WALLET" (FUND+SPOT combined)
                - balances: list of assets with free and locked amounts
        """
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "account_type": "WALLET",
                    "balances": [
                        {"asset": "USDT", "free": "1000.00", "locked": "0.00"},
                        {"asset": "BTC", "free": "0.02", "locked": "0.00"},
                        {"asset": "ETH", "free": "0.5", "locked": "0.00"},
                    ],
                }

            result = await self._make_request("GET", "/openApi/spot/v1/account/balance", signed=True)

            if result.get("code") == 0:
                account_data = result.get("data", {})
                balances = account_data.get("balances", [])

                # Filter only balances with value > 0
                active_balances = [
                    b for b in balances
                    if float(b.get("free", "0")) > 0 or float(b.get("locked", "0")) > 0
                ]

                return {
                    "success": True,
                    "demo": False,
                    "account_type": "WALLET",  # FUND + SPOT combined (BingX API limitation)
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

            result = await self._make_request("GET", "/openApi/spot/v1/account/balance", signed=True)

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

    # ============================================================================
    # FUTURES TRADING METHODS
    # ============================================================================

    async def get_futures_account(self) -> Dict[str, Any]:
        """Get futures account information"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "totalWalletBalance": "10000.00",
                    "totalUnrealizedProfit": "150.50",
                    "totalMarginBalance": "10150.50",
                    "availableBalance": "8500.00",
                    "assets": [
                        {
                            "asset": "USDT",
                            "walletBalance": "10000.00",
                            "unrealizedProfit": "150.50",
                            "marginBalance": "10150.50",
                            "availableBalance": "8500.00"
                        }
                    ]
                }

            result = await self._make_request("GET", "/openApi/swap/v2/user/balance", signed=True)

            if result.get("code") == 0:
                # BingX API returns: {"data": {"balance": {"asset": "USDT", "balance": "16.69", ...}}}
                data = result.get("data", {})
                balance_info = data.get("balance", {})
                logger.info(f"✅ BingX futures balance info: {balance_info}")

                # FIX: Convert BingX format to Binance-compatible format for dashboard
                # BingX returns single balance object, convert to assets array
                assets = []
                if balance_info:
                    assets.append({
                        "asset": balance_info.get("asset", "USDT"),
                        "walletBalance": balance_info.get("balance", "0"),
                        "unrealizedProfit": balance_info.get("unrealizedProfit", "0"),
                        "availableBalance": balance_info.get("availableMargin", "0"),
                        "marginBalance": balance_info.get("equity", "0")
                    })

                return {
                    "success": True,
                    "demo": False,
                    "account": {  # ← FIX: Wrap in 'account' for compatibility
                        "assets": assets
                    },
                    "balance": balance_info  # Keep original for backward compatibility
                }
            else:
                error_msg = f"BingX API error: {result.get('msg')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }

        except Exception as e:
            logger.error(f"Error getting BingX futures account: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def create_futures_order(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        order_type: str,  # "MARKET", "LIMIT", "STOP_MARKET", "TAKE_PROFIT_MARKET"
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        reduce_only: bool = False,
        time_in_force: str = "GTC"
    ) -> Dict[str, Any]:
        """
        Create futures order on BingX

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            side: "BUY" or "SELL"
            order_type: Order type
            quantity: Order quantity
            price: Limit price (required for LIMIT orders)
            stop_price: Stop price (required for STOP orders)
            reduce_only: Reduce only flag
            time_in_force: Time in force (GTC, IOC, FOK)
        """
        try:
            # Normalize symbol to BingX format
            symbol_bingx = symbol.replace("USDT", "-USDT") if "-" not in symbol else symbol
            side = side.upper()

            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "order_id": f"demo_futures_{symbol}_{side}_{int(time.time())}",
                    "symbol": symbol_bingx,
                    "side": side,
                    "type": order_type,
                    "quantity": str(quantity),
                    "status": "FILLED",
                    "filled_quantity": str(quantity),
                    "average_price": "45000.00" if "BTC" in symbol else "2500.00",
                    "timestamp": int(time.time() * 1000),
                }

            # Determine position side
            position_side = "LONG" if side == "BUY" else "SHORT"

            params = {
                "symbol": symbol_bingx,
                "side": side,
                "positionSide": position_side,
                "type": order_type,
                "quantity": quantity,
            }

            if price and order_type in ["LIMIT", "STOP"]:
                params["price"] = price
                params["timeInForce"] = time_in_force

            if stop_price and "STOP" in order_type:
                params["stopPrice"] = stop_price

            if reduce_only:
                params["reduceOnly"] = "true"

            result = await self._make_request("POST", "/openApi/swap/v2/trade/order", params, signed=True)

            if result.get("code") == 0:
                order_data = result.get("data", {})
                return {
                    "success": True,
                    "demo": False,
                    "order_id": str(order_data.get("orderId")),
                    "symbol": symbol,
                    "side": side,
                    "type": order_type,
                    "quantity": str(quantity),
                    "status": order_data.get("status", "NEW"),
                    "filled_quantity": str(order_data.get("executedQty", "0")),
                    "average_price": str(order_data.get("avgPrice", "0")),
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
            logger.error(f"Error creating BingX futures order: {e}")
            return {"success": False, "error": str(e)}

    async def set_leverage(
        self,
        symbol: str,
        leverage: int,
        side: str = "LONG"  # "LONG" or "SHORT"
    ) -> Dict[str, Any]:
        """
        Set leverage for futures trading

        Args:
            symbol: Trading pair
            leverage: Leverage value (1-125)
            side: Position side (LONG or SHORT)
        """
        try:
            symbol_bingx = symbol.replace("USDT", "-USDT") if "-" not in symbol else symbol

            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "symbol": symbol_bingx,
                    "leverage": leverage,
                    "side": side
                }

            params = {
                "symbol": symbol_bingx,
                "side": side.upper(),
                "leverage": leverage
            }

            result = await self._make_request("POST", "/openApi/swap/v2/trade/leverage", params, signed=True)

            if result.get("code") == 0:
                return {
                    "success": True,
                    "demo": False,
                    "symbol": symbol,
                    "leverage": leverage,
                    "side": side
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Unknown error"),
                    "code": result.get("code")
                }

        except Exception as e:
            logger.error(f"Error setting BingX leverage: {e}")
            return {"success": False, "error": str(e)}

    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        reduce_only: bool = True
    ) -> Dict[str, Any]:
        """Create stop loss order for futures"""
        return await self.create_futures_order(
            symbol=symbol,
            side=side,
            order_type="STOP_MARKET",
            quantity=quantity,
            stop_price=stop_price,
            reduce_only=reduce_only
        )

    async def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        reduce_only: bool = True
    ) -> Dict[str, Any]:
        """Create take profit order for futures"""
        return await self.create_futures_order(
            symbol=symbol,
            side=side,
            order_type="TAKE_PROFIT_MARKET",
            quantity=quantity,
            stop_price=stop_price,
            reduce_only=reduce_only
        )

    # ============================================================================
    # SPOT ADVANCED TRADING METHODS
    # ============================================================================

    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = "GTC"
    ) -> Dict[str, Any]:
        """Create limit order for SPOT trading"""
        try:
            symbol_bingx = symbol.replace("USDT", "-USDT") if "-" not in symbol else symbol
            side = side.upper()

            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "order_id": f"demo_limit_{symbol}_{side}_{int(time.time())}",
                    "symbol": symbol_bingx,
                    "side": side,
                    "type": "LIMIT",
                    "quantity": str(quantity),
                    "price": str(price),
                    "status": "NEW",
                    "timestamp": int(time.time() * 1000),
                }

            params = {
                "symbol": symbol_bingx,
                "side": side,
                "type": "LIMIT",
                "quantity": str(quantity),
                "price": str(price),
                "timeInForce": time_in_force
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
                    "type": "LIMIT",
                    "quantity": str(quantity),
                    "price": str(price),
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
            logger.error(f"Error creating BingX limit order: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_order(
        self,
        symbol: str,
        order_id: str
    ) -> Dict[str, Any]:
        """Cancel an order"""
        try:
            symbol_bingx = symbol.replace("USDT", "-USDT") if "-" not in symbol else symbol

            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "order_id": order_id,
                    "symbol": symbol_bingx,
                    "status": "CANCELED"
                }

            params = {
                "symbol": symbol_bingx,
                "orderId": order_id
            }

            result = await self._make_request("POST", "/openApi/spot/v1/order/cancel", params, signed=True)

            if result.get("code") == 0:
                return {
                    "success": True,
                    "demo": False,
                    "order_id": order_id,
                    "symbol": symbol,
                    "status": "CANCELED"
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Unknown error"),
                    "code": result.get("code")
                }

        except Exception as e:
            logger.error(f"Error canceling BingX order: {e}")
            return {"success": False, "error": str(e)}

    async def get_order_status(
        self,
        symbol: str,
        order_id: str
    ) -> Dict[str, Any]:
        """Get status of specific order"""
        try:
            symbol_bingx = symbol.replace("USDT", "-USDT") if "-" not in symbol else symbol

            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "order_id": order_id,
                    "symbol": symbol_bingx,
                    "status": "FILLED",
                    "side": "BUY",
                    "type": "MARKET",
                    "quantity": "0.001",
                    "filled_quantity": "0.001",
                    "average_price": "45000.00"
                }

            params = {
                "symbol": symbol_bingx,
                "orderId": order_id
            }

            result = await self._make_request("GET", "/openApi/spot/v1/order/query", params, signed=True)

            if result.get("code") == 0:
                order_data = result.get("data", {})
                return {
                    "success": True,
                    "demo": False,
                    "order_id": str(order_data.get("orderId")),
                    "symbol": symbol,
                    "status": order_data.get("status"),
                    "side": order_data.get("side"),
                    "type": order_data.get("type"),
                    "quantity": str(order_data.get("origQty", "0")),
                    "filled_quantity": str(order_data.get("executedQty", "0")),
                    "average_price": str(order_data.get("avgPrice", "0")),
                    "raw_response": result
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Unknown error"),
                    "code": result.get("code")
                }

        except Exception as e:
            logger.error(f"Error getting BingX order status: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # REPORTS AND HISTORY METHODS
    # ============================================================================

    async def get_futures_income_history(
        self,
        income_type: Optional[str] = None,
        symbol: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get futures income history (P&L, fees, funding, etc)

        Args:
            income_type: Type of income (REALIZED_PNL, COMMISSION, FUNDING_FEE, etc)
            symbol: Trading pair filter
            start_time: Start timestamp
            end_time: End timestamp
            limit: Number of records
        """
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "income_history": [
                        {
                            "symbol": "BTC-USDT",
                            "incomeType": "REALIZED_PNL",
                            "income": "15.50",
                            "asset": "USDT",
                            "time": int(time.time() * 1000)
                        }
                    ]
                }

            params = {
                "limit": min(limit, 1000)
            }

            if income_type:
                params["incomeType"] = income_type
            if symbol:
                params["symbol"] = symbol.replace("USDT", "-USDT") if "-" not in symbol else symbol
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time

            result = await self._make_request("GET", "/openApi/swap/v2/user/income", params, signed=True)

            if result.get("code") == 0:
                income_data = result.get("data", [])
                return {
                    "success": True,
                    "demo": False,
                    "income_history": income_data
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error getting BingX futures income history: {e}")
            return {"success": False, "error": str(e)}

    async def get_futures_orders(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get futures order history"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "orders": [
                        {
                            "orderId": "demo_futures_123",
                            "symbol": "BTC-USDT",
                            "status": "FILLED",
                            "side": "BUY",
                            "positionSide": "LONG",
                            "type": "MARKET",
                            "origQty": "0.001",
                            "executedQty": "0.001",
                            "avgPrice": "45000.00",
                            "time": int(time.time() * 1000)
                        }
                    ]
                }

            params = {
                "limit": min(limit, 500)
            }

            if symbol:
                params["symbol"] = symbol.replace("USDT", "-USDT") if "-" not in symbol else symbol
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time

            result = await self._make_request("GET", "/openApi/swap/v2/trade/allOrders", params, signed=True)

            if result.get("code") == 0:
                orders = result.get("data", {}).get("orders", [])
                return {
                    "success": True,
                    "demo": False,
                    "orders": orders
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Unknown error")
                }

        except Exception as e:
            logger.error(f"Error getting BingX futures orders: {e}")
            return {"success": False, "error": str(e)}

    async def get_closed_positions_from_orders(
        self,
        symbol: Optional[str] = None,
        limit: int = 500,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Reconstruct closed positions from order history
        Similar to Binance connector implementation
        """
        try:
            # Get all futures orders
            orders_result = await self.get_futures_orders(
                symbol=symbol,
                limit=limit,
                start_time=start_time,
                end_time=end_time
            )

            if not orders_result.get("success"):
                return orders_result

            orders = orders_result.get("orders", [])

            # Filter only filled orders
            filled_orders = [o for o in orders if o.get("status") == "FILLED"]

            # Group by symbol and analyze positions
            positions_by_symbol = {}

            for order in sorted(filled_orders, key=lambda x: x.get("time", 0)):
                sym = order.get("symbol")
                if sym not in positions_by_symbol:
                    positions_by_symbol[sym] = {
                        "symbol": sym,
                        "orders": [],
                        "net_quantity": 0.0,
                        "total_entry_value": 0.0,
                        "total_exit_value": 0.0,
                        "closed_positions": []
                    }

                qty = float(order.get("executedQty", 0))
                price = float(order.get("avgPrice", 0))
                side = order.get("side")
                position_side = order.get("positionSide", "")

                # Track if opening or closing position
                is_opening = (position_side == "LONG" and side == "BUY") or (position_side == "SHORT" and side == "SELL")

                if is_opening:
                    positions_by_symbol[sym]["net_quantity"] += qty
                    positions_by_symbol[sym]["total_entry_value"] += qty * price
                else:
                    positions_by_symbol[sym]["net_quantity"] -= qty
                    positions_by_symbol[sym]["total_exit_value"] += qty * price

                positions_by_symbol[sym]["orders"].append(order)

                # Check if position is now closed
                if abs(positions_by_symbol[sym]["net_quantity"]) < 0.0001:
                    entry_value = positions_by_symbol[sym]["total_entry_value"]
                    exit_value = positions_by_symbol[sym]["total_exit_value"]
                    pnl = exit_value - entry_value if position_side == "LONG" else entry_value - exit_value

                    positions_by_symbol[sym]["closed_positions"].append({
                        "symbol": sym,
                        "side": position_side,
                        "realized_pnl": pnl,
                        "close_time": order.get("time")
                    })

                    # Reset for next position
                    positions_by_symbol[sym]["net_quantity"] = 0.0
                    positions_by_symbol[sym]["total_entry_value"] = 0.0
                    positions_by_symbol[sym]["total_exit_value"] = 0.0

            # Collect all closed positions
            closed_positions = []
            for data in positions_by_symbol.values():
                closed_positions.extend(data["closed_positions"])

            return {
                "success": True,
                "demo": self.is_demo_mode(),
                "closed_positions": closed_positions
            }

        except Exception as e:
            logger.error(f"Error reconstructing closed positions: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    async def normalize_quantity(
        self,
        symbol: str,
        quantity: float,
        is_futures: bool = False
    ) -> float:
        """
        Normalize quantity according to exchange rules

        Args:
            symbol: Trading pair
            quantity: Desired quantity
            is_futures: Whether this is for futures trading

        Returns:
            Normalized quantity that meets exchange requirements
        """
        try:
            import math

            # Get exchange info for the symbol
            if is_futures:
                endpoint = "/openApi/swap/v2/quote/contracts"
            else:
                endpoint = "/openApi/spot/v1/common/symbols"

            result = await self._make_request("GET", endpoint)

            if result.get("code") != 0:
                logger.warning(f"Could not fetch exchange info, using quantity as-is: {quantity}")
                return quantity

            # Find symbol info
            symbols = result.get("data", {}).get("symbols", []) if not is_futures else result.get("data", [])
            symbol_info = None
            symbol_bingx = symbol.replace("USDT", "-USDT") if "-" not in symbol else symbol

            for s in symbols:
                if s.get("symbol") == symbol_bingx:
                    symbol_info = s
                    break

            if not symbol_info:
                logger.warning(f"Symbol {symbol} not found in exchange info, using quantity as-is")
                return quantity

            # Get LOT_SIZE filter
            filters = symbol_info.get("filters", [])
            lot_size_filter = None

            for f in filters:
                if f.get("filterType") == "LOT_SIZE":
                    lot_size_filter = f
                    break

            if not lot_size_filter:
                # Use default precision
                step_size = 0.00001
                min_qty = 0.00001
            else:
                step_size = float(lot_size_filter.get("stepSize", 0.00001))
                min_qty = float(lot_size_filter.get("minQty", 0.00001))

            # Normalize: floor to nearest step_size
            normalized = math.floor(quantity / step_size) * step_size

            # Validate minimum
            if normalized < min_qty:
                raise ValueError(f"Quantity {normalized} below minimum {min_qty} for {symbol}")

            return normalized

        except Exception as e:
            logger.error(f"Error normalizing quantity: {e}")
            # Return original quantity if normalization fails
            return quantity

    async def _get_price_from_binance(self, asset: str) -> Optional[float]:
        """
        Get asset price from BINANCE (1st priority)

        Args:
            asset: Asset symbol (e.g., 'BTC', 'ETH')

        Returns:
            float: Price in USDT or None if not found
        """
        session = await self._get_session()
        url = "https://api.binance.com/api/v3/ticker/price"

        try:
            async with session.get(url, params={"symbol": f"{asset}USDT"}) as response:
                result = await response.json()
                if "price" in result:
                    return float(result["price"])
        except Exception as e:
            logger.debug(f"Could not get {asset} price from Binance: {e}")

        return None

    async def _get_price_from_bingx(self, asset: str) -> Optional[float]:
        """
        Get asset price from BINGX (2nd priority)

        Args:
            asset: Asset symbol (e.g., 'BTC', 'ETH')

        Returns:
            float: Price in USDT or None if not found
        """
        session = await self._get_session()
        url = f"{self.base_url}/openApi/spot/v1/ticker/24hr"
        timestamp = int(time.time() * 1000)
        params = {"symbol": f"{asset}-USDT", "timestamp": timestamp}

        try:
            async with session.get(url, params=params) as response:
                result = await response.json()
                if result.get("code") == 0:
                    data = result.get("data", [])
                    if data and len(data) > 0:
                        return float(data[0].get("lastPrice", 0))
        except Exception as e:
            logger.debug(f"Could not get {asset} price from BingX: {e}")

        return None

    async def _get_asset_price_in_usdt(self, asset: str) -> tuple[float, str]:
        """
        Get asset price in USDT

        Priority order:
        1. USDT/USDC always return 1.0
        2. Try Binance first (more liquid)
        3. Try BingX second
        4. Return 0 if not found

        Args:
            asset: Asset symbol (e.g., 'AERO', 'BTC', 'ETH')

        Returns:
            tuple: (price, source) where source is 'STABLE', 'BINANCE', 'BINGX', or 'NOT_FOUND'
        """
        # Stablecoins always worth $1
        if asset in ["USDT", "USDC"]:
            return 1.0, "STABLE"

        # Try Binance first (1st priority)
        price = await self._get_price_from_binance(asset)
        if price and price > 0:
            return price, "BINANCE"

        # Try BingX second (2nd priority)
        price = await self._get_price_from_bingx(asset)
        if price and price > 0:
            return price, "BINGX"

        # Not found
        return 0, "NOT_FOUND"

    async def get_balances_separated(self) -> Dict[str, Any]:
        """
        Get SPOT and FUTURES balances separated

        LOGIC:
        1. Get FUND account balances from /openApi/fund/v1/account/balance
        2. Get SPOT account balances from /openApi/spot/v1/account/balance
        3. Combine FUND + SPOT balances (sum if asset exists in both)
        4. Convert each asset to USDT using prices from:
           - 1st priority: Binance API (more liquid)
           - 2nd priority: BingX API
        5. Get FUTURES balance from /openApi/swap/v2/user/balance
        6. Calculate: SPOT = WALLET_TOTAL - FUTURES

        Returns:
            dict: {
                "success": bool,
                "wallet_total_usdt": float,  # Total wallet (FUND + SPOT combined)
                "spot_usdt": float,          # SPOT = WALLET - FUTURES
                "futures_usdt": float,       # FUTURES balance
                "assets_count": int,         # Number of assets converted
                "price_sources": dict        # Count by source (BINANCE, BINGX, STABLE)
            }
        """
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "wallet_total_usdt": 1000.00,
                    "spot_usdt": 950.00,
                    "futures_usdt": 50.00,
                    "assets_count": 3,
                    "price_sources": {"BINANCE": 2, "STABLE": 1}
                }

            # 1. Get FUND account balances
            fund_result = await self._make_request(
                "GET",
                "/openApi/fund/v1/account/balance",
                signed=True
            )

            if fund_result.get("code") != 0:
                raise Exception(f"Error getting FUND account: {fund_result.get('msg')}")

            # 2. Get SPOT account balances
            spot_result = await self._make_request(
                "GET",
                "/openApi/spot/v1/account/balance",
                signed=True
            )

            if spot_result.get("code") != 0:
                raise Exception(f"Error getting SPOT account: {spot_result.get('msg')}")

            # 3. Combine FUND + SPOT balances
            # NOTE: FUND uses 'assets', SPOT uses 'balances'
            fund_balances = fund_result.get("data", {}).get("assets", [])
            spot_balances = spot_result.get("data", {}).get("balances", [])

            # Merge balances (sum amounts if asset exists in both)
            combined_balances = {}
            for balance in fund_balances:
                asset = balance.get("asset")
                amount = float(balance.get("free", 0))
                combined_balances[asset] = combined_balances.get(asset, 0) + amount

            for balance in spot_balances:
                asset = balance.get("asset")
                amount = float(balance.get("free", 0))
                combined_balances[asset] = combined_balances.get(asset, 0) + amount

            logger.info(f"Processing {len(combined_balances)} unique assets from BingX FUND + SPOT")
            logger.info(f"  FUND: {len(fund_balances)} assets, SPOT: {len(spot_balances)} assets")

            # 4. Convert each asset to USDT
            wallet_total_usdt = 0
            assets_converted = 0
            price_sources = {"BINANCE": 0, "BINGX": 0, "STABLE": 0, "NOT_FOUND": 0}

            for asset, amount in combined_balances.items():
                if amount <= 0:
                    continue

                # Get price with source tracking
                price, source = await self._get_asset_price_in_usdt(asset)
                value_usdt = amount * price

                # Only count assets with value (price found)
                if price > 0:
                    wallet_total_usdt += value_usdt
                    price_sources[source] += 1

                    # Only count as "converted" if value >= $1
                    if value_usdt >= 1.0:
                        assets_converted += 1
                        logger.debug(f"{asset}: {amount:.8f} @ ${price:.2f} ({source}) = ${value_usdt:.2f}")

                # Small delay to avoid rate limits
                await asyncio.sleep(0.05)

            logger.info(
                f"Wallet total: ${wallet_total_usdt:.2f} "
                f"({assets_converted} assets > $1, "
                f"Binance: {price_sources['BINANCE']}, "
                f"BingX: {price_sources['BINGX']}, "
                f"Stable: {price_sources['STABLE']})"
            )

            # 3. Get FUTURES balance
            futures_result = await self._make_request(
                "GET",
                "/openApi/swap/v2/user/balance",
                signed=True
            )

            futures_balance = 0
            if futures_result.get("code") == 0:
                futures_balance = float(
                    futures_result.get("data", {}).get("balance", {}).get("balance", 0)
                )
                logger.info(f"Futures balance: ${futures_balance:.2f}")
            else:
                logger.warning(f"Could not get futures balance: {futures_result.get('msg')}")

            # 4. Calculate SPOT = WALLET - FUTURES
            spot_balance = wallet_total_usdt - futures_balance

            logger.info(f"Final balances - SPOT: ${spot_balance:.2f}, FUTURES: ${futures_balance:.2f}")

            return {
                "success": True,
                "demo": False,
                "wallet_total_usdt": round(wallet_total_usdt, 2),
                "spot_usdt": round(spot_balance, 2),
                "futures_usdt": round(futures_balance, 2),
                "assets_count": assets_converted,
                "price_sources": {
                    k: v for k, v in price_sources.items() if k != "NOT_FOUND"
                }
            }

        except Exception as e:
            logger.error(f"Error getting separated balances: {e}")
            return {
                "success": False,
                "error": str(e),
                "wallet_total_usdt": 0,
                "spot_usdt": 0,
                "futures_usdt": 0,
                "assets_count": 0,
                "price_sources": {}
            }

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