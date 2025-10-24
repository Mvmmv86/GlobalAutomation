"""
Binance Exchange Connector
Conecta com a API da Binance para executar ordens reais
"""

import asyncio
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from decimal import Decimal
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class BinanceConnector:
    """Connector para Binance API"""

    def __init__(
        self, api_key: str, api_secret: str, testnet: bool = False
    ):
        """
        Initialize Binance connector

        Args:
            api_key: Binance API key (REQUIRED)
            api_secret: Binance API secret (REQUIRED)
            testnet: Use testnet (default False for production)
        """
        # SECURITY: API keys são obrigatórias - SEM fallback para ambiente
        if not api_key or not api_secret:
            raise ValueError("API key and secret are required. No demo mode available.")

        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        # Configurar client com credenciais reais
        self.client = Client(
            api_key=api_key, api_secret=api_secret, testnet=testnet
        )
        logger.info("✅ Binance connector initialized", testnet=testnet)

    async def normalize_quantity(self, symbol: str, quantity: float, is_futures: bool = False) -> float:
        """
        Normaliza quantidade baseado no stepSize do símbolo

        Args:
            symbol: Par de negociação (ex: BTCUSDT, AVAXUSDT)
            quantity: Quantidade original
            is_futures: Se é futures (usa futures_exchange_info)

        Returns:
            Quantidade normalizada segundo stepSize da Binance

        Exemplos:
            BTCUSDT: stepSize=0.001 (3 decimais) → 0.123456 → 0.123
            AVAXUSDT: stepSize=1.0 (0 decimais) → 10.5 → 10.0
        """
        try:
            import math

            # Buscar exchange info
            if is_futures:
                exchange_info = await asyncio.to_thread(
                    self.client.futures_exchange_info
                )
            else:
                exchange_info = await asyncio.to_thread(
                    self.client.get_exchange_info
                )

            # Encontrar símbolo
            symbol_info = next(
                (s for s in exchange_info['symbols'] if s['symbol'] == symbol.upper()),
                None
            )

            if not symbol_info:
                logger.warning(f"Símbolo {symbol} não encontrado, usando 3 decimais como fallback")
                return round(quantity, 3)

            # Buscar filtro LOT_SIZE
            lot_size_filter = next(
                (f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'),
                None
            )

            if not lot_size_filter:
                logger.warning(f"LOT_SIZE não encontrado para {symbol}, usando 3 decimais como fallback")
                return round(quantity, 3)

            step_size = float(lot_size_filter['stepSize'])
            min_qty = float(lot_size_filter['minQty'])

            # ✅ CORRIGIDO: Converter quantity para float antes de calcular
            quantity_float = float(quantity)

            # Normalizar para stepSize (arredondar para baixo)
            normalized = math.floor(quantity_float / step_size) * step_size

            # Verificar quantidade mínima
            if normalized < min_qty:
                logger.error(
                    f"⚠️ Quantidade {normalized} menor que mínimo {min_qty} para {symbol}"
                )
                return min_qty

            logger.info(
                f"📊 Quantidade normalizada: {symbol} {quantity} → {normalized} "
                f"(stepSize={step_size}, minQty={min_qty})"
            )

            return normalized

        except Exception as e:
            logger.error(f"Erro ao normalizar quantidade para {symbol}: {e}")
            # Fallback seguro
            return round(quantity, 3)

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
                    "DRIFTUSDT": "0.50",
                }
                price = demo_prices.get(symbol.upper(), "1.00")
                return Decimal(price)

            # Real price - use correct API based on market type
            # For futures, we need to use the futures API endpoint
            import requests

            # Try futures API first (since most of our trading is futures)
            try:
                resp = requests.get(
                    f'https://fapi.binance.com/fapi/v1/ticker/price',
                    params={'symbol': symbol.upper()},
                    timeout=5
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return Decimal(data['price'])
            except:
                pass

            # Fallback to spot API
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
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Create market order

        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            side: buy or sell
            quantity: Order quantity
            test_order: If True, only test the order (default: auto based on demo mode)
            reduce_only: If True, order will only reduce position (for closing positions)
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
                if reduce_only:
                    # Use futures_create_order for reduceOnly support
                    result = self.client.futures_create_order(
                        symbol=symbol,
                        side=side,
                        type="MARKET",
                        quantity=quantity_str,
                        reduceOnly="true"
                    )
                else:
                    # Use simplified order_market for regular orders
                    result = self.client.order_market(
                        symbol=symbol,
                        side=side,
                        quantity=quantity_str
                    )

                # futures_create_order returns different fields than order_market
                return {
                    "success": True,
                    "demo": False,
                    "test_order": False,
                    "order_id": str(result.get("orderId", result.get("id", ""))),
                    "symbol": result["symbol"],
                    "side": result["side"],
                    "type": result["type"],
                    "quantity": result.get("origQty", result.get("quantity", "0")),
                    "price": result.get("price", "0"),
                    "status": result["status"],
                    "filled_quantity": result.get("executedQty", result.get("quantity", "0")),
                    "average_price": result.get("avgPrice", result.get("price", "0")),
                    "commission": result.get("commission", "0"),
                    "timestamp": result.get("transactTime", result.get("updateTime", 0)),
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
                    "success": True,
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
                "success": True,
                "demo": False,
                "account_type": account.get("accountType", "SPOT"),
                "can_trade": account.get("canTrade", False),
                "can_withdraw": account.get("canWithdraw", False),
                "can_deposit": account.get("canDeposit", False),
                "balances": active_balances,
            }

        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {"success": False, "error": str(e)}

    async def get_futures_account(self) -> Dict[str, Any]:
        """Get futures account information"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "account": {
                        "totalWalletBalance": "0.00",
                        "availableBalance": "0.00",
                        "totalUnrealizedProfit": "0.00",
                        "assets": []
                    }
                }

            # Get futures account info
            futures_account = self.client.futures_account()

            return {
                "success": True,
                "demo": False,
                "account": futures_account
            }

        except Exception as e:
            logger.error(f"Error getting futures account info: {e}")
            return {"success": False, "error": str(e)}

    async def get_account_orders(self, symbol=None, limit=100, start_time=None, end_time=None) -> Dict[str, Any]:
        """Get account orders"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "orders": []
                }

            # Get orders from Binance
            orders = self.client.get_all_orders(
                symbol=symbol,
                limit=limit,
                startTime=start_time,
                endTime=end_time
            )

            return {
                "success": True,
                "demo": False,
                "orders": orders
            }

        except Exception as e:
            logger.error(f"Error getting account orders: {e}")
            return {"success": False, "error": str(e)}

    async def get_futures_orders(self, symbol=None, limit=100, start_time=None, end_time=None) -> Dict[str, Any]:
        """Get futures orders history"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "orders": []
                }

            # Get futures orders from Binance
            orders = self.client.futures_get_all_orders(
                symbol=symbol,
                limit=limit,
                startTime=start_time,
                endTime=end_time
            )

            return {
                "success": True,
                "demo": False,
                "orders": orders
            }

        except Exception as e:
            logger.error(f"Error getting futures orders: {e}")
            return {"success": False, "error": str(e)}

    async def get_futures_positions(self) -> Dict[str, Any]:
        """Get futures positions"""
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "positions": []
                }

            # Get futures positions (use asyncio.to_thread for sync client)
            positions = await asyncio.to_thread(
                self.client.futures_position_information
            )

            logger.info(f"🔍 BINANCE API returned {len(positions)} total positions")

            # Filter only positions with size > 0
            active_positions = [
                pos for pos in positions
                if float(pos.get('positionAmt', 0)) != 0
            ]

            logger.info(f"🎯 Filtered to {len(active_positions)} active positions (positionAmt != 0)")

            return {
                "success": True,
                "demo": False,
                "positions": active_positions
            }

        except Exception as e:
            logger.error(f"Error getting futures positions: {e}")
            return {"success": False, "error": str(e)}

    async def get_force_orders(self, symbol=None, start_time=None, end_time=None, limit=100) -> Dict[str, Any]:
        """
        Busca ordens de liquidação (force orders) da Binance

        Args:
            symbol: Símbolo específico (opcional)
            start_time: Timestamp de início (opcional)
            end_time: Timestamp de fim (opcional)
            limit: Limite de resultados (máximo 1000, padrão 100)

        Returns:
            Dict com dados das ordens de liquidação ou erro
        """
        if not self.client:
            logger.warning("🚨 Demo mode: returning mock force orders data")
            return {
                "success": True,
                "demo": True,
                "force_orders": []
            }

        try:
            logger.info(f"🔥 Getting force orders from Binance API", symbol=symbol, limit=limit)

            # Parâmetros para a API
            params = {"limit": min(limit, 1000)}  # Máximo permitido pela Binance

            if symbol:
                params["symbol"] = symbol
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time

            # Chamar endpoint de force orders da Binance
            force_orders = await asyncio.to_thread(
                self.client.futures_forceorders, **params
            )

            logger.info(f"📊 Found {len(force_orders)} force orders", symbol=symbol)

            return {
                "success": True,
                "demo": False,
                "force_orders": force_orders
            }

        except BinanceAPIException as e:
            logger.error(f"Binance API error getting force orders: {e}")
            return {"success": False, "error": f"Binance API error: {e}"}
        except Exception as e:
            logger.error(f"Error getting force orders: {e}")
            return {"success": False, "error": str(e)}

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Busca dados históricos de candles (klines/OHLCV)

        Args:
            symbol: Par de negociação (ex: BTCUSDT)
            interval: Timeframe (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            limit: Quantidade de candles (max 1000)
            start_time: Timestamp de início (ms)
            end_time: Timestamp de fim (ms)

        Returns:
            Dict com success, data (list de klines)
            Cada kline: [timestamp, open, high, low, close, volume, ...]
        """
        if not self.client:
            logger.warning("🔴 get_klines called in DEMO mode - returning empty data")
            return {
                "success": False,
                "demo": True,
                "error": "API keys not configured",
                "data": []
            }

        try:
            logger.info(f"📊 Fetching klines for {symbol} ({interval}, limit={limit})")

            # Parâmetros para API
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": min(limit, 1000)  # Max 1000 por request
            }

            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time

            # Chamar API da Binance (SPOT klines)
            klines = await asyncio.to_thread(
                self.client.get_klines, **params
            )

            logger.info(f"✅ Fetched {len(klines)} klines for {symbol}")

            return {
                "success": True,
                "demo": False,
                "data": klines
            }

        except BinanceAPIException as e:
            logger.error(f"Binance API error getting klines: {e}")
            return {"success": False, "error": f"Binance API error: {e}", "data": []}
        except Exception as e:
            logger.error(f"Error getting klines: {e}")
            return {"success": False, "error": str(e), "data": []}

    async def get_ticker_24h(self, symbol: str) -> Dict[str, Any]:
        """
        Busca ticker 24h do símbolo (preço, volume, mudança %)

        Args:
            symbol: Par de negociação (ex: BTCUSDT)

        Returns:
            Dict com dados de ticker 24h
        """
        if not self.client:
            logger.warning("🔴 get_ticker_24h called in DEMO mode")
            return {
                "success": False,
                "demo": True,
                "error": "API keys not configured",
                "data": {}
            }

        try:
            logger.info(f"📊 Fetching 24h ticker for {symbol}")

            # Chamar API da Binance
            ticker = await asyncio.to_thread(
                self.client.get_ticker, symbol=symbol
            )

            logger.info(f"✅ Fetched ticker for {symbol}: ${ticker.get('lastPrice', 0)}")

            return {
                "success": True,
                "demo": False,
                "data": ticker
            }

        except BinanceAPIException as e:
            logger.error(f"Binance API error getting ticker: {e}")
            return {"success": False, "error": f"Binance API error: {e}", "data": {}}
        except Exception as e:
            logger.error(f"Error getting ticker: {e}")
            return {"success": False, "error": str(e), "data": {}}

    async def create_spot_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create SPOT order on Binance

        Args:
            symbol: Trading pair (ex: BTCUSDT)
            side: BUY or SELL
            order_type: MARKET, LIMIT, STOP_LOSS_LIMIT
            quantity: Amount to trade
            price: Price (for LIMIT orders)
            stop_price: Stop price (for STOP orders)
        """
        try:
            if self.is_demo_mode():
                return {
                    "success": False,
                    "error": "Demo mode - cannot create real orders",
                    "demo": True
                }

            # Normalizar quantidade usando stepSize correto do símbolo
            quantity = await self.normalize_quantity(symbol, quantity, is_futures=False)

            # Prepare order params
            params = {
                'symbol': symbol.upper(),
                'side': side.upper(),
                'type': order_type.upper(),
                'quantity': quantity
            }

            # Add price for LIMIT orders
            if order_type.upper() in ['LIMIT', 'STOP_LOSS_LIMIT']:
                if not price:
                    return {"success": False, "error": "Price required for LIMIT orders"}
                params['price'] = price
                params['timeInForce'] = 'GTC'  # Good Till Cancelled

            # Add stop price for STOP orders
            if 'STOP' in order_type.upper():
                if not stop_price:
                    return {"success": False, "error": "Stop price required for STOP orders"}
                params['stopPrice'] = stop_price

            logger.info(f"🔵 Creating SPOT order: {params}")

            # Execute order
            order_result = await asyncio.to_thread(
                self.client.create_order,
                **params
            )

            logger.info(f"✅ SPOT order created successfully: {order_result.get('orderId')}")

            return {
                "success": True,
                "data": order_result,
                "order_id": str(order_result.get('orderId')),
                "demo": False
            }

        except BinanceAPIException as e:
            logger.error(f"❌ Binance API error creating SPOT order: {e}")
            return {"success": False, "error": f"Binance error: {e.message}"}
        except Exception as e:
            logger.error(f"❌ Error creating SPOT order: {e}")
            return {"success": False, "error": str(e)}

    async def create_futures_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        leverage: int = 1,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create FUTURES order on Binance

        Args:
            symbol: Trading pair (ex: BTCUSDT)
            side: BUY or SELL
            order_type: MARKET, LIMIT, STOP, STOP_MARKET
            quantity: Amount to trade
            price: Price (for LIMIT orders)
            stop_price: Stop price (for STOP orders)
            leverage: Leverage (1-125x)
            stop_loss: Stop loss price
            take_profit: Take profit price
        """
        try:
            if self.is_demo_mode():
                return {
                    "success": False,
                    "error": "Demo mode - cannot create real orders",
                    "demo": True
                }

            # 1. Set leverage first
            if leverage > 1:
                logger.info(f"🔧 Setting leverage to {leverage}x for {symbol}")
                await asyncio.to_thread(
                    self.client.futures_change_leverage,
                    symbol=symbol.upper(),
                    leverage=leverage
                )

            # 2. Normalizar quantidade usando stepSize correto do símbolo
            quantity = await self.normalize_quantity(symbol, quantity, is_futures=True)

            # Prepare main order params
            params = {
                'symbol': symbol.upper(),
                'side': side.upper(),
                'type': order_type.upper() if order_type.upper() != 'STOP' else 'STOP_MARKET',
                'quantity': quantity
            }

            # Add price for LIMIT orders
            if order_type.upper() == 'LIMIT':
                if not price:
                    return {"success": False, "error": "Price required for LIMIT orders"}
                params['price'] = price
                params['timeInForce'] = 'GTC'

            # Add stop price for STOP orders
            if 'STOP' in order_type.upper():
                if not stop_price:
                    return {"success": False, "error": "Stop price required for STOP orders"}
                params['stopPrice'] = stop_price

            logger.info(f"🔵 Creating FUTURES order: {params}")

            # 3. Execute main order
            order_result = await asyncio.to_thread(
                self.client.futures_create_order,
                **params
            )

            logger.info(f"✅ FUTURES order created successfully: {order_result.get('orderId')}")

            # Inicializar IDs de SL/TP como None
            sl_order_id = None
            tp_order_id = None

            # 4. Add Stop Loss if provided
            if stop_loss:
                sl_side = 'SELL' if side.upper() == 'BUY' else 'BUY'
                sl_params = {
                    'symbol': symbol.upper(),
                    'side': sl_side,
                    'type': 'STOP_MARKET',
                    'stopPrice': stop_loss,
                    'closePosition': 'true'  # Close entire position
                }

                logger.info(f"🛑 Creating Stop Loss: {sl_params}")

                sl_result = await asyncio.to_thread(
                    self.client.futures_create_order,
                    **sl_params
                )

                sl_order_id = str(sl_result.get('orderId'))
                logger.info(f"✅ Stop Loss created: {sl_order_id}")

            # 5. Add Take Profit if provided
            if take_profit:
                tp_side = 'SELL' if side.upper() == 'BUY' else 'BUY'
                tp_params = {
                    'symbol': symbol.upper(),
                    'side': tp_side,
                    'type': 'TAKE_PROFIT_MARKET',
                    'stopPrice': take_profit,
                    'closePosition': 'true'  # Close entire position
                }

                logger.info(f"🎯 Creating Take Profit: {tp_params}")

                tp_result = await asyncio.to_thread(
                    self.client.futures_create_order,
                    **tp_params
                )

                tp_order_id = str(tp_result.get('orderId'))
                logger.info(f"✅ Take Profit created: {tp_order_id}")

            # Retornar IDs de todas as ordens
            return {
                "success": True,
                "data": order_result,
                "order_id": str(order_result.get('orderId')),
                "stop_loss_order_id": sl_order_id,  # ✅ NOVO: ID do Stop Loss
                "take_profit_order_id": tp_order_id,  # ✅ NOVO: ID do Take Profit
                "demo": False
            }

        except BinanceAPIException as e:
            logger.error(f"❌ Binance API error creating FUTURES order: {e}")
            return {"success": False, "error": f"Binance error: {e.message}"}
        except Exception as e:
            logger.error(f"❌ Error creating FUTURES order: {e}")
            return {"success": False, "error": str(e)}

    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ) -> Dict[str, Any]:
        """
        Create STOP_MARKET order for stop loss

        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            side: SELL (for long) or BUY (for short)
            quantity: Quantity to close
            stop_price: Price to trigger stop loss

        Returns:
            Dict with order result
        """
        try:
            if self.is_demo_mode():
                logger.info(f"🛑 Demo mode: would create Stop Loss at {stop_price}")
                return {
                    "success": True,
                    "demo": True,
                    "orderId": "DEMO_SL_" + str(int(asyncio.get_event_loop().time() * 1000))
                }

            params = {
                'symbol': symbol.upper(),
                'side': side.upper(),
                'type': 'STOP_MARKET',
                'quantity': quantity,
                'stopPrice': stop_price,
                'timeInForce': 'GTC'
            }

            logger.info(f"🛑 Creating Stop Loss order: {params}")

            result = await asyncio.to_thread(
                self.client.futures_create_order,
                **params
            )

            logger.info(f"✅ Stop Loss order created: {result.get('orderId')}")

            return {
                "success": True,
                "demo": False,
                "orderId": str(result.get('orderId')),
                "symbol": symbol,
                "stopPrice": stop_price
            }

        except BinanceAPIException as e:
            logger.error(f"❌ Binance API error creating Stop Loss: {e}")
            return {"success": False, "error": f"Binance error: {e.message}"}
        except Exception as e:
            logger.error(f"❌ Error creating Stop Loss: {e}")
            return {"success": False, "error": str(e)}

    async def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ) -> Dict[str, Any]:
        """
        Create TAKE_PROFIT_MARKET order

        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            side: SELL (for long) or BUY (for short)
            quantity: Quantity to close
            stop_price: Price to trigger take profit

        Returns:
            Dict with order result
        """
        try:
            if self.is_demo_mode():
                logger.info(f"🎯 Demo mode: would create Take Profit at {stop_price}")
                return {
                    "success": True,
                    "demo": True,
                    "orderId": "DEMO_TP_" + str(int(asyncio.get_event_loop().time() * 1000))
                }

            params = {
                'symbol': symbol.upper(),
                'side': side.upper(),
                'type': 'TAKE_PROFIT_MARKET',
                'quantity': quantity,
                'stopPrice': stop_price,
                'timeInForce': 'GTC'
            }

            logger.info(f"🎯 Creating Take Profit order: {params}")

            result = await asyncio.to_thread(
                self.client.futures_create_order,
                **params
            )

            logger.info(f"✅ Take Profit order created: {result.get('orderId')}")

            return {
                "success": True,
                "demo": False,
                "orderId": str(result.get('orderId')),
                "symbol": symbol,
                "stopPrice": stop_price
            }

        except BinanceAPIException as e:
            logger.error(f"❌ Binance API error creating Take Profit: {e}")
            return {"success": False, "error": f"Binance error: {e.message}"}
        except Exception as e:
            logger.error(f"❌ Error creating Take Profit: {e}")
            return {"success": False, "error": str(e)}

    async def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """
        Set leverage for a futures symbol

        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            leverage: Leverage level (1-125x)

        Returns:
            Dict with success status
        """
        try:
            if self.is_demo_mode():
                logger.info(f"🔧 Demo mode: would set leverage to {leverage}x for {symbol}")
                return {"success": True, "demo": True, "leverage": leverage}

            logger.info(f"🔧 Setting leverage to {leverage}x for {symbol}")

            result = await asyncio.to_thread(
                self.client.futures_change_leverage,
                symbol=symbol.upper(),
                leverage=leverage
            )

            logger.info(f"✅ Leverage set successfully for {symbol}: {leverage}x")

            return {
                "success": True,
                "demo": False,
                "leverage": result.get("leverage", leverage),
                "symbol": symbol
            }

        except BinanceAPIException as e:
            logger.error(f"❌ Binance API error setting leverage: {e}")
            return {"success": False, "error": f"Binance error: {e.message}"}
        except Exception as e:
            logger.error(f"❌ Error setting leverage: {e}")
            return {"success": False, "error": str(e)}


# Factory function para criar connector
def create_binance_connector(
    api_key: str = None, api_secret: str = None, testnet: bool = True
) -> BinanceConnector:
    """Create Binance connector instance"""
    return BinanceConnector(api_key=api_key, api_secret=api_secret, testnet=testnet)
