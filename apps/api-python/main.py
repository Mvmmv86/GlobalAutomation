"""FastAPI main application - Entry point"""

import structlog
import json
from datetime import datetime, date, timedelta
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from presentation.controllers.webhook_controller import create_webhook_router
from presentation.controllers.health_controller import create_health_router
from presentation.controllers.dashboard_controller import create_dashboard_router
from presentation.controllers.positions_controller import create_positions_router
from presentation.controllers.dashboard_cards_controller import create_dashboard_cards_router
from presentation.controllers.sync_controller import create_sync_router
from presentation.controllers.exchange_account_controller import create_exchange_account_router
from infrastructure.background.sync_scheduler import sync_scheduler
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.exchanges.bybit_connector import BybitConnector
from infrastructure.security.encryption_service import EncryptionService
from infrastructure.pricing.binance_price_service import BinancePriceService

# from presentation.controllers.auth_controller import create_auth_router  # Removido - problema DI
from infrastructure.config.settings import get_settings
from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.services.order_processor import order_processor
from infrastructure.di import cleanup_container


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    settings = get_settings()

    # Startup
    logger.info("Starting TradingView Gateway API", version=settings.version)

    try:
        # Initialize database with asyncpg (pgBouncer transaction mode)
        await transaction_db.connect()
        logger.info("Database connected successfully (pgBouncer transaction mode)")

        # Initialize Redis (temporarily disabled for integration testing)
        # await redis_manager.connect()
        logger.info("Redis connection skipped for integration testing")

        # Start background sync scheduler
        logger.info("🚀 Starting background sync scheduler with real prices (30s interval)")
        await sync_scheduler.start()  # Habilitado para dados em tempo real

        yield

    finally:
        # Shutdown
        logger.info("Shutting down TradingView Gateway API")

        # Stop background sync scheduler
        logger.info("🛑 Stopping background sync scheduler")
        await sync_scheduler.stop()

        # Close connections
        await transaction_db.disconnect()
        # await redis_manager.disconnect()

        # Cleanup DI container
        await cleanup_container()

        logger.info("Shutdown completed")


