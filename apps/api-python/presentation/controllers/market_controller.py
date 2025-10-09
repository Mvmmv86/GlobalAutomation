"""
Market Data Controller
Fornece dados de mercado (candles, ticker, orderbook) das exchanges
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import asyncpg
import logging

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.exchanges.unified_exchange_connector import get_unified_connector
from infrastructure.cache.candles_cache import candles_cache

router = APIRouter(prefix="/api/v1/market", tags=["market"])
logger = logging.getLogger(__name__)


@router.get("/candles")
async def get_candles(
    symbol: str = Query(..., description="Symbol (ex: BTCUSDT)"),
    interval: str = Query("1h", description="Interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)"),
    limit: int = Query(500, ge=1, le=1000, description="Number of candles to fetch"),
    exchange_account_id: Optional[str] = Query(None, description="Exchange account ID (optional)"),
    market_type: Optional[str] = Query("auto", description="Market type: auto, spot, futures")
):
    """
    Busca dados históricos de candles (OHLCV) com auto-detecção SPOT/FUTURES

    **Parâmetros:**
    - symbol: Par de negociação (ex: BTCUSDT, ETHUSDT)
    - interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, etc)
    - limit: Quantidade de candles (max 1000)
    - exchange_account_id: ID da conta (opcional, usa conta principal se não fornecido)
    - market_type: Tipo de mercado (auto, spot, futures) - auto detecta automaticamente

    **Retorna:**
    ```json
    {
      "success": true,
      "symbol": "BTCUSDT",
      "interval": "1h",
      "market_type": "futures",
      "count": 500,
      "candles": [
        {
          "time": 1234567890,
          "open": 109000.50,
          "high": 109500.00,
          "low": 108500.00,
          "close": 109200.00,
          "volume": 1234.567
        },
        ...
      ]
    }
    ```
    """

    try:
        # 🚀 PERFORMANCE: Check cache first
        cached_data = await candles_cache.get(symbol, interval, limit)
        if cached_data:
            logger.info(f"📊 Returning CACHED candles for {symbol} {interval}")
            return cached_data

        logger.info(f"📥 Cache miss - fetching fresh candles for {symbol} {interval}")

        # Buscar credenciais da exchange e informações da posição
        if not exchange_account_id:
            account_query = """
                SELECT ea.id, ea.api_key, ea.secret_key, ea.testnet, ea.exchange
                FROM exchange_accounts ea
                WHERE ea.testnet = false
                  AND ea.is_active = true
                  AND ea.is_main = true
                LIMIT 1
            """
            account = await transaction_db.fetchrow(account_query)
        else:
            account_query = """
                SELECT ea.id, ea.api_key, ea.secret_key, ea.testnet, ea.exchange
                FROM exchange_accounts ea
                WHERE ea.id = $1 AND ea.is_active = true
            """
            account = await transaction_db.fetchrow(account_query, exchange_account_id)

        if not account:
            raise HTTPException(
                status_code=404,
                detail="Exchange account not found or inactive"
            )

        # Detectar tipo de mercado automaticamente baseado em posições abertas
        operation_type = 'futures'  # default para tentar futures primeiro
        auto_detect = market_type == 'auto'

        if not auto_detect:
            # Usar tipo fornecido pelo usuário
            operation_type = 'futures' if market_type == 'futures' else 'spot'
            print(f"🔧 Manual market type selected: {operation_type}")
        else:
            # Auto-detecção: Tenta FUTURES primeiro, depois SPOT no fallback automático
            print(f"🔍 Auto-detect enabled - will try FUTURES first, then SPOT")

        # Criar connector unificado (com auto-detecção SPOT/FUTURES)
        connector = await get_unified_connector(
            exchange=account["exchange"] or "binance",
            api_key=account["api_key"],
            api_secret=account["secret_key"],
            testnet=account["testnet"],
            operation_type=operation_type
        )

        try:
            # Buscar candles usando connector unificado
            candles_result = await connector.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit,
                auto_detect_market=auto_detect  # Tenta FUTURES e SPOT automaticamente
            )

            if not candles_result["success"]:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to fetch candles: {candles_result.get('error', 'Unknown error')}"
                )

            # Formatar dados para o frontend
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
                "market_type": candles_result.get("market_type", operation_type),
                "source": candles_result.get("source", "unknown"),
                "count": len(candles),
                "candles": candles
            }

            # 🚀 PERFORMANCE: Cache the result
            await candles_cache.set(symbol, interval, limit, result)
            logger.info(f"💾 Cached {len(candles)} candles for {symbol} {interval}")

            return result

        finally:
            # Fechar connector
            await connector.close()

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching candles: {str(e)}"
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