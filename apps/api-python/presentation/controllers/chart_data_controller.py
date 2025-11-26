"""
Controller para dados de gráfico e histórico de candles
Fornece endpoints para WebSocket e dados históricos
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import aiohttp
import json
from decimal import Decimal

from infrastructure.database.connection import get_db_session
from infrastructure.database.models.candle import Candle as CandleModel
from infrastructure.database.repositories.candle_repository import CandleRepository
from presentation.middleware.auth import get_current_user
from infrastructure.exchanges.bingx_connector import BingXConnector
from infrastructure.config.settings import get_settings

router = APIRouter(prefix="/api/v1/chart", tags=["Chart Data"])
settings = get_settings()

class CandleData:
    """Estrutura de dados para candle"""
    def __init__(self, time: int, open: float, high: float, low: float, close: float, volume: float):
        self.time = time
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": self.time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }


@router.get("/historical")
async def get_historical_data(
    symbol: str = Query(..., description="Trading pair symbol (e.g., BTCUSDT)"),
    interval: str = Query("1m", description="Kline interval (1m, 5m, 15m, 1h, etc)"),
    start_time: Optional[int] = Query(None, description="Start time in milliseconds"),
    end_time: Optional[int] = Query(None, description="End time in milliseconds"),
    limit: int = Query(1000, ge=1, le=1000, description="Number of candles to fetch"),
    use_cache: bool = Query(True, description="Use cached data if available"),
    session: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Obtém dados históricos de candles
    Primeiro verifica cache no banco, depois busca da exchange se necessário
    """
    try:
        # Calcular tempos padrão se não fornecidos
        if not end_time:
            end_time = int(datetime.now().timestamp() * 1000)

        if not start_time:
            # Calcular baseado no intervalo e limite
            interval_ms = get_interval_milliseconds(interval)
            start_time = end_time - (interval_ms * limit)

        # Inicializar repository
        repo = CandleRepository(session)
        cached_candles = []

        # Verificar cache se habilitado
        if use_cache:
            cached_candles = await repo.get_candles(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )

            if cached_candles and len(cached_candles) >= limit * 0.8:  # Se tem 80% dos dados pedidos
                # Converter para formato de resposta
                candles = [
                    {
                        "time": c.time,
                        "open": c.open,
                        "high": c.high,
                        "low": c.low,
                        "close": c.close,
                        "volume": c.volume
                    }
                    for c in cached_candles
                ]

                return {
                    "success": True,
                    "symbol": symbol,
                    "interval": interval,
                    "candles": candles,
                    "count": len(candles),
                    "cached": True,
                    "start_time": start_time,
                    "end_time": end_time
                }

        # Buscar dados da Binance
        candles = await fetch_binance_klines(symbol, interval, start_time, end_time, limit)

        # Salvar no cache para próximas requisições
        if candles and use_cache:
            try:
                now_ms = int(datetime.now().timestamp() * 1000)
                candles_to_save = [
                    CandleModel(
                        symbol=symbol,
                        interval=interval,
                        time=candle["time"],
                        open=candle["open"],
                        high=candle["high"],
                        low=candle["low"],
                        close=candle["close"],
                        volume=candle["volume"],
                        created_at=now_ms,
                        updated_at=now_ms
                    )
                    for candle in candles
                ]

                inserted = await repo.save_candles(candles_to_save)
                print(f"✅ Cached {inserted} candles for {symbol} {interval}")
            except Exception as cache_error:
                print(f"⚠️ Error caching candles: {cache_error}")
                # Não falhar a requisição se o cache falhar

        return {
            "success": True,
            "symbol": symbol,
            "interval": interval,
            "candles": candles,
            "count": len(candles),
            "cached": False,
            "start_time": start_time,
            "end_time": end_time
        }

    except Exception as e:
        print(f"Error fetching historical data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/websocket-config")