def create_app() -> FastAPI:
    """Create FastAPI application with all configurations"""
    settings = get_settings()

    # Create FastAPI app
    app = FastAPI(
        title="TradingView Gateway API",
        description="Python FastAPI backend for TradingView webhook processing",
        version=settings.version,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # Add rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Security middleware
    if settings.environment == "production":
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests"""
        start_time = structlog.get_logger().info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_ip=get_remote_address(request),
        )

        # Special logging for exchange-accounts POST requests
        if request.method == "POST" and "exchange-accounts" in request.url.path:
            try:
                # Read body for debugging (this consumes the body once)
                body = await request.body()
                logger.info("🚨 EXCHANGE ACCOUNT POST REQUEST",
                           body_length=len(body),
                           content_type=request.headers.get("content-type"),
                           headers=dict(request.headers))

                # We need to reconstruct the request with the body
                from fastapi import Request as FastAPIRequest
                from starlette.requests import Request as StarletteRequest

                # Create a new request with the same body
                scope = request.scope.copy()
                receive = request.receive.__class__(lambda: {"type": "http.request", "body": body})

                # Create new request
                new_request = StarletteRequest(scope, receive)
                request._body = body  # Cache the body for later use

            except Exception as e:
                logger.error("Error reading POST body", error=str(e))

        try:
            response = await call_next(request)

            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                client_ip=get_remote_address(request),
            )

            return response

        except Exception as e:
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                client_ip=get_remote_address(request),
                error=str(e),
            )
            raise

    # Error handlers
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle ValueError exceptions"""
        logger.warning("ValueError occurred", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=400, content={"error": "Bad Request", "detail": str(exc)}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions"""
        logger.error(
            "Unhandled exception occurred",
            error=str(exc),
            path=request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred"
                if settings.environment == "production"
                else str(exc),
            },
        )

    # Include routers with /api/v1 prefix
    # Routers will use dependency injection via FastAPI Depends
    # auth_router = create_auth_router()  # Comentado temporariamente - problema na DI
    # webhook_router = create_webhook_router()  # Comentado temporariamente para usar asyncpg
    health_router = create_health_router()
    dashboard_router = create_dashboard_router()
    positions_router = create_positions_router()
    dashboard_cards_router = create_dashboard_cards_router()
    sync_router = create_sync_router()

    # app.include_router(auth_router, prefix="/api/v1")  # Comentado temporariamente
    # app.include_router(webhook_router, prefix="/api/v1")  # Comentado temporariamente
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(dashboard_router)
    app.include_router(positions_router)
    app.include_router(dashboard_cards_router)
    app.include_router(sync_router)
    app.include_router(create_exchange_account_router())


    return app


# Create app instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint"""
    settings = get_settings()
    return {
        "service": "TradingView Gateway API",
        "version": settings.version,
        "environment": settings.environment,
        "status": "healthy",
        "database": "asyncpg (pgBouncer transaction mode)",
    }


# Webhook endpoint para teste com asyncpg
@app.post("/api/v1/webhooks/tv/test-webhook")
async def test_webhook(request: Request):
    """Test webhook endpoint using asyncpg"""
    try:
        body = await request.body()
        payload = json.loads(body.decode("utf-8"))

        # Log básico
        logger.info(f"Webhook received: {payload.get('ticker', 'unknown')}")

        # Detectar tipo de payload
        is_complete = "position" in payload and "risk_management" in payload

        return {
            "success": True,
            "message": "Webhook processed successfully",
            "payload_type": "complete" if is_complete else "simple",
            "ticker": payload.get("ticker"),
            "action": payload.get("action"),
            "database": "asyncpg transaction mode",
        }
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# Webhook endpoint para TradingView real
@app.post("/api/v1/webhooks/tradingview")
async def tradingview_webhook(request: Request):
    """Real TradingView webhook endpoint"""
    try:
        body = await request.body()
        body_str = body.decode("utf-8")

        # TradingView pode enviar JSON ou texto plano
        try:
            payload = json.loads(body_str)
            logger.info(f"📊 TradingView JSON webhook: {payload}")
        except:
            # Se não for JSON, é texto plano
            logger.info(f"📊 TradingView text webhook: {body_str}")
            payload = {"message": body_str}

        # Processar o webhook
        print("\n" + "=" * 60)
        print("🚨 WEBHOOK RECEBIDO DO TRADINGVIEW!")
        print(f"📅 Time: {datetime.utcnow().isoformat()}")
        print(f"📦 Payload: {payload}")
        print("=" * 60 + "\n")

        # Salvar em arquivo para debug
        with open("tradingview_webhooks.log", "a") as f:
            f.write(f"\n{datetime.utcnow().isoformat()} - {json.dumps(payload)}\n")

        # 🎯 PROCESSAR ORDEM REAL
        print("⚙️ Processando ordem na exchange...")
        order_result = await order_processor.process_tradingview_webhook(payload)

        if order_result["success"]:
            print(f"✅ Ordem criada: ID {order_result['order_id']}")
            print(f"🏭 Exchange Order: {order_result.get('exchange_order_id', 'N/A')}")
            print(f"📊 Status: {order_result.get('status', 'unknown')}")
        else:
            print(f"❌ Erro na ordem: {order_result.get('error', 'Unknown error')}")

        return {
            "success": True,
            "message": "TradingView webhook received and processed",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
            "order_result": order_result,
        }

    except Exception as e:
        logger.error(f"TradingView webhook error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# Função helper reutilizada do sync controller
async def get_exchange_connector(account_id: str):
    """Get exchange connector for account - reutilizada do sync controller"""
    try:
        encryption_service = EncryptionService()

        # Get account from database
        account = await transaction_db.fetchrow("""
            SELECT id, name, exchange, api_key, secret_key, passphrase, testnet, is_active
            FROM exchange_accounts
            WHERE id = $1 AND is_active = true
        """, account_id)

        if not account:
            raise HTTPException(status_code=404, detail=f"Exchange account {account_id} not found or inactive")

        # Decrypt API credentials - FASE 1: Fallback para env vars se descriptografia falhar
        try:
            api_key = encryption_service.decrypt_string(account['api_key']) if account['api_key'] else None
            secret_key = encryption_service.decrypt_string(account['secret_key']) if account['secret_key'] else None
            passphrase = encryption_service.decrypt_string(account['passphrase']) if account['passphrase'] else None
        except Exception as decrypt_error:
            print(f"⚠️ Erro na descriptografia, usando fallback: {decrypt_error}")
            # Fallback para variáveis de ambiente (igual dashboard)
            import os
            api_key = account['api_key'] or os.getenv('BINANCE_API_KEY')
            secret_key = account['secret_key'] or os.getenv('BINANCE_SECRET_KEY') or os.getenv('BINANCE_API_SECRET')
            passphrase = account['passphrase']

        # Create appropriate connector
        exchange = account['exchange'].lower()
        testnet = account['testnet']

        if exchange == 'binance':
            return BinanceConnector(api_key, secret_key, testnet)
        elif exchange == 'bybit':
            return BybitConnector(api_key, secret_key, testnet)
        else:
            raise HTTPException(status_code=400, detail=f"Exchange {exchange} not supported")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exchange connector: {e}")
        raise HTTPException(status_code=500, detail="Failed to get exchange connector")

# 🎯 SISTEMA HÍBRIDO: Função para buscar TODOS os símbolos relevantes
async def get_all_relevant_symbols(exchange_account_id: str) -> list:
    """
    Estratégia híbrida para garantir cobertura completa de símbolos:
    1. Símbolos que já temos ordens no banco (histórico)
    2. Top símbolos populares da Binance
    3. Combinar sem duplicatas
    """
    try:
        print("🔍 Iniciando busca híbrida de símbolos...")

        # 1. SÍMBOLOS HISTÓRICOS: Buscar da nossa base de dados
        existing_symbols_rows = await transaction_db.fetch("""
            SELECT DISTINCT symbol
            FROM trading_orders
            WHERE symbol IS NOT NULL
              AND symbol != ''
              AND created_at >= NOW() - INTERVAL '3 months'
            ORDER BY symbol
        """)

        existing_symbols = [row['symbol'] for row in existing_symbols_rows]
        print(f"📚 Símbolos históricos encontrados: {len(existing_symbols)} - {existing_symbols[:10]}...")

        # 2. SÍMBOLOS POPULARES: Lista curada dos principais pares
        popular_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'LINKUSDT', 'DOTUSDT', 'AVAXUSDT',
            'XRPUSDT', 'LTCUSDT', 'MATICUSDT', 'ATOMUSDT', 'ALGOUSDT', 'VETUSDT', 'XLMUSDT', 'TRXUSDT',
            'EOSUSDT', 'IOTAUSDT', 'NEOUSDT', 'DASHUSDT', 'ETCUSDT', 'XMRUSDT', 'ZECUSDT', 'COMPUSDT',
            'FILUSDT', 'UNIUSDT', 'AAVEUSDT', 'SUSHIUSDT', 'CHZUSDT', 'MANAUSDT', 'SANDUSDT', 'ENJUSDT',
            'GRTUSDT', 'BALUSDT', 'CRVUSDT', 'RNDRUSDT', 'NEARUSDT', 'FTMUSDT', 'APEUSDT', 'GALAUSDT'
        ]
        print(f"⭐ Símbolos populares: {len(popular_symbols)}")

        # 3. COMBINAR SEM DUPLICATAS: Histórico tem prioridade
        all_symbols = list(dict.fromkeys(existing_symbols + popular_symbols))

        print(f"🎯 TOTAL DE SÍMBOLOS: {len(all_symbols)} (histórico: {len(existing_symbols)}, populares: {len(popular_symbols)})")

        return all_symbols

    except Exception as e:
        print(f"❌ Erro na busca híbrida de símbolos: {e}")
        # Fallback para símbolos populares
        fallback_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'LINKUSDT', 'DOTUSDT', 'AVAXUSDT',
            'XRPUSDT', 'LTCUSDT', 'MATICUSDT', 'ATOMUSDT', 'ALGOUSDT', 'VETUSDT', 'XLMUSDT', 'TRXUSDT'
        ]
        print(f"🔄 Usando fallback com {len(fallback_symbols)} símbolos populares")
        return fallback_symbols


# 📊 ENDPOINTS PARA FRONTEND - VISUALIZAÇÃO DE ORDENS
@app.get("/api/v1/orders")
async def get_orders(
    limit: int = Query(default=50, description="Limite de ordens a retornar"),
    exchange_account_id: str = Query(default=None, description="ID da conta de exchange"),
    date_from: str = Query(default=None, description="Data inicial (YYYY-MM-DD)"),
    date_to: str = Query(default=None, description="Data final (YYYY-MM-DD)")
):
    """Lista ordens com filtros para o frontend - FASE 1: Dados diretos da Binance"""
    try:
        print(f"🔍 FASE 1: Buscando ordens direto da Binance API")
        print(f"🔍 Filtros: account_id={exchange_account_id}, date_from={date_from}, date_to={date_to}, limit={limit}")

        # FASE 1: Se não especificar conta, usar conta principal
        if not exchange_account_id or exchange_account_id == 'all':
            # Buscar conta principal (comportamento atual)
            main_account = await transaction_db.fetchrow("""
                SELECT id FROM exchange_accounts
                WHERE testnet = false AND is_active = true
                ORDER BY created_at ASC
                LIMIT 1
            """)

            if not main_account:
                return {"success": False, "error": "Nenhuma conta principal encontrada", "data": []}

            account_id_to_use = main_account['id']
        else:
            account_id_to_use = exchange_account_id

        print(f"🏦 Usando conta: {account_id_to_use}")

        # Buscar ordens direto da Binance via connector
        connector = await get_exchange_connector(account_id_to_use)

        # Configurar filtros de tempo - PADRÃO: Últimos 3 meses se não especificado
        start_time = None
        end_time = None

        if date_from:
            try:
                start_time = int(datetime.strptime(date_from, '%Y-%m-%d').timestamp() * 1000)
            except ValueError as e:
                print(f"❌ Erro ao converter date_from: {e}")

        if date_to:
            try:
                # Adicionar 23:59:59 ao date_to
                end_time = int((datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)).timestamp() * 1000)
            except ValueError as e:
                print(f"❌ Erro ao converter date_to: {e}")

        # Se não especificado, buscar apenas últimos 3 meses (mais eficiente)
        if not date_from and not date_to:
            # Últimos 90 dias (3 meses)
            three_months_ago = datetime.now() - timedelta(days=90)
            start_time = int(three_months_ago.timestamp() * 1000)
            print(f"🗓️ Aplicando filtro padrão: últimos 3 meses (desde {three_months_ago.strftime('%Y-%m-%d')})")

        # SISTEMA HÍBRIDO: Buscar símbolos dinamicamente para MÁXIMA cobertura
        all_symbols = await get_all_relevant_symbols(exchange_account_id)
        print(f"🎯 Sistema Híbrido: {len(all_symbols)} símbolos identificados para busca completa")
        all_raw_orders = []

        for symbol in all_symbols:
            try:
                print(f"🔍 Buscando ordens SPOT + FUTURES para {symbol}...")

                # 1. BUSCAR ORDENS SPOT
                spot_result = await connector.get_account_orders(
                    symbol=symbol,
                    limit=100,  # Limite alto para pegar histórico completo
                    start_time=start_time,
                    end_time=end_time
                )

                spot_orders = []
                if spot_result.get('success', True):
                    spot_orders = spot_result.get('orders', [])
                    # Marcar como SPOT
                    for order in spot_orders:
                        order['_market_type'] = 'SPOT'
                    all_raw_orders.extend(spot_orders)

                # 2. BUSCAR ORDENS FUTURES
                # IMPORTANTE: Binance Futures tem limitação de 7 dias sem start_time
                # e 90 dias com start_time. Buscar últimos 7 dias apenas
                futures_result = await connector.get_futures_orders(
                    symbol=symbol,
                    limit=100,  # Limite alto para pegar histórico completo
                    start_time=None,  # None = últimos 7 dias (padrão Binance)
                    end_time=None
                )

                futures_orders = []
                if futures_result.get('success', True):
                    futures_orders = futures_result.get('orders', [])
                    # Marcar como FUTURES
                    for order in futures_orders:
                        order['_market_type'] = 'FUTURES'
                    all_raw_orders.extend(futures_orders)

                total_orders = len(spot_orders) + len(futures_orders)
                print(f"✅ {symbol}: {len(spot_orders)} SPOT + {len(futures_orders)} FUTURES = {total_orders} ordens")

            except Exception as e:
                print(f"❌ Erro ao buscar {symbol}: {e}")
                continue

        # Ordenar por data (mais recentes primeiro) - CRUCIAL para mostrar ordens atuais
        all_raw_orders.sort(key=lambda x: int(x.get('updateTime', x.get('time', 0))), reverse=True)

        # FASE 1: Aplicar limite inteligente - se muito dados, pegar só os mais recentes
        if len(all_raw_orders) > limit and limit < 1000:
            raw_orders = all_raw_orders[:limit]
            print(f"⚡ Aplicando limite de {limit} ordens (das {len(all_raw_orders)} encontradas)")
        else:
            raw_orders = all_raw_orders
            print(f"📋 Retornando todas as {len(all_raw_orders)} ordens encontradas")

        # Contar SPOT vs FUTURES
        spot_count = len([o for o in raw_orders if o.get('_market_type') == 'SPOT'])
        futures_count = len([o for o in raw_orders if o.get('_market_type') == 'FUTURES'])

        print(f"📊 Total de ordens coletadas: {len(raw_orders)} ({spot_count} SPOT + {futures_count} FUTURES)")

        # FASE 1: Converter dados da Binance para formato da nossa tabela
        orders_list = []
        for order in raw_orders:
            try:
                # Mapear campos da Binance para nosso formato
                order_data = {
                    "id": str(order.get('orderId', order.get('id', ''))),
                    "symbol": order.get('symbol', ''),
                    "side": order.get('side', '').lower(),
                    "order_type": order.get('type', 'market').lower(),
                    "quantity": float(order.get('origQty', order.get('executedQty', 0))),
                    "price": float(order.get('price', 0)) if order.get('price') else None,
                    "status": order.get('status', 'unknown').lower(),
                    "exchange": "binance",  # FASE 1: Hardcoded
                    "exchange_order_id": str(order.get('orderId', order.get('id', ''))),
                    "filled_quantity": float(order.get('executedQty', 0)),
                    "average_price": float(order.get('avgPrice', order.get('price', 0))) if order.get('avgPrice', order.get('price')) else None,
                    "created_at": datetime.fromtimestamp(int(order.get('time', 0)) / 1000).isoformat() if order.get('time') else None,
                    "updated_at": datetime.fromtimestamp(int(order.get('updateTime', order.get('time', 0))) / 1000).isoformat() if order.get('updateTime', order.get('time')) else None,

                    # FASE 2: Campos completos - SPOT/FUTURES baseado no mercado
                    "operation_type": order.get('_market_type', 'SPOT').lower(),  # SPOT ou FUTURES
                    "entry_exit": "entrada" if order.get('side', '').lower() == 'buy' else "saida",
                    "margin_usdt": float(order.get('cummulativeQuoteQty', 0)) if order.get('cummulativeQuoteQty') else (float(order.get('origQty', 0)) * float(order.get('price', 0)) if order.get('price') else 0),
                    "profit_loss": 0.0,  # FASE 2: Será calculado abaixo para operações SPOT + FUTURES

                    # ORDEM ID para agrupar operações relacionadas
                    "order_id": None  # Será calculado depois do processamento de P&L
                }

                orders_list.append(order_data)

            except (ValueError, TypeError) as e:
                print(f"❌ Erro ao processar ordem {order.get('orderId', 'N/A')}: {e}")
                continue

        # FASE 2: CALCULAR P&L PARA OPERAÇÕES SPOT + FUTURES USANDO LÓGICA SIMPLIFICADA
        print(f"🧮 FASE 2: Calculando P&L individual para operações SPOT + FUTURES...")

        try:
            # Agrupar ordens SPOT E FUTURES por ativo para calcular preço médio
            spot_orders = [o for o in orders_list if o.get('operation_type') == 'spot']
            futures_orders = [o for o in orders_list if o.get('operation_type') == 'futures']

            # Agrupar SPOT
            spot_orders_by_asset = {}
            for order in spot_orders:
                symbol = order.get('symbol', '')
                if symbol.endswith('USDT'):
                    asset = symbol[:-4]
                else:
                    asset = symbol.split('USDT')[0] if 'USDT' in symbol else symbol

                if asset not in spot_orders_by_asset:
                    spot_orders_by_asset[asset] = []
                spot_orders_by_asset[asset].append(order)

            # Agrupar FUTURES
            futures_orders_by_asset = {}
            for order in futures_orders:
                symbol = order.get('symbol', '')
                if symbol.endswith('USDT'):
                    asset = symbol[:-4]
                else:
                    asset = symbol.split('USDT')[0] if 'USDT' in symbol else symbol

                if asset not in futures_orders_by_asset:
                    futures_orders_by_asset[asset] = []
                futures_orders_by_asset[asset].append(order)

            print(f"📊 SPOT P&L: Processando {len(spot_orders)} ordens SPOT para {len(spot_orders_by_asset)} ativos")
            print(f"📊 FUTURES P&L: Processando {len(futures_orders)} ordens FUTURES para {len(futures_orders_by_asset)} ativos")

            # CALCULAR P&L PARA ORDENS SPOT
            for asset, asset_orders in spot_orders_by_asset.items():
                try:
                    # FASE 2: Implementação simplificada - calcular preço médio de compra
                    total_quantity = 0.0
                    total_cost = 0.0

                    # Coletar apenas ordens de compra (BUY) para calcular preço médio
                    buy_orders = [o for o in asset_orders if o.get('side') == 'buy' and o.get('filled_quantity', 0) > 0]

                    for buy_order in buy_orders:
                        quantity = float(buy_order.get('filled_quantity', 0))
                        price = float(buy_order.get('average_price', 0))

                        if quantity > 0 and price > 0:
                            total_quantity += quantity
                            total_cost += quantity * price

                    # Calcular preço médio de compra ponderado
                    avg_buy_price = total_cost / total_quantity if total_quantity > 0 else 0.0

                    if avg_buy_price > 0:
                        print(f"📊 {asset}: Preço médio de compra = ${avg_buy_price:.4f} (de {len(buy_orders)} compras)")

                    # Calcular P&L para cada ordem deste ativo
                    for order in asset_orders:
                        try:
                            if order.get('side') == 'sell' and avg_buy_price > 0:
                                # Para vendas: (preço_venda - preço_médio_compra) × quantidade
                                sell_price = float(order.get('average_price', 0))
                                quantity = float(order.get('filled_quantity', 0))

                                if sell_price > 0 and quantity > 0:
                                    pnl = (sell_price - avg_buy_price) * quantity
                                    order['profit_loss'] = round(pnl, 4)
                                    print(f"💰 {asset} SELL: {quantity:.4f} @ ${sell_price:.4f} vs avg ${avg_buy_price:.4f} = ${pnl:.4f}")

                            elif order.get('side') == 'buy' and avg_buy_price > 0:
                                # Para compras: P&L vs preço médio (se for mais barato que a média)
                                buy_price = float(order.get('average_price', 0))
                                quantity = float(order.get('filled_quantity', 0))

                                if buy_price > 0 and quantity > 0:
                                    # P&L potencial se vendesse ao preço médio
                                    pnl_potential = (avg_buy_price - buy_price) * quantity
                                    order['profit_loss'] = round(pnl_potential, 4)
                                    print(f"📈 {asset} BUY: {quantity:.4f} @ ${buy_price:.4f} vs avg ${avg_buy_price:.4f} = ${pnl_potential:.4f} (vs média)")

                        except Exception as e:
                            print(f"❌ Erro calculando P&L para ordem {order.get('id', 'N/A')}: {e}")
                            continue

                except Exception as e:
                    print(f"❌ Erro calculando P&L SPOT para {asset}: {e}")
                    continue

            # CALCULAR P&L PARA ORDENS FUTURES
            for asset, asset_orders in futures_orders_by_asset.items():
                try:
                    # FUTURES: Calcular preço médio de compra (entrada)
                    total_quantity = 0.0
                    total_cost = 0.0

                    # Coletar apenas ordens de compra (BUY) para calcular preço médio
                    buy_orders = [o for o in asset_orders if o.get('side') == 'buy' and o.get('filled_quantity', 0) > 0]

                    for buy_order in buy_orders:
                        quantity = float(buy_order.get('filled_quantity', 0))
                        price = float(buy_order.get('average_price', 0))

                        if quantity > 0 and price > 0:
                            total_quantity += quantity
                            total_cost += quantity * price

                    # Calcular preço médio de entrada ponderado
                    avg_entry_price = total_cost / total_quantity if total_quantity > 0 else 0.0

                    if avg_entry_price > 0:
                        print(f"📊 {asset} FUTURES: Preço médio de entrada = ${avg_entry_price:.4f} (de {len(buy_orders)} compras)")

                    # Calcular P&L para cada ordem FUTURES deste ativo
                    for order in asset_orders:
                        try:
                            if order.get('side') == 'sell' and avg_entry_price > 0:
                                # Para vendas FUTURES: (preço_venda - preço_médio_entrada) × quantidade
                                sell_price = float(order.get('average_price', 0))
                                quantity = float(order.get('filled_quantity', 0))

                                if sell_price > 0 and quantity > 0:
                                    pnl = (sell_price - avg_entry_price) * quantity
                                    order['profit_loss'] = round(pnl, 4)
                                    print(f"💰 {asset} FUTURES SELL: {quantity:.4f} @ ${sell_price:.4f} vs avg ${avg_entry_price:.4f} = ${pnl:.4f}")

                            elif order.get('side') == 'buy' and avg_entry_price > 0:
                                # Para compras FUTURES: P&L vs preço médio (se for mais barato que a média)
                                buy_price = float(order.get('average_price', 0))
                                quantity = float(order.get('filled_quantity', 0))

                                if buy_price > 0 and quantity > 0:
                                    # P&L potencial se vendesse ao preço médio
                                    pnl_potential = (avg_entry_price - buy_price) * quantity
                                    order['profit_loss'] = round(pnl_potential, 4)
                                    print(f"📈 {asset} FUTURES BUY: {quantity:.4f} @ ${buy_price:.4f} vs avg ${avg_entry_price:.4f} = ${pnl_potential:.4f} (vs média)")

                        except Exception as e:
                            print(f"❌ Erro calculando P&L para ordem FUTURES {order.get('id', 'N/A')}: {e}")
                            continue

                except Exception as e:
                    print(f"❌ Erro calculando P&L FUTURES para {asset}: {e}")
                    continue

            print(f"✅ FASE 2: P&L calculado para {len(spot_orders)} SPOT + {len(futures_orders)} FUTURES operações")

        except Exception as e:
            print(f"❌ Erro no cálculo de P&L: {e}")
            # Continuar sem P&L se houver erro

        # GERAR ORDER_ID para agrupar operações relacionadas
        print(f"🔗 Gerando order_id para agrupar operações relacionadas...")
        try:
            # IMPORTANTE: NÃO reordenar! Manter ordem por data (mais recentes primeiro)
            # Criar índice temporário para processar agrupamento sem alterar ordem

            operation_groups = {}
            current_order_id = 1

            # Processar em ordem cronológica reversa (mais antigas primeiro) para agrupar corretamente
            # mas sem alterar a lista original
            orders_chronological = sorted(orders_list, key=lambda x: x.get('created_at', ''))

            for order in orders_chronological:
                symbol = order.get('symbol', '')
                created_at_str = order.get('created_at', '')
                operation_type = order.get('operation_type', 'spot')

                if not created_at_str:
                    order['order_id'] = f"OP_{current_order_id}"
                    current_order_id += 1
                    continue

                try:
                    order_time = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                except:
                    order['order_id'] = f"OP_{current_order_id}"
                    current_order_id += 1
                    continue

                # Buscar grupo existente para este símbolo + operation_type
                group_key = f"{symbol}_{operation_type}"
                found_group = False

                if group_key in operation_groups:
                    for existing_group_id, group_data in operation_groups[group_key].items():
                        # Se ordem está dentro de 10 minutos da última ordem do grupo
                        time_diff = abs((order_time - group_data['last_time']).total_seconds())
                        if time_diff <= 600:  # 10 minutos
                            order['order_id'] = existing_group_id
                            group_data['last_time'] = max(group_data['last_time'], order_time)
                            group_data['count'] += 1
                            found_group = True
                            break

                if not found_group:
                    # Criar novo grupo
                    new_group_id = f"OP_{current_order_id}"
                    if group_key not in operation_groups:
                        operation_groups[group_key] = {}

                    operation_groups[group_key][new_group_id] = {
                        'last_time': order_time,
                        'count': 1
                    }
                    order['order_id'] = new_group_id
                    current_order_id += 1

            # Contar grupos criados
            total_groups = sum(len(groups) for groups in operation_groups.values())
            print(f"✅ Criados {total_groups} grupos de operações para {len(orders_list)} ordens")

            # MANTER ORDEM ORIGINAL (mais recentes primeiro) - NÃO reordenar!
            # orders_list já está ordenado corretamente

        except Exception as e:
            print(f"❌ Erro gerando order_id: {e}")
            # Fallback: usar IDs sequenciais simples
            for i, order in enumerate(orders_list):
                order['order_id'] = f"OP_{i+1}"

        print(f"✅ Processadas {len(orders_list)} ordens com sucesso")
        return {"success": True, "data": orders_list, "total": len(orders_list)}

    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to fetch orders", "detail": str(e)},
        )


