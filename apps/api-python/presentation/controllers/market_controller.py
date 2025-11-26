"""
Market Data Controller
Fornece dados de mercado (candles, ticker, orderbook) das exchanges
Usa API PÚBLICA da Binance para candles (não requer autenticação)
Suporta fetch paginado para histórico extenso (anos de dados)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import asyncpg
import logging
import aiohttp
import asyncio

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.exchanges.unified_exchange_connector import get_unified_connector
from infrastructure.cache.candles_cache import candles_cache

router = APIRouter(prefix="/api/v1/market", tags=["market"])
logger = logging.getLogger(__name__)

# Mapeamento de intervalo para milissegundos (para paginação)
INTERVAL_MS = {
    "1m": 60 * 1000,
    "3m": 3 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "2h": 2 * 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "6h": 6 * 60 * 60 * 1000,
    "8h": 8 * 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "3d": 3 * 24 * 60 * 60 * 1000,
    "1w": 7 * 24 * 60 * 60 * 1000,
    "1M": 30 * 24 * 60 * 60 * 1000,
}


async def fetch_binance_public_klines(
    symbol: str,
    interval: str,
    limit: int = 500,
    market_type: str = "futures",
    end_time: Optional[int] = None
) -> dict:
    """
    Busca candles da API PÚBLICA da Binance (sem autenticação)
    Suporta até 1000 candles por request
    Histórico disponível: anos de dados para timeframes maiores
    """
    # URLs da Binance API pública
    if market_type == "futures":
        url = "https://fapi.binance.com/fapi/v1/klines"
    else:
        url = "https://api.binance.com/api/v3/klines"

    params = {
        "symbol": symbol.upper().replace("/", ""),
        "interval": interval,
        "limit": min(limit, 1000)  # Binance max é 1000
    }

    # Adicionar endTime se fornecido (para paginação)
    if end_time:
        params["endTime"] = end_time

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    error_text = await response.text()
                    # Se futures falhar, tentar spot
                    if market_type == "futures" and "Invalid symbol" in error_text:
                        logger.info(f"Symbol {symbol} not found in futures, trying spot...")
                        return await fetch_binance_public_klines(symbol, interval, limit, "spot", end_time)
                    return {
                        "success": False,
                        "error": f"Binance API error: {response.status} - {error_text}",
                        "data": []
                    }

                data = await response.json()

                logger.info(f"✅ Fetched {len(data)} candles from Binance public API ({market_type})")

                return {
                    "success": True,
                    "data": data,
                    "market_type": market_type,
                    "source": "binance_public"
                }

    except Exception as e:
        logger.error(f"❌ Binance public API error: {e}")
        # Se futures falhar por outro motivo, tentar spot
        if market_type == "futures":
            logger.info("Trying spot market as fallback...")
            return await fetch_binance_public_klines(symbol, interval, limit, "spot", end_time)
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


async def fetch_binance_paginated_klines(
    symbol: str,
    interval: str,
    total_candles: int,
    market_type: str = "futures"
) -> dict:
    """
    Busca candles PAGINADOS da API PÚBLICA da Binance
    Faz múltiplas requests para obter histórico extenso (anos de dados)

    Args:
        symbol: Par de trading (ex: BTCUSDT)
        interval: Timeframe (1m, 1h, 1d, etc)
        total_candles: Quantidade total desejada (ex: 5000, 10000)
        market_type: futures ou spot

    Returns:
        Lista de candles ordenados do mais antigo ao mais recente
    """
    all_data = []
    remaining = total_candles
    end_time = None
    pages_fetched = 0
    max_pages = 20  # Limite de segurança para não fazer requests infinitos
    actual_market_type = market_type

    logger.info(f"📚 Starting paginated fetch: {symbol} {interval} - requesting {total_candles} candles")

    while remaining > 0 and pages_fetched < max_pages:
        # Buscar até 1000 candles por request
        batch_size = min(remaining, 1000)

        result = await fetch_binance_public_klines(
            symbol=symbol,
            interval=interval,
            limit=batch_size,
            market_type=actual_market_type if pages_fetched == 0 else result.get("market_type", actual_market_type),
            end_time=end_time
        )

        if not result["success"]:
            if pages_fetched == 0:
                # Se a primeira request falhar, retornar erro
                return result
            else:
                # Se já temos dados, retornar o que temos
                logger.warning(f"⚠️ Paginated fetch stopped at page {pages_fetched}: {result.get('error')}")
                break

        data = result["data"]
        if not data:
            logger.info(f"📭 No more data available at page {pages_fetched + 1}")
            break

        # Guardar o market_type detectado (pode ter sido fallback para spot)
        actual_market_type = result.get("market_type", actual_market_type)

        # Adicionar dados (no início, pois estamos indo para trás no tempo)
        all_data = data + all_data

        # Calcular o próximo endTime (1ms antes do candle mais antigo)
        oldest_candle_time = data[0][0]  # open_time do primeiro candle
        end_time = oldest_candle_time - 1

        remaining -= len(data)
        pages_fetched += 1

        logger.info(f"📖 Page {pages_fetched}: fetched {len(data)} candles, total so far: {len(all_data)}")

        # Se recebemos menos do que pedimos, chegamos ao fim do histórico
        if len(data) < batch_size:
            logger.info(f"📚 Reached end of available history")
            break

        # Pequeno delay entre requests para não sobrecarregar a API
        if remaining > 0:
            await asyncio.sleep(0.1)

    logger.info(f"✅ Paginated fetch complete: {len(all_data)} candles in {pages_fetched} pages")

    return {
        "success": True,
        "data": all_data,
        "market_type": actual_market_type,
        "source": "binance_public_paginated",
        "pages_fetched": pages_fetched
    }


@router.get("/candles")
async def get_candles(
    symbol: str = Query(..., description="Symbol (ex: BTCUSDT)"),
    interval: str = Query("1h", description="Interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)"),
    limit: int = Query(5000, ge=1, le=20000, description="Number of candles (max 20000 via pagination)"),
    market_type: Optional[str] = Query("auto", description="Market type: auto, spot, futures")
):
    """
    Busca dados históricos de candles (OHLCV) da API PÚBLICA da Binance
    NÃO REQUER autenticação - usa dados públicos de mercado
    SUPORTA PAGINAÇÃO para histórico extenso (anos de dados)

    **Histórico Disponível (com paginação):**
    - 30m com 5000 candles: ~104 dias
    - 1h com 5000 candles: ~208 dias
    - 4h com 5000 candles: ~833 dias (~2.3 anos)
    - 1d com 5000 candles: ~13.7 anos (todo histórico BTC)

    **Parâmetros:**
    - symbol: Par de negociação (ex: BTCUSDT, ETHUSDT)
    - interval: Timeframe (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
    - limit: Quantidade de candles (max 20000 - usa paginação automática)
    - market_type: Tipo de mercado (auto, spot, futures) - auto tenta futures primeiro

    **Retorna:**
    ```json
    {
      "success": true,
      "symbol": "BTCUSDT",
      "interval": "1h",
      "market_type": "futures",
      "source": "binance_public_paginated",
      "count": 5000,
      "candles": [...]
    }
    ```
    """

    try:
        # 🚀 PERFORMANCE: Check cache first
        cached_data = await candles_cache.get(symbol, interval, limit)
        if cached_data:
            logger.info(f"📊 Returning CACHED candles for {symbol} {interval} (limit={limit})")
            return cached_data

        logger.info(f"📥 Cache miss - fetching from Binance PUBLIC API: {symbol} {interval} (limit={limit})")

        # Determinar tipo de mercado inicial
        initial_market = "futures" if market_type in ["auto", "futures"] else "spot"

        # 🌐 USAR API PÚBLICA DA BINANCE (sem autenticação)
        # Se limit > 1000, usar fetch paginado
        if limit > 1000:
            logger.info(f"📚 Using PAGINATED fetch for {limit} candles")
            candles_result = await fetch_binance_paginated_klines(
                symbol=symbol,
                interval=interval,
                total_candles=limit,
                market_type=initial_market
            )
        else:
            candles_result = await fetch_binance_public_klines(
                symbol=symbol,
                interval=interval,
                limit=limit,
                market_type=initial_market
            )

        if not candles_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch candles: {candles_result.get('error', 'Unknown error')}"
            )

        # Formatar dados para o frontend
        # Binance retorna: [open_time, open, high, low, close, volume, close_time, ...]
        candles = []
        for kline in candles_result["data"]:
            candles.append({
                "time": int(kline[0] / 1000),  # Converter de ms para seconds
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5])
            })

        result = {
            "success": True,
            "symbol": symbol,
            "interval": interval,
            "market_type": candles_result.get("market_type", initial_market),
            "source": candles_result.get("source", "binance_public"),
            "count": len(candles),
            "candles": candles
        }

        # 🚀 PERFORMANCE: Cache the result
        await candles_cache.set(symbol, interval, limit, result)
        logger.info(f"💾 Cached {len(candles)} candles for {symbol} {interval} from Binance public API")

        return result

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching candles: {str(e)}"
        )


@router.get("/candles/history")
async def get_candles_history(
    symbol: str = Query(..., description="Symbol (ex: BTCUSDT)"),
    interval: str = Query("1h", description="Interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, etc)"),
    end_time: int = Query(..., description="End time in milliseconds (fetch candles BEFORE this time)"),
    limit: int = Query(1000, ge=1, le=1000, description="Number of candles (max 1000)"),
    market_type: Optional[str] = Query("auto", description="Market type: auto, spot, futures")
):
    """
    Busca candles HISTÓRICOS (para lazy loading / infinite scroll)
    Retorna candles ANTES do endTime especificado

    **Uso típico:**
    1. Frontend carrega candles iniciais com /candles
    2. Quando usuário scrolla para a esquerda (passado), chama /candles/history
       com endTime = timestamp do candle mais antigo atual
    3. Repete até não haver mais dados

    **Parâmetros:**
    - symbol: Par de trading (ex: BTCUSDT)
    - interval: Timeframe
    - end_time: Timestamp em MS - busca candles ANTES deste momento
    - limit: Quantidade (max 1000)

    **Retorna:**
    - candles: Array ordenado do mais antigo ao mais recente
    - has_more: Boolean indicando se há mais dados históricos
    - oldest_time: Timestamp do candle mais antigo retornado
    """
    try:
        logger.info(f"📜 Fetching historical candles: {symbol} {interval} before {end_time} (limit={limit})")

        # Determinar tipo de mercado inicial
        initial_market = "futures" if market_type in ["auto", "futures"] else "spot"

        # Buscar candles com endTime
        result = await fetch_binance_public_klines(
            symbol=symbol,
            interval=interval,
            limit=limit,
            market_type=initial_market,
            end_time=end_time
        )

        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch historical candles: {result.get('error', 'Unknown error')}"
            )

        # Formatar dados
        candles = []
        for kline in result["data"]:
            candles.append({
                "time": int(kline[0] / 1000),  # MS para seconds
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5])
            })

        # Verificar se há mais dados (se retornou menos que o pedido, não há mais)
        has_more = len(result["data"]) >= limit
        oldest_time = candles[0]["time"] * 1000 if candles else None

        logger.info(f"✅ Historical candles: {len(candles)} fetched, has_more={has_more}")

        return {
            "success": True,
            "symbol": symbol,
            "interval": interval,
            "market_type": result.get("market_type", initial_market),
            "count": len(candles),
            "has_more": has_more,
            "oldest_time": oldest_time,
            "candles": candles
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching historical candles: {str(e)}"
        )


@router.get("/cache/metrics")
async def get_cache_metrics():
    """
    Get candles cache metrics
    """
    metrics = candles_cache.get_metrics()
    return {
        "success": True,
        "data": metrics
    }


@router.post("/cache/invalidate")
async def invalidate_cache(symbol: Optional[str] = Query(None, description="Symbol to invalidate (optional)")):
    """
    Invalidate candles cache
    """
    count = await candles_cache.invalidate(symbol)
    return {
        "success": True,
        "data": {
            "invalidated_entries": count,
            "symbol": symbol or "all"
        }
    }


@router.get("/validate-symbol")
async def validate_symbol(
    symbol: str = Query(..., description="Symbol to validate (ex: BTCUSDT)"),
    exchange_account_id: Optional[str] = Query(None, description="Exchange account ID (optional)")
):
    """
    Valida se um símbolo tem dados de candles disponíveis na exchange

    **Retorna:**
    ```json
    {
      "success": true,
      "symbol": "BTCUSDT",
      "valid": true,
      "message": "Symbol has candle data available"
    }
    ```
    """
    try:
        # Buscar conta
        if not exchange_account_id:
            account_query = """
                SELECT id, api_key, secret_key, testnet
                FROM exchange_accounts
                WHERE testnet = false AND is_active = true AND is_main = true
                LIMIT 1
            """
            account = await transaction_db.fetchrow(account_query)
        else:
            account_query = """
                SELECT id, api_key, secret_key, testnet
                FROM exchange_accounts
                WHERE id = $1 AND is_active = true
            """
            account = await transaction_db.fetchrow(account_query, exchange_account_id)

        if not account:
            raise HTTPException(status_code=404, detail="Exchange account not found")

        # Conectar com Binance
        connector = BinanceConnector(
            api_key=account["api_key"],
            api_secret=account["secret_key"],
            testnet=account["testnet"]
        )

        # Tentar buscar apenas 1 candle para validar
        candles_result = await connector.get_klines(
            symbol=symbol,
            interval="1h",
            limit=1
        )

        if candles_result["success"]:
            return {
                "success": True,
                "symbol": symbol,
                "valid": True,
                "message": "Symbol has candle data available"
            }
        else:
            error_msg = candles_result.get("error", "Unknown error")
            # Verificar se é erro de símbolo inválido
            if "Invalid symbol" in error_msg or "-1121" in error_msg:
                return {
                    "success": True,
                    "symbol": symbol,
                    "valid": False,
                    "message": "Symbol does not have candle data available"
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error validating symbol: {error_msg}"
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating symbol: {str(e)}"
        )


@router.get("/ticker")
async def get_ticker(
    symbol: str = Query(..., description="Symbol (ex: BTCUSDT)"),
    exchange_account_id: Optional[str] = Query(None, description="Exchange account ID (optional)")
):
    """
    Busca ticker 24h do símbolo (preço atual, volume, mudança %)
    """

    try:
        # Buscar conta
        if not exchange_account_id:
            account_query = """
                SELECT id, api_key, secret_key, testnet
                FROM exchange_accounts
                WHERE testnet = false AND is_active = true AND is_main = true
                LIMIT 1
            """
            account = await transaction_db.fetchrow(account_query)
        else:
            account_query = """
                SELECT id, api_key, secret_key, testnet
                FROM exchange_accounts
                WHERE id = $1 AND is_active = true
            """
            account = await transaction_db.fetchrow(account_query, exchange_account_id)

        if not account:
            raise HTTPException(status_code=404, detail="Exchange account not found")

        # Conectar com Binance
        connector = BinanceConnector(
            api_key=account["api_key"],
            api_secret=account["secret_key"],
            testnet=account["testnet"]
        )

        # Buscar ticker
        ticker_result = await connector.get_ticker_24h(symbol=symbol)

        if not ticker_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch ticker: {ticker_result.get('error', 'Unknown error')}"
            )

        ticker = ticker_result["data"]

        return {
            "success": True,
            "symbol": symbol,
            "price": float(ticker.get("lastPrice", 0)),
            "priceChange": float(ticker.get("priceChange", 0)),
            "priceChangePercent": float(ticker.get("priceChangePercent", 0)),
            "high": float(ticker.get("highPrice", 0)),
            "low": float(ticker.get("lowPrice", 0)),
            "volume": float(ticker.get("volume", 0)),
            "quoteVolume": float(ticker.get("quoteVolume", 0))
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching ticker: {str(e)}"
        )