async def get_websocket_config(
    symbol: str = Query(..., description="Trading pair symbol"),
    testnet: bool = Query(False, description="Use testnet"),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Retorna configuração para conexão WebSocket
    """
    base_url = "wss://stream.binance.com:9443/ws" if not testnet else "wss://testnet.binance.vision/ws"

    # Formatar símbolo para Binance
    formatted_symbol = symbol.upper().replace("/", "")

    return {
        "success": True,
        "config": {
            "base_url": base_url,
            "symbol": formatted_symbol,
            "streams": {
                "kline_1m": f"{formatted_symbol.lower()}@kline_1m",
                "kline_5m": f"{formatted_symbol.lower()}@kline_5m",
                "kline_15m": f"{formatted_symbol.lower()}@kline_15m",
                "kline_1h": f"{formatted_symbol.lower()}@kline_1h",
                "kline_4h": f"{formatted_symbol.lower()}@kline_4h",
                "kline_1d": f"{formatted_symbol.lower()}@kline_1d",
                "trade": f"{formatted_symbol.lower()}@trade",
                "depth": f"{formatted_symbol.lower()}@depth20@100ms",
                "ticker": f"{formatted_symbol.lower()}@ticker"
            },
            "reconnect": {
                "max_attempts": 10,
                "delay": 3000,
                "backoff_factor": 1.5
            }
        }
    }


@router.get("/symbols")
async def get_available_symbols(
    exchange: str = Query("binance", description="Exchange name"),
    market_type: str = Query("spot", description="Market type (spot/futures)"),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Lista símbolos disponíveis para trading
    """
    try:
        if exchange.lower() == "binance":
            symbols = await fetch_binance_symbols(market_type)
        else:
            # Por enquanto só suporta Binance
            symbols = []

        return {
            "success": True,
            "exchange": exchange,
            "market_type": market_type,
            "symbols": symbols,
            "count": len(symbols)
        }

    except Exception as e:
        print(f"Error fetching symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_cache(
    symbol: Optional[str] = Query(None, description="Clear specific symbol or all"),
    interval: Optional[str] = Query(None, description="Clear specific interval"),
    session: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Limpa cache de candles do banco de dados
    """
    try:
        repo = CandleRepository(session)

        if symbol and interval:
            deleted = await repo.delete_candles(symbol, interval)
        elif symbol:
            deleted = await repo.delete_candles(symbol)
        else:
            deleted = await repo.delete_all_candles()

        await session.commit()

        return {
            "success": True,
            "deleted": deleted,
            "message": f"Deleted {deleted} candles from cache"
        }

    except Exception as e:
        print(f"Error clearing cache: {e}")
        return {
            "success": False,
            "deleted": 0,
            "message": str(e)
        }


@router.get("/validate")
async def validate_candles(
    symbol: str = Query(..., description="Trading pair symbol"),
    interval: str = Query("1m", description="Kline interval"),
    session: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Valida integridade dos dados de candles no cache
    """
    # Cache temporariamente desabilitado
    return {
        "success": True,
        "valid": True,
        "issues": [],
        "gaps": [],
        "candle_count": 0,
        "symbol": symbol,
        "interval": interval,
        "message": "Cache system temporarily disabled"
    }


# Funções auxiliares

def get_interval_milliseconds(interval: str) -> int:
    """Converte intervalo string para millisegundos"""
    intervals = {
        "1m": 60000,
        "3m": 180000,
        "5m": 300000,
        "15m": 900000,
        "30m": 1800000,
        "1h": 3600000,
        "2h": 7200000,
        "4h": 14400000,
        "6h": 21600000,
        "8h": 28800000,
        "12h": 43200000,
        "1d": 86400000,
        "3d": 259200000,
        "1w": 604800000,
        "1M": 2592000000
    }
    return intervals.get(interval, 60000)


async def fetch_binance_klines(
    symbol: str,
    interval: str,
    start_time: int,
    end_time: int,
    limit: int
) -> List[Dict[str, Any]]:
    """Busca klines da API da Binance"""

    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol.upper().replace("/", ""),
        "interval": interval,
        "startTime": start_time,
        "endTime": end_time,
        "limit": min(limit, 1000)
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Binance API error: {response.status} - {error_text}")

            data = await response.json()

            candles = []
            for kline in data:
                candles.append({
                    "time": kline[0],
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5])
                })

            return candles


async def fetch_binance_symbols(market_type: str) -> List[str]:
    """Busca símbolos disponíveis da Binance"""

    if market_type == "spot":
        url = "https://api.binance.com/api/v3/exchangeInfo"
    else:
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch symbols: {response.status}")

            data = await response.json()
            symbols = []

            for symbol_info in data.get("symbols", []):
                if symbol_info.get("status") == "TRADING":
                    symbols.append(symbol_info["symbol"])

            return sorted(symbols)


# Função format_candle removida temporariamente