@app.get("/api/v1/orders/stats")
async def get_orders_stats():
    """Estatísticas das ordens para dashboard"""
    try:
        stats = await transaction_db.fetchrow(
            """
            SELECT
                COUNT(*) as total_orders,
                COUNT(CASE WHEN status IN ('FILLED', 'filled') THEN 1 END) as filled_orders,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_orders,
                COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_orders,
                SUM(CASE WHEN status IN ('FILLED', 'filled') AND filled_quantity > 0
                    THEN filled_quantity * COALESCE(average_price, price, 0)
                    ELSE 0 END) as total_volume
            FROM trading_orders
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """
        )

        total = stats["total_orders"] or 0
        filled = stats["filled_orders"] or 0

        return {
            "success": True,
            "data": {
                "total_orders": total,
                "filled_orders": filled,
                "pending_orders": stats["pending_orders"] or 0,
                "failed_orders": stats["failed_orders"] or 0,
                "success_rate": round((filled / total * 100) if total > 0 else 0, 1),
                "total_volume": float(stats["total_volume"])
                if stats["total_volume"]
                else 0,
            },
        }

    except Exception as e:
        logger.error(f"Error fetching order stats: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to fetch order stats", "detail": str(e)},
        )


@app.get("/api/v1/orders/{order_id}")
async def get_order_details(order_id: int):
    """Busca detalhes de uma ordem específica"""
    try:
        order = await transaction_db.fetchrow(
            """
            SELECT 
                id, webhook_delivery_id, symbol, side, order_type, quantity, price, status,
                exchange, exchange_order_id, filled_quantity, average_price,
                error_message, raw_response, created_at, updated_at
            FROM trading_orders 
            WHERE id = $1
        """,
            order_id,
        )

        if not order:
            return JSONResponse(status_code=404, content={"error": "Order not found"})

        order_data = {
            "id": order["id"],
            "webhook_delivery_id": order["webhook_delivery_id"],
            "symbol": order["symbol"],
            "side": order["side"],
            "order_type": order["order_type"],
            "quantity": float(order["quantity"]) if order["quantity"] else 0,
            "price": float(order["price"]) if order["price"] else None,
            "status": order["status"],
            "exchange": order["exchange"],
            "exchange_order_id": order["exchange_order_id"],
            "filled_quantity": float(order["filled_quantity"])
            if order["filled_quantity"]
            else 0,
            "average_price": float(order["average_price"])
            if order["average_price"]
            else None,
            "error_message": order["error_message"],
            "raw_response": order["raw_response"],
            "created_at": order["created_at"].isoformat()
            if order["created_at"]
            else None,
            "updated_at": order["updated_at"].isoformat()
            if order["updated_at"]
            else None,
        }

        return {"success": True, "data": order_data}

    except Exception as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to fetch order details", "detail": str(e)},
        )


