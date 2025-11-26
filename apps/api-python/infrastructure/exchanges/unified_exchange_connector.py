"""
Unified Exchange Connector
Usa CCXT como primário + conectores nativos como fallback
Suporta múltiplas exchanges com API unificada
"""

import asyncio
import ccxt.async_support as ccxt
from typing import Dict, Any, Optional, List
import structlog
from decimal import Decimal

from infrastructure.exchanges.binance_connector import BinanceConnector

logger = structlog.get_logger()


class UnifiedExchangeConnector:
    """
    Connector unificado que suporta múltiplas exchanges
    Usa CCXT como primário e conectores nativos como fallback
    """

    def __init__(
        self,
        exchange_name: str = "binance",
        api_key: str = None,
        api_secret: str = None,
        testnet: bool = False,
        market_type: str = "spot"  # 'spot' ou 'future'
    ):
        """
        Initialize unified connector

        Args:
            exchange_name: Nome da exchange (binance, bybit, okx, etc)
            api_key: API key
            api_secret: API secret
            testnet: Usar testnet
            market_type: Tipo de mercado ('spot' ou 'future')
        """
        self.exchange_name = exchange_name.lower()
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.market_type = market_type

        # CCXT Client (primário)
        self.ccxt_client = None
        self.native_client = None

        # Inicializar CCXT
        try:
            self._init_ccxt()
            logger.info(
                f"✅ CCXT connector initialized",
                exchange=exchange_name,
                market_type=market_type,
                testnet=testnet
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize CCXT: {e}")

        # Inicializar connector nativo como fallback (apenas Binance por enquanto)
        if exchange_name == "binance":
            try:
                self.native_client = BinanceConnector(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=testnet
                )
                logger.info("✅ Native Binance connector initialized as fallback")
            except Exception as e:
                logger.error(f"⚠️ Failed to initialize native connector: {e}")

    def _init_ccxt(self):
        """Inicializa cliente CCXT"""
        exchange_class = getattr(ccxt, self.exchange_name, None)
        if not exchange_class:
            raise ValueError(f"Exchange {self.exchange_name} not supported by CCXT")

        config = {
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': self.market_type,  # 'spot' ou 'future'
            }
        }

        # Configurar testnet se aplicável
        if self.testnet and self.exchange_name == 'binance':
            if self.market_type == 'future':
                config['urls'] = {'api': 'https://testnet.binancefuture.com'}
            else:
                config['urls'] = {'api': 'https://testnet.binance.vision'}

        self.ccxt_client = exchange_class(config)

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500,
        since: Optional[int] = None,
        auto_detect_market: bool = True
    ) -> Dict[str, Any]:
        """
        Busca dados históricos de candles (OHLCV)
        Auto-detecta se deve usar SPOT ou FUTURES

        Args:
            symbol: Par de negociação (ex: BTC/USDT para CCXT, BTCUSDT para nativo)
            interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Quantidade de candles
            since: Timestamp de início (ms)
            auto_detect_market: Se True, tenta FUTURES primeiro, depois SPOT

        Returns:
            Dict com success, data, market_type
        """
        # Normalizar símbolo para CCXT (BTC/USDT)
        ccxt_symbol = self._normalize_symbol_ccxt(symbol)

        # Tentar CCXT primeiro
        if self.ccxt_client:
            result = await self._get_klines_ccxt(
                ccxt_symbol, interval, limit, since, auto_detect_market
            )
            if result['success']:
                return result

        # Fallback: Nativo (apenas Binance)
        if self.native_client and self.exchange_name == 'binance':
            logger.warning("⚠️ CCXT failed, falling back to native Binance")
            native_symbol = symbol.replace('/', '')  # BTCUSDT
            return await self._get_klines_native(native_symbol, interval, limit, auto_detect_market)

        return {
            'success': False,
            'error': 'Failed to fetch klines from all sources',
            'data': []
        }

    async def _get_klines_ccxt(
        self,
        symbol: str,
        interval: str,
        limit: int,
        since: Optional[int],
        auto_detect: bool
    ) -> Dict[str, Any]:
        """Busca klines usando CCXT"""
        try:
            # Tentar com tipo de mercado configurado
            logger.info(
                f"📊 Fetching klines via CCXT",
                symbol=symbol,
                interval=interval,
                market=self.market_type
            )

            ohlcv = await self.ccxt_client.fetch_ohlcv(
                symbol,
                timeframe=interval,
                since=since,
                limit=limit
            )

            # Converter formato CCXT para nosso formato
            klines = self._convert_ccxt_to_binance_format(ohlcv)

            logger.info(f"✅ Fetched {len(klines)} klines via CCXT ({self.market_type})")

            return {
                'success': True,
                'data': klines,
                'market_type': self.market_type,
                'source': 'ccxt'
            }

        except Exception as e:
            error_msg = str(e).lower()

            # Se auto-detect ativado e falhou, tentar outro mercado
            if auto_detect and 'symbol' in error_msg:
                logger.warning(f"Symbol not found in {self.market_type}, trying alternate market")
                alternate_market = 'spot' if self.market_type == 'future' else 'future'

                try:
                    # Temporariamente mudar tipo de mercado
                    self.ccxt_client.options['defaultType'] = alternate_market

                    ohlcv = await self.ccxt_client.fetch_ohlcv(
                        symbol,
                        timeframe=interval,
                        since=since,
                        limit=limit
                    )

                    klines = self._convert_ccxt_to_binance_format(ohlcv)

                    logger.info(f"✅ Fetched {len(klines)} klines via CCXT ({alternate_market})")

                    # Restaurar tipo original
                    self.ccxt_client.options['defaultType'] = self.market_type

                    return {
                        'success': True,
                        'data': klines,
                        'market_type': alternate_market,
                        'source': 'ccxt'
                    }

                except Exception as e2:
                    logger.error(f"❌ Failed in alternate market too: {e2}")
                    # Restaurar tipo original
                    self.ccxt_client.options['defaultType'] = self.market_type

            logger.error(f"CCXT error: {e}")
            return {
                'success': False,
                'error': f"CCXT error: {e}",
                'data': []
            }

    async def _get_klines_native(
        self,
        symbol: str,
        interval: str,
        limit: int,
        auto_detect: bool
    ) -> Dict[str, Any]:
        """Busca klines usando connector nativo da Binance"""
        try:
            # Tentar FUTURES primeiro se auto-detect
            if auto_detect or self.market_type == 'future':
                # Verificar se BinanceConnector tem método futures_klines
                if hasattr(self.native_client.client, 'futures_klines'):
                    try:
                        klines = await asyncio.to_thread(
                            self.native_client.client.futures_klines,
                            symbol=symbol,
                            interval=interval,
                            limit=limit
                        )
                        logger.info(f"✅ Fetched {len(klines)} klines via native Binance (FUTURES)")
                        return {
                            'success': True,
                            'data': klines,
                            'market_type': 'future',
                            'source': 'native'
                        }
                    except Exception as e:
                        if not auto_detect:
                            raise
                        logger.warning(f"Futures failed, trying spot: {e}")

            # Tentar SPOT
            result = await self.native_client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )

            if result['success']:
                result['market_type'] = 'spot'
                result['source'] = 'native'
                return result

            return result

        except Exception as e:
            logger.error(f"Native connector error: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': []
            }

    def _normalize_symbol_ccxt(self, symbol: str) -> str:
        """
        Normaliza símbolo para formato CCXT (BTC/USDT)
        """
        if '/' in symbol:
            return symbol  # Já está no formato CCXT

        # Converter BTCUSDT -> BTC/USDT
        # Assumir que termina com USDT, BUSD, BTC, ETH, etc
        quote_currencies = ['USDT', 'BUSD', 'BTC', 'ETH', 'BNB', 'USDC']

        for quote in quote_currencies:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}/{quote}"

        # Fallback: assumir USDT
        return f"{symbol[:-4]}/USDT"

    def _convert_ccxt_to_binance_format(self, ohlcv: List) -> List:
        """
        Converte formato CCXT para formato Binance
        CCXT: [timestamp, open, high, low, close, volume]
        Binance: [timestamp, open, high, low, close, volume, close_time, quote_volume, trades, ...]
        """
        klines = []
        for candle in ohlcv:
            # CCXT retorna: [timestamp, open, high, low, close, volume]
            klines.append([
                candle[0],  # open_time
                str(candle[1]),  # open
                str(candle[2]),  # high
                str(candle[3]),  # low
                str(candle[4]),  # close
                str(candle[5]),  # volume
                candle[0] + 3600000 - 1,  # close_time (aproximado)
                "0",  # quote_volume (não disponível)
                0,  # trades (não disponível)
                "0",  # taker_buy_base
                "0",  # taker_buy_quote
                "0"   # ignore
            ])
        return klines

    async def close(self):
        """Fecha conexões"""
        if self.ccxt_client:
            await self.ccxt_client.close()
            logger.info("✅ CCXT client closed")


# Funções de conveniência
async def get_unified_connector(
    exchange: str,
    api_key: str,
    api_secret: str,
    testnet: bool = False,
    operation_type: str = 'spot'
) -> UnifiedExchangeConnector:
    """
    Cria connector unificado baseado nos parâmetros

    Args:
        exchange: Nome da exchange (binance, bybit, okx)
        api_key: API key
        api_secret: API secret
        testnet: Usar testnet
        operation_type: Tipo de operação ('spot' ou 'futures')

    Returns:
        UnifiedExchangeConnector configurado
    """
    market_type = 'future' if operation_type == 'futures' else 'spot'

    return UnifiedExchangeConnector(
        exchange_name=exchange,
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet,
        market_type=market_type
    )
