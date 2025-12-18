"""
Binance Exchange Connector
Conecta com a API da Binance para executar ordens reais
"""

import asyncio
import os
import time
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
        # IMPORTANTE: Usar requests_params para aumentar recvWindow (janela de tolerância de timestamp)
        self.client = Client(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
            requests_params={'timeout': 30}
        )

        # Sincronizar timestamp com servidor Binance para evitar erro -1021
        # "Timestamp for this request was Xms ahead of the server's time"
        self._sync_time_with_server()

        logger.info("Binance connector initialized with time sync", testnet=testnet)

    def _sync_time_with_server(self):
        """
        Sincroniza o relogio local com o servidor da Binance.
        Resolve erro -1021 (Timestamp ahead/behind server time).
        """
        try:
            # Obter tempo do servidor Binance
            server_time = self.client.get_server_time()
            server_timestamp = server_time['serverTime']

            # Calcular offset entre tempo local e servidor
            local_timestamp = int(time.time() * 1000)
            self.time_offset = server_timestamp - local_timestamp

            # Aplicar offset no client da Binance
            # A biblioteca python-binance usa timestamp_offset internamente
            self.client.timestamp_offset = self.time_offset

            logger.info(
                "Binance time sync completed",
                time_offset_ms=self.time_offset,
                server_time=server_timestamp,
                local_time=local_timestamp
            )

            # Se offset for muito grande (>10 segundos), alertar
            if abs(self.time_offset) > 10000:
                logger.warning(
                    f"Large time offset detected: {self.time_offset}ms. "
                    "Consider syncing your system clock."
                )

        except Exception as e:
            self.time_offset = 0
            logger.warning(
                f"Could not sync time with Binance server: {e}. "
                "Using local time (may cause timestamp errors)."
            )

    def is_demo_mode(self) -> bool:
        """Legacy method - always returns False (demo mode removed)"""
        return False

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

            # Normalizar para stepSize (arredondar para CIMA para garantir margem mínima)
            # Usar ceil garante que a margem efetiva seja >= margem configurada
            normalized = math.ceil(quantity_float / step_size) * step_size

            # Arredondar para evitar problemas de ponto flutuante
            decimals = len(str(step_size).split('.')[-1]) if '.' in str(step_size) else 0
            normalized = round(normalized, decimals)

            # Verificar quantidade mínima
            if normalized < min_qty:
                logger.error(
                    f"⚠️ Quantidade {normalized} menor que mínimo {min_qty} para {symbol}"
                )
                return min_qty

            logger.info(
                f"📊 Quantidade normalizada: {symbol} {quantity} → {normalized} "
                f"(stepSize={step_size}, minQty={min_qty}, ceil=True)"
            )

            return normalized

        except Exception as e:
            logger.error(f"Erro ao normalizar quantidade para {symbol}: {e}")
            # Fallback seguro
            return round(quantity, 3)

    async def normalize_price(self, symbol: str, price: float, is_futures: bool = True) -> float:
        """
        Normaliza preço baseado no tickSize do símbolo (filtro PRICE_FILTER)

        Args:
            symbol: Par de negociação (ex: BTCUSDT, ETHUSDT)
            price: Preço original
            is_futures: Se é futures (usa futures_exchange_info)

        Returns:
            Preço normalizado segundo tickSize da Binance

        Exemplos:
            BTCUSDT: tickSize=0.10 (1 decimal) → 45123.456 → 45123.40
            ETHUSDT: tickSize=0.01 (2 decimais) → 3850.123 → 3850.12
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
                logger.warning(f"Símbolo {symbol} não encontrado, usando 2 decimais como fallback")
                return round(price, 2)

            # Buscar filtro PRICE_FILTER
            price_filter = next(
                (f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'),
                None
            )

            if not price_filter:
                logger.warning(f"PRICE_FILTER não encontrado para {symbol}, usando 2 decimais como fallback")
                return round(price, 2)

            tick_size = float(price_filter['tickSize'])

            # Normalizar para tickSize (arredondar para baixo para não ultrapassar)
            normalized = math.floor(price / tick_size) * tick_size

            # Arredondar para evitar problemas de ponto flutuante
            decimals = len(str(tick_size).split('.')[-1]) if '.' in str(tick_size) else 0
            normalized = round(normalized, decimals)

            logger.info(
                f"💰 Preço normalizado: {symbol} {price} → {normalized} "
                f"(tickSize={tick_size})"
            )

            return normalized

        except Exception as e:
            logger.error(f"Erro ao normalizar preço para {symbol}: {e}")
            # Fallback seguro
            return round(price, 2)

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

    async def get_futures_income_history(self, income_type=None, symbol=None, start_time=None, end_time=None, limit=1000) -> Dict[str, Any]:
        """
        Busca histórico de income (P&L realizado, fees, funding, etc) da Binance Futures

        Args:
            income_type: Tipo de income (REALIZED_PNL, COMMISSION, FUNDING_FEE, etc)
            symbol: Símbolo específico (opcional)
            start_time: Timestamp de início em milissegundos (opcional)
            end_time: Timestamp de fim em milissegundos (opcional)
            limit: Limite de resultados (máximo 1000, padrão 1000)

        Returns:
            Dict com histórico de income ou erro

        Income Types disponíveis:
            - REALIZED_PNL: P&L realizado (posições fechadas)
            - COMMISSION: Taxas de trading
            - FUNDING_FEE: Taxas de funding
            - TRANSFER: Transferências
            - WELCOME_BONUS: Bônus
            - INSURANCE_CLEAR: Liquidações
        """
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "income_history": []
                }

            # Parâmetros para a API
            params = {"limit": min(limit, 1000)}

            if income_type:
                params["incomeType"] = income_type
            if symbol:
                params["symbol"] = symbol
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time

            # Chamar endpoint de income history da Binance
            income_history = await asyncio.to_thread(
                self.client.futures_income_history, **params
            )

            logger.info(f"📊 Retrieved {len(income_history)} income records",
                       income_type=income_type,
                       symbol=symbol)

            return {
                "success": True,
                "demo": False,
                "income_history": income_history
            }

        except Exception as e:
            logger.error(f"Error getting futures income history: {e}")
            return {"success": False, "error": str(e)}

    async def get_closed_positions_from_orders(self, symbol=None, limit=500, start_time=None, end_time=None) -> Dict[str, Any]:
        """
        Reconstrói histórico de posições fechadas a partir das orders futures

        Analisa orders de abertura e fechamento para identificar posições completas.
        Útil para mostrar histórico de posições no frontend.

        Args:
            symbol: Filtrar por símbolo específico
            limit: Número máximo de orders a buscar
            start_time: Timestamp início em ms
            end_time: Timestamp fim em ms

        Returns:
            Dict com posições fechadas identificadas
        """
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "closed_positions": []
                }

            # Buscar todas as orders futures
            orders_result = await self.get_futures_orders(
                symbol=symbol,
                limit=limit,
                start_time=start_time,
                end_time=end_time
            )

            if not orders_result['success']:
                return orders_result

            orders = orders_result['orders']

            # Filtrar apenas orders executadas (FILLED)
            filled_orders = [o for o in orders if o['status'] == 'FILLED']

            # Agrupar por símbolo
            positions_by_symbol = {}

            for order in filled_orders:
                symbol = order['symbol']
                side = order['side']  # BUY ou SELL
                qty = float(order['executedQty'])
                price = float(order['avgPrice']) if order.get('avgPrice') else float(order.get('price', 0))
                timestamp = order['time']
                reduce_only = order.get('reduceOnly', False)

                if symbol not in positions_by_symbol:
                    positions_by_symbol[symbol] = {
                        'open_qty': 0,
                        'orders': []
                    }

                # Determinar se é abertura ou fechamento
                if side == 'BUY':
                    if reduce_only:
                        # Fechando SHORT
                        positions_by_symbol[symbol]['open_qty'] += qty
                    else:
                        # Abrindo LONG
                        positions_by_symbol[symbol]['open_qty'] += qty
                else:  # SELL
                    if reduce_only:
                        # Fechando LONG
                        positions_by_symbol[symbol]['open_qty'] -= qty
                    else:
                        # Abrindo SHORT
                        positions_by_symbol[symbol]['open_qty'] -= qty

                positions_by_symbol[symbol]['orders'].append({
                    'orderId': order['orderId'],
                    'side': side,
                    'qty': qty,
                    'price': price,
                    'timestamp': timestamp,
                    'reduceOnly': reduce_only,
                    'realized_pnl': float(order.get('realizedPnl', 0))
                })

            # Identificar posições que foram totalmente fechadas
            closed_positions = []

            for symbol, data in positions_by_symbol.items():
                # Se qty final é próxima de zero, posição foi fechada
                if abs(data['open_qty']) < 0.001:
                    # Calcular P&L total
                    total_realized_pnl = sum(o['realized_pnl'] for o in data['orders'])

                    # Encontrar primeira e última order
                    sorted_orders = sorted(data['orders'], key=lambda x: x['timestamp'])
                    first_order = sorted_orders[0]
                    last_order = sorted_orders[-1]

                    closed_positions.append({
                        'symbol': symbol,
                        'side': 'LONG' if first_order['side'] == 'BUY' else 'SHORT',
                        'entry_time': first_order['timestamp'],
                        'close_time': last_order['timestamp'],
                        'entry_price': first_order['price'],
                        'exit_price': last_order['price'],
                        'quantity': sum(o['qty'] for o in data['orders'] if not o['reduceOnly']),
                        'realized_pnl': total_realized_pnl,
                        'orders_count': len(data['orders']),
                        'status': 'closed'
                    })

            logger.info(f"📊 Identified {len(closed_positions)} closed positions from {len(filled_orders)} orders")

            return {
                "success": True,
                "demo": False,
                "closed_positions": closed_positions
            }

        except Exception as e:
            logger.error(f"Error reconstructing closed positions: {e}", exc_info=True)
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
            # IMPORTANT: Since Dec 9, 2025, must use Algo Order API for STOP_MARKET orders
            if stop_loss:
                sl_side = 'SELL' if side.upper() == 'BUY' else 'BUY'

                logger.info(f"🛑 Creating Stop Loss via Algo Order API: {symbol} {sl_side} @ {stop_loss}")

                try:
                    sl_result = await self._create_algo_conditional_order(
                        symbol=symbol.upper(),
                        side=sl_side,
                        order_type='STOP_MARKET',
                        trigger_price=stop_loss,
                        close_position=True  # Auto-cancels when position closes!
                    )
                    if sl_result.get('success'):
                        sl_order_id = str(sl_result.get('algoId'))
                        logger.info(f"✅ Stop Loss created: {sl_order_id}")
                    else:
                        logger.warning(f"⚠️ Failed to create Stop Loss: {sl_result.get('error')}")
                except Exception as sl_error:
                    logger.warning(f"⚠️ Failed to create Stop Loss: {sl_error}")

            # 5. Add Take Profit if provided
            # IMPORTANT: Since Dec 9, 2025, must use Algo Order API for TAKE_PROFIT_MARKET orders
            if take_profit:
                tp_side = 'SELL' if side.upper() == 'BUY' else 'BUY'

                logger.info(f"🎯 Creating Take Profit via Algo Order API: {symbol} {tp_side} @ {take_profit}")

                try:
                    tp_result = await self._create_algo_conditional_order(
                        symbol=symbol.upper(),
                        side=tp_side,
                        order_type='TAKE_PROFIT_MARKET',
                        trigger_price=take_profit,
                        close_position=True  # Auto-cancels when position closes!
                    )
                    if tp_result.get('success'):
                        tp_order_id = str(tp_result.get('algoId'))
                        logger.info(f"✅ Take Profit created: {tp_order_id}")
                    else:
                        logger.warning(f"⚠️ Failed to create Take Profit: {tp_result.get('error')}")
                except Exception as tp_error:
                    logger.warning(f"⚠️ Failed to create Take Profit: {tp_error}")

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

    # ============================================================================
    # UNIFIED ORDER WITH SL/TP - STRATEGY PATTERN
    # ============================================================================
    async def execute_order_with_sl_tp(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        quantity: float,
        leverage: int = 10,
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        **kwargs  # Extra params (position_side ignored for Binance)
    ) -> Dict[str, Any]:
        """
        Execute futures order with Stop Loss and Take Profit in a SINGLE operation.

        BINANCE STRATEGY: Order + SL/TP são criados juntos na mesma chamada.
        O create_futures_order já suporta os parâmetros stop_loss e take_profit.

        Args:
            symbol: Trading pair (e.g., "ETHUSDT")
            side: "BUY" or "SELL"
            quantity: Order quantity
            leverage: Leverage multiplier (default 10)
            stop_loss_price: Stop loss price (optional)
            take_profit_price: Take profit price (optional)
            **kwargs: Additional params (position_side is ignored for Binance)

        Returns:
            Dict with:
                - success: bool
                - order_id: main order ID
                - stop_loss_order_id: SL order ID (if created)
                - take_profit_order_id: TP order ID (if created)
                - avgPrice: executed price
                - executedQty: executed quantity
        """
        try:
            logger.info(
                f"🔵 BINANCE execute_order_with_sl_tp: {symbol} {side} qty={quantity} "
                f"leverage={leverage}x SL={stop_loss_price} TP={take_profit_price}"
            )

            # Normalizar preços de SL/TP para evitar erro de precisão (-1111)
            normalized_sl = None
            normalized_tp = None

            if stop_loss_price:
                normalized_sl = await self.normalize_price(symbol, stop_loss_price, is_futures=True)
                logger.info(f"   SL normalizado: {stop_loss_price} → {normalized_sl}")

            if take_profit_price:
                normalized_tp = await self.normalize_price(symbol, take_profit_price, is_futures=True)
                logger.info(f"   TP normalizado: {take_profit_price} → {normalized_tp}")

            # BINANCE: Usar create_futures_order que JÁ suporta SL/TP integrado
            result = await self.create_futures_order(
                symbol=symbol,
                side=side.upper(),
                order_type="MARKET",
                quantity=quantity,
                leverage=leverage,
                stop_loss=normalized_sl,
                take_profit=normalized_tp
            )

            if result.get("success"):
                logger.info(
                    f"✅ BINANCE Order + SL/TP criados com sucesso: "
                    f"order_id={result.get('order_id')}, "
                    f"sl_id={result.get('stop_loss_order_id')}, "
                    f"tp_id={result.get('take_profit_order_id')}"
                )

                # Retornar no formato padronizado para o bot_broadcast_service
                return {
                    "success": True,
                    "orderId": result.get("order_id"),
                    "order_id": result.get("order_id"),
                    "stop_loss_order_id": result.get("stop_loss_order_id"),
                    "take_profit_order_id": result.get("take_profit_order_id"),
                    "avgPrice": result.get("data", {}).get("avgPrice"),
                    "executedQty": result.get("data", {}).get("executedQty"),
                    "data": result.get("data"),
                    "demo": result.get("demo", False)
                }
            else:
                logger.error(f"❌ BINANCE execute_order_with_sl_tp failed: {result.get('error')}")
                return result

        except Exception as e:
            logger.error(f"❌ BINANCE execute_order_with_sl_tp error: {e}")
            return {"success": False, "error": str(e)}


    # ============================================================================
    # BINANCE ALGO ORDER API (NEW - December 2025)
    # Required for STOP_MARKET, TAKE_PROFIT_MARKET orders after API migration
    # ============================================================================
    async def _create_algo_conditional_order(
        self,
        symbol: str,
        side: str,
        order_type: str,  # STOP_MARKET or TAKE_PROFIT_MARKET
        trigger_price: float,
        close_position: bool = True,  # Use closePosition instead of quantity
        working_type: str = "CONTRACT_PRICE"
    ) -> Dict[str, Any]:
        """
        Create conditional order via Binance NEW Algo Order API.

        Since Dec 9, 2025, conditional orders (STOP_MARKET, TAKE_PROFIT_MARKET, etc.)
        must be created via POST /fapi/v1/algoOrder with algoType=CONDITIONAL.

        IMPORTANT: Using closePosition=true means the order will:
        - Close the ENTIRE position when triggered
        - Auto-cancel when position is closed manually
        - NOT require quantity parameter

        Args:
            symbol: Trading pair (e.g., ETHUSDT)
            side: BUY or SELL
            order_type: STOP_MARKET or TAKE_PROFIT_MARKET
            trigger_price: Price that triggers the order
            close_position: If True, closes entire position (like old closePosition param)
            working_type: MARK_PRICE or CONTRACT_PRICE (default)

        Returns:
            Dict with success, algoId, and order details
        """
        import hashlib
        import hmac
        import requests

        try:
            # Base URL for futures API
            base_url = "https://fapi.binance.com"
            endpoint = "/fapi/v1/algoOrder"

            # Get current timestamp with offset
            timestamp = int(time.time() * 1000) + self.time_offset

            # Prepare parameters - using closePosition instead of quantity
            # When closePosition=true, do NOT include quantity or reduceOnly
            params = {
                'symbol': symbol.upper(),
                'side': side.upper(),
                'type': order_type.upper(),
                'algoType': 'CONDITIONAL',
                'triggerPrice': str(trigger_price),
                'closePosition': 'true' if close_position else 'false',
                'workingType': working_type,
                'timestamp': timestamp,
                'recvWindow': 60000  # 60 seconds tolerance
            }

            # Create query string
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])

            # Generate signature
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            # Add signature to params
            params['signature'] = signature

            # Headers
            headers = {
                'X-MBX-APIKEY': self.api_key
            }

            logger.info(f"🔵 Calling Binance Algo Order API: {order_type} {side} {symbol} @ {trigger_price}")

            # Make request
            response = await asyncio.to_thread(
                requests.post,
                f"{base_url}{endpoint}",
                params=params,
                headers=headers,
                timeout=30
            )

            result = response.json()

            if response.status_code == 200:
                logger.info(f"✅ Algo Order created: {result.get('algoId')} - {order_type}")
                return {
                    "success": True,
                    "algoId": result.get('algoId'),
                    "clientAlgoId": result.get('clientAlgoId'),
                    "algoStatus": result.get('algoStatus'),
                    "triggerPrice": result.get('triggerPrice'),
                    "data": result
                }
            else:
                error_msg = result.get('msg', 'Unknown error')
                error_code = result.get('code', 'N/A')
                logger.error(f"❌ Algo Order API error: [{error_code}] {error_msg}")
                return {
                    "success": False,
                    "error": f"[{error_code}] {error_msg}",
                    "data": result
                }

        except Exception as e:
            logger.error(f"❌ Exception creating Algo Order: {e}")
            return {"success": False, "error": str(e)}


    async def get_open_orders(self, symbol: str = None) -> Dict[str, Any]:
        """
        Get open orders for a symbol or all symbols

        Args:
            symbol: Trading pair (optional, if None returns all)

        Returns:
            Dict with open orders list
        """
        try:
            if self.is_demo_mode():
                return {
                    "success": True,
                    "demo": True,
                    "orders": []
                }

            # Get futures open orders
            if symbol:
                orders = await asyncio.to_thread(
                    self.client.futures_get_open_orders,
                    symbol=symbol.upper()
                )
            else:
                orders = await asyncio.to_thread(
                    self.client.futures_get_open_orders
                )

            logger.info(f"📋 Found {len(orders)} open orders" + (f" for {symbol}" if symbol else ""))

            return {
                "success": True,
                "demo": False,
                "orders": orders
            }

        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return {"success": False, "error": str(e), "orders": []}

    async def close(self):
        """
        Close connector and cleanup resources.
        For Binance python-binance client, there's no explicit close needed,
        but we implement this for interface compatibility with other connectors.
        """
        try:
            # python-binance Client doesn't have explicit close
            # Just log that we're done
            logger.info("BinanceConnector closed (no cleanup needed)")
        except Exception as e:
            logger.warning(f"Error during BinanceConnector close: {e}")


# Factory function para criar connector
def create_binance_connector(
    api_key: str = None, api_secret: str = None, testnet: bool = True
) -> BinanceConnector:
    """Create Binance connector instance"""
    return BinanceConnector(api_key=api_key, api_secret=api_secret, testnet=testnet)