@app.post("/api/v1/orders/test")
async def create_test_order():
    """Criar ordem de teste manualmente"""
    try:
        test_payload = {
            "ticker": "BTCUSDT",
            "action": "buy",
            "quantity": 0.001,
            "price": 50000.00,
            "order_type": "market",
        }

        result = await order_processor.process_tradingview_webhook(test_payload)

        return {"success": True, "message": "Test order created", "data": result}

    except Exception as e:
        logger.error(f"Error creating test order: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to create test order", "detail": str(e)},
        )


# 🔐 ENDPOINT DE LOGIN FUNCIONANDO COM MESMA CONEXÃO DOS ORDERS
@app.post("/api/v1/auth/login")
async def auth_login_override(request: Request):
    """Login usando a mesma conexão que funciona para orders"""
    try:
        body = await request.json()
        email = body.get("email")
        password = body.get("password")

        if not email or not password:
            return JSONResponse(
                status_code=400, content={"detail": "Email and password required"}
            )

        # Buscar usuário no banco usando a mesma conexão dos orders
        user = await transaction_db.fetchrow(
            """
            SELECT id, email, name, password_hash, is_active, is_verified, totp_enabled, created_at
            FROM users 
            WHERE email = $1 AND is_active = true
        """,
            email,
        )

        if not user:
            return JSONResponse(
                status_code=401, content={"detail": "Incorrect email or password"}
            )

        # Verificar senha com bcrypt
        import bcrypt

        try:
            password_valid = bcrypt.checkpw(
                password.encode("utf-8"), user["password_hash"].encode("utf-8")
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return JSONResponse(
                status_code=401, content={"detail": "Incorrect email or password"}
            )

        if not password_valid:
            return JSONResponse(
                status_code=401, content={"detail": "Incorrect email or password"}
            )

        # Criar tokens
        import jwt
        from datetime import datetime, timedelta

        # Token payload
        access_payload = {
            "user_id": str(user["id"]),  # Converter UUID para string
            "email": user["email"],
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=30),  # 30 minutos
        }

        refresh_payload = {
            "user_id": str(user["id"]),  # Converter UUID para string
            "email": user["email"],
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=7),  # 7 dias
        }

        # Chave secreta (em produção usar variável de ambiente)
        secret_key = "trading_platform_secret_key_2024"

        access_token = jwt.encode(access_payload, secret_key, algorithm="HS256")
        refresh_token = jwt.encode(refresh_payload, secret_key, algorithm="HS256")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 1800,  # 30 minutos em segundos
            "token_type": "bearer",
        }

    except Exception as e:
        logger.error(f"Login error: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.get("/api/v1/auth/me")
async def get_current_user(request: Request):
    """Get current user profile"""
    try:
        # Extrair token do header Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401, content={"detail": "Authentication required"}
            )

        token = auth_header.split(" ")[1]

        # Verificar token
        import jwt

        secret_key = "trading_platform_secret_key_2024"

        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            user_id = payload.get("user_id")
            email = payload.get("email")
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token expired"})
        except jwt.InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        # Buscar usuário atual no banco
        user = await transaction_db.fetchrow(
            """
            SELECT id, email, name, is_active, is_verified, totp_enabled, created_at
            FROM users 
            WHERE id = $1 AND is_active = true
        """,
            user_id,
        )

        if not user:
            return JSONResponse(status_code=401, content={"detail": "User not found"})

        return {
            "id": str(user["id"]),  # Converter UUID para string
            "email": user["email"],
            "name": user["name"],
            "isActive": user["is_active"],
            "isVerified": user["is_verified"],
            "totpEnabled": user["totp_enabled"],
            "createdAt": user["created_at"].isoformat(),
            "updatedAt": user["created_at"].isoformat(),
        }

    except Exception as e:
        logger.error(f"Get current user error: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.get("/api/v1/exchange-accounts")
async def get_exchange_accounts():
    """Get exchange accounts from database"""
    try:
        # Get exchange accounts from database
        accounts = await transaction_db.fetch("""
            SELECT
                id, name, exchange,
                testnet, is_active, created_at, updated_at
            FROM exchange_accounts
            WHERE is_active = true
            ORDER BY created_at DESC
        """)

        result = []
        for account in accounts:
            result.append({
                "id": str(account["id"]),
                "name": account["name"],
                "exchange": account["exchange"],
                "api_key_preview": "***key***",
                "testnet": account["testnet"],
                "is_active": account["is_active"],
                "status": "connected" if account["is_active"] else "disconnected",
                "balance": {
                    "total": 0.0,  # Would need to fetch from exchange API
                    "available": 0.0,
                    "used": 0.0
                },
                "created_at": account["created_at"].isoformat(),
                "updated_at": account["updated_at"].isoformat()
            })

        return result
    except Exception as e:
        logger.error(f"Get exchange accounts error: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.get("/api/v1/webhooks")
async def get_webhooks():
    """Get webhooks from database"""
    try:
        # Mock webhook data for demo
        result = [
            {
                "id": "webhook_1",
                "name": "TradingView Webhook",
                "url": "/api/v1/webhooks/tradingview",
                "secret_key": "***hidden***",
                "status": "active",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "last_triggered": None
            }
        ]

        return result
    except Exception as e:
        logger.error(f"Get webhooks error: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})



if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.environment == "development",
        log_level="info",
    )
