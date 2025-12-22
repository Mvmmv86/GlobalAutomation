"""FastAPI main application - Entry point - v2.1 - Reload trigger"""

import os
import structlog
import json
from datetime import datetime, date, timedelta
from contextlib import asynccontextmanager

# IMPORTANTE: Carregar .env apenas em desenvolvimento
# Em produção (DigitalOcean), as variáveis vêm do App Platform Environment Variables
if os.getenv("ENV", "development") != "production":
    from dotenv import load_dotenv
    load_dotenv()
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from presentation.controllers.webhook_controller import create_webhook_router
from presentation.controllers.webhooks_crud_controller import create_webhooks_crud_router
from presentation.controllers.tradingview_webhook_secure_controller import create_secure_tradingview_webhook_router
from presentation.controllers.health_controller import create_health_router
from presentation.controllers.dashboard_controller import create_dashboard_router
from presentation.controllers.positions_controller import create_positions_router
from presentation.controllers.dashboard_cards_controller import create_dashboard_cards_router
from presentation.controllers.sync_controller import create_sync_router
from presentation.controllers.exchange_account_controller import create_exchange_account_router
from presentation.controllers.market_controller import router as market_router
from presentation.controllers.orders_controller import create_orders_router
from presentation.controllers.sltp_update_controller import router as sltp_router
from presentation.controllers.websocket_controller import create_websocket_router
from presentation.controllers.bots_controller import router as bots_router
from presentation.controllers.bot_subscriptions_controller import router as bot_subscriptions_router
from presentation.controllers.admin_controller import router as admin_router
from presentation.controllers.chart_data_controller import router as chart_data_router
from presentation.controllers.notifications_controller import create_notifications_router
from presentation.controllers.indicator_alerts_controller import create_indicator_alerts_router
# TODO: Re-enable after refactoring - strategy_controller depends on indicators module
# from presentation.controllers.strategy_controller import router as strategy_router
from infrastructure.background.sync_scheduler import sync_scheduler
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.exchanges.bybit_connector import BybitConnector
from infrastructure.security.encryption_service import EncryptionService
from infrastructure.pricing.binance_price_service import BinancePriceService
from infrastructure.cache import start_cache_cleanup_task
from infrastructure.cache.candles_cache import start_candles_cache_cleanup
from infrastructure.services.indicator_alert_monitor import get_indicator_alert_monitor
from infrastructure.services.strategy_websocket_monitor import get_strategy_ws_monitor

# from presentation.controllers.auth_controller import create_auth_router  # Removido - problema DI
from infrastructure.config.settings import get_settings
from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.database.connection import database_manager
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

        # Also initialize the regular database manager for chart cache
        await database_manager.connect()
        logger.info("Database manager connected successfully (for chart cache)")

        # Initialize Redis (temporarily disabled for integration testing)
        # await redis_manager.connect()
        logger.info("Redis connection skipped for integration testing")

        # Start background sync scheduler
        logger.info("🚀 Starting background sync scheduler with real prices (30s interval)")
        await sync_scheduler.start()  # Habilitado para dados em tempo real

        # Start cache cleanup background task
        logger.info("🧹 Starting cache cleanup background task (60s interval)")
        import asyncio
        asyncio.create_task(start_cache_cleanup_task())

        # Start candles cache cleanup
        logger.info("📊 Starting candles cache cleanup background task")
        asyncio.create_task(start_candles_cache_cleanup())

        # Start indicator alert monitor (checks indicator signals every 30s)
        print("📊 [main.py] Starting Indicator Alert Monitor...")
        try:
            indicator_alert_monitor = get_indicator_alert_monitor(transaction_db)
            print(f"📊 [main.py] Got indicator_alert_monitor: {indicator_alert_monitor}")
            await indicator_alert_monitor.start()
            print("📊 [main.py] Indicator Alert Monitor start() completed")
        except Exception as e:
            print(f"❌ [main.py] Error starting Indicator Alert Monitor: {e}")
            import traceback
            traceback.print_exc()

        # Start Strategy WebSocket Monitor (real-time signal detection < 1s latency)
        strategy_ws_monitor = None
        print("🚀 [main.py] Starting Strategy WebSocket Monitor (real-time)...")
        try:
            strategy_ws_monitor = get_strategy_ws_monitor(transaction_db)
            await strategy_ws_monitor.start()
            print("🚀 [main.py] Strategy WebSocket Monitor started successfully!")
        except Exception as e:
            print(f"⚠️ [main.py] Strategy WebSocket Monitor not started (optional): {e}")

        yield

    finally:
        # Shutdown
        logger.info("Shutting down TradingView Gateway API")

        # Stop background sync scheduler
        logger.info("🛑 Stopping background sync scheduler")
        await sync_scheduler.stop()

        # Stop indicator alert monitor
        await indicator_alert_monitor.stop()

        # Stop strategy WebSocket monitor
        if strategy_ws_monitor:
            await strategy_ws_monitor.stop()

        # Close connections
        await transaction_db.disconnect()
        await database_manager.disconnect()
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

    # Security middleware - TrustedHostMiddleware
    # NOTA: Desabilitado em produção porque o DigitalOcean App Platform
    # já faz validação de host e usa hosts internos que não conseguimos prever.
    # O proxy reverso do DO já garante a segurança de host.
    # if settings.environment == "production":
    #     app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    # 🚀 PERFORMANCE: GZip compression for faster data transfer
    app.add_middleware(
        GZipMiddleware,
        minimum_size=500  # Compress responses >= 500 bytes
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

        # REMOVIDO: Middleware que consumia o body e causava timeout
        # O body agora é lido diretamente no controller sem interferência

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
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors with detailed logging"""
        errors = exc.errors()
        logger.error(
            "Validation error occurred",
            path=request.url.path,
            errors=errors,
            body=exc.body if hasattr(exc, 'body') else None
        )

        # Format error messages for user
        error_messages = []
        for error in errors:
            field = " -> ".join(str(loc) for loc in error['loc'])
            msg = error['msg']
            error_messages.append(f"{field}: {msg}")

        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "detail": "Invalid parameters. " + "; ".join(error_messages),
                "validation_errors": errors
            }
        )

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
    webhook_router = create_webhook_router()  # ✅ DESCOMENTADO - Webhooks TradingView
    health_router = create_health_router()
    dashboard_router = create_dashboard_router()
    positions_router = create_positions_router()
    dashboard_cards_router = create_dashboard_cards_router()
    sync_router = create_sync_router()

    # app.include_router(auth_router, prefix="/api/v1")  # Comentado temporariamente
    app.include_router(webhook_router, prefix="/api/v1")  # ✅ DESCOMENTADO - Webhooks TradingView
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(dashboard_router)
    app.include_router(positions_router)
    app.include_router(dashboard_cards_router)
    app.include_router(sync_router)
    app.include_router(create_exchange_account_router())
    app.include_router(market_router)  # Market data (candles, ticker)
    app.include_router(create_orders_router())  # Orders endpoints (create, close, modify)
    app.include_router(sltp_router, prefix="/api/v1/orders")  # SL/TP modification endpoint
    app.include_router(create_websocket_router())  # WebSocket for real-time notifications
    app.include_router(create_webhooks_crud_router())  # Webhooks CRUD endpoints (já tem prefix interno)
    app.include_router(create_secure_tradingview_webhook_router(), prefix="/api/v1")  # Secure TradingView webhooks with all security layers
    app.include_router(bots_router)  # Bots management (copy-trading)
    app.include_router(bot_subscriptions_router)  # Bot subscriptions
    app.include_router(admin_router)  # Admin management (dashboard, users, bots CRUD)
    app.include_router(chart_data_router)  # Chart data and WebSocket support
    app.include_router(create_notifications_router())  # Notifications CRUD endpoints
    app.include_router(create_indicator_alerts_router())  # Indicator Alerts CRUD endpoints
    # TODO: Re-enable after refactoring
    # app.include_router(strategy_router)  # Automated trading strategies


    return app


# Create app instance
app = create_app()


# ============================================================================
# ADMIN PANEL - Serve static files
# ============================================================================
import os
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Path to admin panel dist folder
ADMIN_DIST_PATH = Path(__file__).parent.parent.parent / "frontend-admin" / "dist"

if ADMIN_DIST_PATH.exists():
    # Mount static files (CSS, JS, images)
    app.mount("/dashboard-admin/assets", StaticFiles(directory=str(ADMIN_DIST_PATH / "assets")), name="admin-assets")

    # Serve index.html for /dashboard-admin and all sub-routes
    from fastapi.responses import FileResponse

    @app.get("/dashboard-admin{full_path:path}")
    async def serve_admin(full_path: str):
        """Serve admin panel SPA (Single Page Application)"""
        # Always return index.html for client-side routing
        return FileResponse(str(ADMIN_DIST_PATH / "index.html"))

    logger.info(f"✅ Admin panel mounted at /dashboard-admin (path: {ADMIN_DIST_PATH})")
else:
    logger.warning(f"⚠️ Admin panel not found at {ADMIN_DIST_PATH}")


@app.get("/")
async def root():
    """Root endpoint"""
    settings = get_settings()

    # Extrair identificador do banco (para debug)
    db_url = settings.database_url
    # Pegar apenas o identificador do projeto Supabase (ex: zmdqmrugotfftxvrwdsd)
    db_identifier = "unknown"
    db_region = "unknown"
    if "postgres." in db_url:
        try:
            db_identifier = db_url.split("postgres.")[1].split(":")[0]
        except:
            pass

    if "us-east" in db_url:
        db_region = "us-east-2 (DEV)"
    elif "us-west" in db_url:
        db_region = "us-west-2 (PROD)"

    return {
        "service": "TradingView Gateway API",
        "version": settings.version,
        "environment": settings.environment,
        "status": "healthy",
        "database": "asyncpg (pgBouncer transaction mode)",
        "database_identifier": db_identifier,  # Para debug - mostra qual banco está conectado
        "database_region": db_region,
        "is_using_dev_db": db_identifier == "zmdqmrugotfftxvrwdsd",
        "is_using_prod_db": db_identifier == "wqmqsanuegvzbmjtxzac",
        "admin_panel": "/dashboard-admin" if ADMIN_DIST_PATH.exists() else "not_available"
    }


@app.get("/debug/database-check")
async def debug_database_check():
    """
    TEMPORÁRIO: Endpoint para debug - identificar qual banco está conectado
    REMOVER APÓS RESOLVER O PROBLEMA!
    """
    import os
    settings = get_settings()
    db_url = settings.database_url

    # Extrair identificadores (sem expor senha)
    db_identifier = "unknown"
    db_region = "unknown"

    if "postgres." in db_url:
        try:
            db_identifier = db_url.split("postgres.")[1].split(":")[0]
        except:
            pass

    if "us-east" in db_url:
        db_region = "us-east-2 (DEV)"
    elif "us-west" in db_url:
        db_region = "us-west-2 (PROD)"

    # Verificar variáveis de ambiente diretamente
    raw_db_url = os.getenv("DATABASE_URL", "NOT_SET")
    raw_env = os.getenv("ENV", "NOT_SET")

    # Mascarar senha
    masked_raw_url = "NOT_SET"
    if raw_db_url != "NOT_SET":
        try:
            # postgresql+asyncpg://postgres.XXX:PASSWORD@host
            parts = raw_db_url.split("@")
            if len(parts) == 2:
                user_pass = parts[0].split(":")
                if len(user_pass) >= 3:
                    masked_raw_url = f"{user_pass[0]}:{user_pass[1]}:****@{parts[1]}"
                else:
                    masked_raw_url = raw_db_url[:50] + "..."
        except:
            masked_raw_url = raw_db_url[:50] + "..."

    return {
        "CRITICAL_INFO": "🚨 SE is_dev=True EM PRODUÇÃO, HÁ UM PROBLEMA CRÍTICO!",
        "database_identifier": db_identifier,
        "database_region": db_region,
        "is_dev": db_identifier == "zmdqmrugotfftxvrwdsd",
        "is_prod": db_identifier == "wqmqsanuegvzbmjtxzac",
        "settings_environment": settings.environment,
        "os_ENV": raw_env,
        "os_DATABASE_URL_masked": masked_raw_url,
        "env_file_used": str(settings.model_config.get("env_file", "NOT_SET")),
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


# 🔄 REDIRECT: Rota antiga mantida para compatibilidade (zero downtime)
# Redireciona para /api/v1/webhooks/tv/{id} que tem tracking completo
@app.post("/api/v1/webhooks/tradingview/{webhook_id}")
async def tradingview_webhook_redirect(request: Request, webhook_id: str):
    """
    REDIRECT: Mantido para compatibilidade com URLs antigas.
    Encaminha para a rota nova /api/v1/webhooks/tv/ que tem tracking completo.
    """
    # Simplesmente redireciona para a rota nova usando RedirectResponse
    # Status 307 mantém o método POST e o body
    return RedirectResponse(
        url=f"/api/v1/webhooks/tv/{webhook_id}",
        status_code=307
    )


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

        # Decrypt API credentials - CRÍTICO: Não usar fallback (escalabilidade)
        try:
            api_key = encryption_service.decrypt_string(account['api_key']) if account['api_key'] else None
            secret_key = encryption_service.decrypt_string(account['secret_key']) if account['secret_key'] else None
            passphrase = encryption_service.decrypt_string(account['passphrase']) if account['passphrase'] else None
            print(f"✅ API keys decrypted successfully for account {account['id']}")
        except Exception as decrypt_error:
            # ERRO CRÍTICO: Não usar fallback para variáveis de ambiente
            # Cada cliente deve ter suas próprias chaves descriptografadas
            print(f"❌ CRITICAL: Failed to decrypt API keys for account {account['id']}: {decrypt_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Cannot decrypt exchange API keys. Please check your exchange account configuration."
            )

        # Validar que as chaves foram descriptografadas
        if not api_key or not secret_key:
            print(f"❌ CRITICAL: API keys are empty after decryption for account {account['id']}")
            raise HTTPException(
                status_code=500,
                detail="Exchange API keys are not configured correctly"
            )

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
    Estratégia híbrida MELHORADA para garantir cobertura completa de símbolos:
    1. Símbolos de POSIÇÕES ATUAIS (ativos novos que o usuário está operando)
    2. Símbolos HISTÓRICOS do banco (ordens antigas)
    3. Símbolos populares como fallback
    4. Combinar tudo sem duplicatas
    """
    try:
        print("🔍 Iniciando busca híbrida MELHORADA de símbolos...")

        all_discovered_symbols = []

        # 1. DESCOBERTA DINÂMICA: Buscar posições atuais direto da Binance (como faz Positions)
        try:
            connector = await get_exchange_connector(exchange_account_id)

            # Buscar FUTURES positions (ativos com posição)
            futures_result = await connector.get_futures_positions()
            if futures_result.get('success', True):
                futures_positions = futures_result.get('positions', [])
                futures_symbols = []
                for pos in futures_positions:
                    symbol = pos.get('symbol')
                    # Pegar apenas posições com quantidade > 0
                    position_amt = abs(float(pos.get('positionAmt', 0)))
                    if symbol and position_amt > 0:
                        futures_symbols.append(symbol)

                if futures_symbols:
                    print(f"🎯 FUTURES: {len(futures_symbols)} símbolos com posição ativa: {futures_symbols[:5]}...")
                    all_discovered_symbols.extend(futures_symbols)

            # Buscar SPOT balances (ativos na carteira)
            spot_result = await connector.get_account()
            if spot_result.get('success', True):
                spot_balances = spot_result.get('balances', [])
                spot_symbols = []
                for balance in spot_balances:
                    asset = balance.get('asset', '')
                    free = float(balance.get('free', 0))
                    locked = float(balance.get('locked', 0))

                    # Se tem saldo, adicionar símbolo USDT
                    if (free + locked) > 0 and asset != 'USDT':
                        symbol = f"{asset}USDT"
                        spot_symbols.append(symbol)

                if spot_symbols:
                    print(f"💰 SPOT: {len(spot_symbols)} ativos com saldo: {spot_symbols[:5]}...")
                    all_discovered_symbols.extend(spot_symbols)

        except Exception as e:
            print(f"⚠️ Erro na descoberta dinâmica de símbolos: {e}")

        # 2. SÍMBOLOS HISTÓRICOS: Buscar da nossa base de dados (últimos 6 meses)
        existing_symbols_rows = await transaction_db.fetch("""
            SELECT DISTINCT symbol
            FROM trading_orders
            WHERE symbol IS NOT NULL
              AND symbol != ''
              AND created_at >= NOW() - INTERVAL '6 months'
            ORDER BY symbol
        """)

        existing_symbols = [row['symbol'] for row in existing_symbols_rows]
        if existing_symbols:
            print(f"📚 Histórico do banco: {len(existing_symbols)} símbolos dos últimos 6 meses")
            all_discovered_symbols.extend(existing_symbols)

        # 3. SÍMBOLOS POPULARES: Lista curada dos principais pares (fallback mínimo)
        popular_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'LINKUSDT', 'DOTUSDT', 'AVAXUSDT',
            'XRPUSDT', 'LTCUSDT', 'MATICUSDT', 'ATOMUSDT', 'ALGOUSDT', 'VETUSDT', 'XLMUSDT', 'TRXUSDT',
            'EOSUSDT', 'IOTAUSDT', 'NEOUSDT', 'DASHUSDT', 'ETCUSDT', 'XMRUSDT', 'ZECUSDT', 'COMPUSDT',
            'FILUSDT', 'UNIUSDT', 'AAVEUSDT', 'SUSHIUSDT', 'CHZUSDT', 'MANAUSDT', 'SANDUSDT', 'ENJUSDT',
            'GRTUSDT', 'BALUSDT', 'CRVUSDT', 'RNDRUSDT', 'NEARUSDT', 'FTMUSDT', 'APEUSDT', 'GALAUSDT',
            # Adicionar ativos novos populares
            'WIFUSDT', 'SEIUSDT', 'ARBUSDT', 'OPUSDT', 'INJUSDT', 'SUIUSDT', 'APTUSDT', 'STXUSDT',
            'BLURUSDT', 'JUPUSDT', 'TIAUSDT', 'PYTHUSDT', 'ORDIUSDT', 'BONKUSDT', 'DOGEUSDT'
        ]
        all_discovered_symbols.extend(popular_symbols)

        # 4. COMBINAR SEM DUPLICATAS: Descobertos têm prioridade
        all_symbols = list(dict.fromkeys(all_discovered_symbols))

        print(f"🎯 TOTAL DE SÍMBOLOS ÚNICOS: {len(all_symbols)}")
        print(f"   - Posições ativas (descobertos): primeiros da lista")
        print(f"   - Histórico banco: símbolos operados antes")
        print(f"   - Populares: garantia de cobertura mínima")

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


# 🚀 SISTEMA DE CACHE SIMPLES PARA ORDERS
import asyncio
from typing import Dict, List, Any, Optional
from time import time

# Cache global para orders (em memória)
orders_cache: Dict[str, Dict[str, Any]] = {}
CACHE_DURATION = 60  # 60 segundos

def get_cache_key(account_id: str, date_from: Optional[str], date_to: Optional[str]) -> str:
    """Gera chave única para o cache baseada nos parâmetros"""
    return f"{account_id}_{date_from or 'none'}_{date_to or 'none'}"

def is_cache_valid(cache_entry: Dict[str, Any]) -> bool:
    """Verifica se o cache ainda é válido"""
    if not cache_entry:
        return False
    return (time() - cache_entry.get('timestamp', 0)) < CACHE_DURATION

async def fetch_orders_for_symbol(connector, symbol: str, start_time: Optional[int], end_time: Optional[int]) -> List[Dict]:
    """Busca ordens para um símbolo específico (SPOT + FUTURES) com tratamento de erros"""
    orders = []

    try:
        # SPOT Orders
        try:
            spot_result = await connector.get_account_orders(
                symbol=symbol,
                limit=500,
                start_time=start_time,
                end_time=end_time
            )
            if spot_result.get('success', True):
                spot_orders = spot_result.get('orders', [])
                for order in spot_orders:
                    order['_market_type'] = 'SPOT'
                orders.extend(spot_orders)
        except Exception as e:
            if "Symbol is closed" not in str(e) and "Invalid symbol" not in str(e):
                print(f"⚠️ Erro SPOT {symbol}: {str(e)[:50]}")

        # FUTURES Orders (últimos 7 dias apenas)
        try:
            futures_result = await connector.get_futures_orders(
                symbol=symbol,
                limit=500,
                start_time=None,  # Limitação: apenas 7 dias
                end_time=None
            )
            if futures_result.get('success', True):
                futures_orders = futures_result.get('orders', [])
                for order in futures_orders:
                    order['_market_type'] = 'FUTURES'
                orders.extend(futures_orders)
        except Exception as e:
            if "Symbol is closed" not in str(e) and "Invalid symbol" not in str(e):
                print(f"⚠️ Erro FUTURES {symbol}: {str(e)[:50]}")

    except Exception as e:
        print(f"❌ Erro geral para {symbol}: {str(e)[:50]}")

    if orders:
        print(f"✅ {symbol}: {len(orders)} ordens encontradas")

    return orders

async def fetch_orders_parallel(connector, symbols: List[str], start_time: Optional[int], end_time: Optional[int]) -> List[Dict]:
    """Busca ordens para múltiplos símbolos em paralelo (chunks de 10)"""
    all_orders = []

    # 🚀 PERFORMANCE: Chunks maiores para paralelização mais eficiente
    chunk_size = 20  # Aumentado de 10 para 20 (Binance suporta até ~50 req/s)
    chunks = [symbols[i:i+chunk_size] for i in range(0, len(symbols), chunk_size)]

    print(f"🚀 Processando {len(symbols)} símbolos em {len(chunks)} lotes paralelos de até {chunk_size} símbolos")

    for i, chunk in enumerate(chunks):
        print(f"📦 Lote {i+1}/{len(chunks)}: {len(chunk)} símbolos")

        # Criar tasks para buscar em paralelo
        tasks = [
            fetch_orders_for_symbol(connector, symbol, start_time, end_time)
            for symbol in chunk
        ]

        # Executar em paralelo e coletar resultados
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Processar resultados
        for result in chunk_results:
            if isinstance(result, list):
                all_orders.extend(result)
            elif isinstance(result, Exception):
                print(f"⚠️ Erro em lote: {str(result)[:50]}")

    return all_orders

# 📊 ENDPOINTS PARA FRONTEND - VISUALIZAÇÃO DE ORDENS
@app.get("/api/v1/orders")
async def get_orders(
    limit: int = Query(default=50, description="Limite de ordens a retornar"),
    exchange_account_id: str = Query(default=None, description="ID da conta de exchange"),
    date_from: str = Query(default=None, description="Data inicial (YYYY-MM-DD)"),
    date_to: str = Query(default=None, description="Data final (YYYY-MM-DD)")
):
    """Lista ordens com filtros para o frontend - COM CACHE E PARALELIZAÇÃO"""
    try:
        print(f"🔍 FASE 2: Buscando ordens com CACHE + PARALELIZAÇÃO")
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

        # CACHE: Verificar se temos dados em cache válidos
        cache_key = get_cache_key(account_id_to_use, date_from, date_to)
        cached_data = orders_cache.get(cache_key)

        if cached_data and is_cache_valid(cached_data):
            print(f"✨ CACHE HIT! Retornando {len(cached_data['data'])} ordens do cache (idade: {int(time() - cached_data['timestamp'])}s)")
            return {"success": True, "data": cached_data['data'][:limit], "total": len(cached_data['data']), "cached": True}

        print(f"🔄 CACHE MISS - Buscando dados frescos da API...")

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

        # Filtrar símbolos problemáticos conhecidos
        symbols_blacklist = ['NEOUSDT', 'IOTAUSDT']  # Símbolos deslistados
        all_symbols = [s for s in all_symbols if s not in symbols_blacklist and ' ' not in s]

        print(f"🎯 Sistema Híbrido: {len(all_symbols)} símbolos válidos para busca paralela")

        # 🚀 PARALELIZAÇÃO: Buscar ordens em paralelo (muito mais rápido!)
        start_fetch_time = time()
        all_raw_orders = await fetch_orders_parallel(connector, all_symbols, start_time, end_time)
        fetch_duration = time() - start_fetch_time

        print(f"⚡ Busca paralela completada em {fetch_duration:.2f}s (vs ~{len(all_symbols)*2}s sequencial)")

        # Ordenar por data (mais recentes primeiro) - CRUCIAL para mostrar ordens atuais
        all_raw_orders.sort(key=lambda x: int(x.get('updateTime', x.get('time', 0))), reverse=True)

        # 🧠 BUSCA HÍBRIDA: Complementar com ordens históricas do banco se necessário
        if len(all_raw_orders) < limit and limit > 100:
            print(f"🔍 BUSCA HÍBRIDA: API retornou {len(all_raw_orders)} ordens, buscando {limit - len(all_raw_orders)} do banco...")

            try:
                # Buscar ordens históricas do banco (mais antigas que as da API)
                oldest_api_time = None
                if all_raw_orders:
                    oldest_api_time = min([int(order.get('updateTime', order.get('time', 0))) for order in all_raw_orders])
                    oldest_api_date = datetime.fromtimestamp(oldest_api_time / 1000)
                    print(f"📅 Ordem mais antiga da API: {oldest_api_date}")

                # Query para buscar ordens do banco anteriores às da API
                historical_limit = min(limit - len(all_raw_orders), 500)  # Limite de segurança

                if oldest_api_time:
                    historical_orders_query = """
                        SELECT
                            id, symbol, side, 'market' as order_type, quantity, price, status,
                            exchange, exchange_order_id, filled_quantity, average_price,
                            created_at, updated_at, operation_type, entry_exit,
                            margin_usdt, profit_loss, order_id
                        FROM orders
                        WHERE created_at < $1 AND exchange_account_id = $2
                        ORDER BY created_at DESC
                        LIMIT $3
                    """
                    historical_orders_db = await transaction_db.fetch(
                        historical_orders_query,
                        oldest_api_date,
                        account_id_to_use,
                        historical_limit
                    )
                else:
                    # Se não há ordens da API, buscar as mais recentes do banco
                    historical_orders_query = """
                        SELECT
                            id, symbol, side, 'market' as order_type, quantity, price, status,
                            exchange, exchange_order_id, filled_quantity, average_price,
                            created_at, updated_at, operation_type, entry_exit,
                            margin_usdt, profit_loss, order_id
                        FROM orders
                        WHERE exchange_account_id = $1
                        ORDER BY created_at DESC
                        LIMIT $2
                    """
                    historical_orders_db = await transaction_db.fetch(
                        historical_orders_query,
                        account_id_to_use,
                        historical_limit
                    )

                # Converter ordens do banco para formato compatível
                historical_orders = []
                for order in historical_orders_db:
                    historical_order = {
                        'orderId': str(order['exchange_order_id']),
                        'symbol': order['symbol'],
                        'side': order['side'].upper(),
                        'type': order['order_type'].upper(),
                        'origQty': str(order['quantity']),
                        'price': str(order['price']),
                        'status': order['status'].upper(),
                        'executedQty': str(order['filled_quantity']),
                        'cummulativeQuoteQty': str(float(order['filled_quantity']) * float(order['average_price'])),
                        'time': int(order['created_at'].timestamp() * 1000),
                        'updateTime': int(order['updated_at'].timestamp() * 1000),
                        '_market_type': order['operation_type'].upper(),
                        '_source': 'DATABASE',
                        '_order_id': order['order_id'],
                        '_profit_loss': order['profit_loss']
                    }
                    historical_orders.append(historical_order)

                print(f"✅ BUSCA HÍBRIDA: {len(historical_orders)} ordens históricas encontradas no banco")

                # Mesclar ordens da API + banco
                all_raw_orders.extend(historical_orders)

                # Re-ordenar por data após mesclar
                all_raw_orders.sort(key=lambda x: int(x.get('updateTime', x.get('time', 0))), reverse=True)

                print(f"🔗 TOTAL APÓS BUSCA HÍBRIDA: {len(all_raw_orders)} ordens (API + Banco)")

            except Exception as e:
                print(f"⚠️ Erro na busca híbrida: {e}")
        else:
            print(f"✅ API forneceu {len(all_raw_orders)} ordens suficientes, sem necessidade de busca no banco")

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

        # CACHE: Salvar resultado no cache para próximas requisições
        orders_cache[cache_key] = {
            'data': orders_list,
            'timestamp': time()
        }
        print(f"💾 Resultado salvo no cache (válido por {CACHE_DURATION}s)")

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


@app.get("/api/v1/liquidations")
async def get_liquidations(
    exchangeAccountId: Optional[str] = Query(None, description="ID da conta de exchange"),
    symbol: Optional[str] = Query(None, description="Símbolo específico"),
    startTime: Optional[int] = Query(None, description="Timestamp de início"),
    endTime: Optional[int] = Query(None, description="Timestamp de fim"),
    limit: Optional[int] = Query(100, description="Limite de resultados")
):
    """
    Buscar dados de liquidação (force orders) da Binance

    Retorna ordens de liquidação para análise de preços reais de liquidação
    """
    try:
        if not exchangeAccountId:
            return JSONResponse(
                status_code=400,
                content={"error": "exchangeAccountId é obrigatório"}
            )

        # Buscar connector da exchange
        connector = await get_exchange_connector(exchangeAccountId)
        if not connector:
            return JSONResponse(
                status_code=404,
                content={"error": "Exchange account not found"}
            )

        # Buscar dados de liquidação da Binance
        result = await connector.get_force_orders(
            symbol=symbol,
            start_time=startTime,
            end_time=endTime,
            limit=limit
        )

        if not result.get("success"):
            return JSONResponse(
                status_code=500,
                content={"error": result.get("error", "Failed to fetch liquidations")}
            )

        force_orders = result.get("force_orders", [])

        # Processar dados de liquidação para frontend
        liquidations = []
        for order in force_orders:
            liquidations.append({
                "symbol": order.get("symbol"),
                "side": order.get("side"),
                "orderType": order.get("orderType"),
                "origQty": float(order.get("origQty", 0)) if order.get("origQty") else 0,
                "price": float(order.get("price", 0)) if order.get("price") else 0,
                "avgPrice": float(order.get("avgPrice", 0)) if order.get("avgPrice") else 0,
                "orderStatus": order.get("orderStatus"),
                "timeInForce": order.get("timeInForce"),
                "time": order.get("time"),
                "lastFillTime": order.get("lastFillTime"),
                "executedQty": float(order.get("executedQty", 0)) if order.get("executedQty") else 0,
                "cummulativeQuoteQty": float(order.get("cummulativeQuoteQty", 0)) if order.get("cummulativeQuoteQty") else 0,
            })

        return {
            "success": True,
            "data": liquidations,
            "demo": result.get("demo", False),
            "count": len(liquidations)
        }

    except Exception as e:
        logger.error(f"Error fetching liquidations: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to fetch liquidations", "detail": str(e)}
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


# 🔐 ENDPOINT DE REGISTRO FUNCIONANDO COM MESMA CONEXÃO DOS ORDERS
@app.post("/api/v1/auth/register")
async def auth_register(request: Request):
    """Registrar novo usuário"""
    try:
        body = await request.json()
        email = body.get("email")
        password = body.get("password")
        name = body.get("name", "")

        if not email or not password:
            return JSONResponse(
                status_code=400, content={"detail": "Email and password required"}
            )

        # Validar tamanho mínimo da senha
        if len(password) < 8:
            return JSONResponse(
                status_code=400, content={"detail": "Password must be at least 8 characters"}
            )

        # Verificar se email já existe
        existing_user = await transaction_db.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            email.lower()
        )

        if existing_user:
            return JSONResponse(
                status_code=400, content={"detail": "Email already registered"}
            )

        # Hash da senha com bcrypt
        import bcrypt
        import uuid

        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

        # Criar novo usuário
        user_id = str(uuid.uuid4())

        await transaction_db.execute(
            """
            INSERT INTO users (id, email, name, password_hash, is_active, is_verified, totp_enabled, created_at, updated_at)
            VALUES ($1, $2, $3, $4, true, false, false, NOW(), NOW())
            """,
            user_id,
            email.lower(),
            name or email.split("@")[0],
            password_hash
        )

        logger.info(f"New user registered: {email}")

        return {
            "user_id": user_id,
            "email": email.lower(),
            "message": "User registered successfully"
        }

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


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

        # Chave secreta - usar variável de ambiente SECRET_KEY
        secret_key = os.getenv("SECRET_KEY", "trading_platform_secret_key_2024")

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


# 🔐 ENDPOINT DE REFRESH TOKEN
@app.post("/api/v1/auth/refresh")
async def auth_refresh_token(request: Request):
    """Refresh access token using refresh token"""
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")

        if not refresh_token:
            return JSONResponse(
                status_code=400, content={"detail": "Refresh token required"}
            )

        import jwt
        from datetime import datetime, timedelta

        secret_key = os.getenv("SECRET_KEY", "trading_platform_secret_key_2024")

        try:
            # Verificar refresh token
            payload = jwt.decode(refresh_token, secret_key, algorithms=["HS256"])

            # Verificar se é um refresh token
            if payload.get("type") != "refresh":
                return JSONResponse(
                    status_code=401, content={"detail": "Invalid token type"}
                )

            # Standard JWT uses "sub" for subject (user_id)
            user_id = payload.get("sub") or payload.get("user_id")
            email = payload.get("email", "")

            # Criar novo access token - usando formato padrão JWT
            access_payload = {
                "sub": user_id,  # Standard JWT field for subject
                "email": email,
                "type": "access",
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(minutes=30),
            }

            new_access_token = jwt.encode(access_payload, secret_key, algorithm="HS256")

            return {
                "access_token": new_access_token,
                "expires_in": 1800,  # 30 minutos em segundos
                "token_type": "bearer",
            }

        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401, content={"detail": "Refresh token expired"}
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                status_code=401, content={"detail": "Invalid refresh token"}
            )

    except Exception as e:
        logger.error(f"Refresh token error: {e}")
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

        secret_key = os.getenv("SECRET_KEY", "trading_platform_secret_key_2024")

        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            user_id = payload.get("user_id")
            email = payload.get("email")
        except jwt.ExpiredSignatureError:
            return JSONResponse(status_code=401, content={"detail": "Token expired"})
        except jwt.InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        # Buscar usuário atual no banco usando UUID corretamente
        import uuid as uuid_module

        try:
            # Converter string para UUID se necessário
            if isinstance(user_id, str):
                user_uuid = uuid_module.UUID(user_id)
            else:
                user_uuid = user_id
        except ValueError:
            return JSONResponse(status_code=401, content={"detail": "Invalid user ID format"})

        user = await transaction_db.fetchrow(
            """
            SELECT id, email, name, is_active, is_verified, totp_enabled, created_at
            FROM users
            WHERE id = $1 AND is_active = true
        """,
            user_uuid,
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
async def get_exchange_accounts(request: Request):
    """Get exchange accounts from database - filtered by authenticated user"""
    try:
        # Extrair user_id do token JWT
        auth_header = request.headers.get("Authorization")
        user_id = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            import jwt
            secret_key = os.getenv("SECRET_KEY", "trading_platform_secret_key_2024")
            try:
                payload = jwt.decode(token, secret_key, algorithms=["HS256"])
                user_id = payload.get("user_id")
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                pass

        # Se não há user_id, retorna lista vazia (usuário não autenticado)
        if not user_id:
            return []

        # Converter user_id string para UUID
        import uuid as uuid_module
        try:
            user_uuid = uuid_module.UUID(user_id) if isinstance(user_id, str) else user_id
        except ValueError:
            return []

        # Get exchange accounts from database - FILTRADO POR USER_ID
        accounts = await transaction_db.fetch("""
            SELECT
                id, name, exchange,
                testnet, is_active, created_at, updated_at
            FROM exchange_accounts
            WHERE is_active = true AND user_id = $1
            ORDER BY created_at DESC
        """, user_uuid)

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


# REMOVIDO: Endpoint mock substituído pelo webhooks_crud_controller
# O endpoint GET /api/v1/webhooks agora é fornecido pelo create_webhooks_crud_router()
# que busca dados reais do banco de dados


# 🔗 ENDPOINT DINÂMICO: Retorna URL atual do ngrok
@app.get("/api/v1/ngrok/url")
async def get_ngrok_url():
    """
    Retorna a URL pública atual do ngrok

    O frontend usa este endpoint para gerar URLs de webhook dinamicamente,
    eliminando a necessidade de atualizar manualmente o .env quando o ngrok reinicia.
    """
    try:
        import aiohttp

        # Consultar API local do ngrok
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:4040/api/tunnels") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tunnels = data.get("tunnels", [])

                    if tunnels:
                        # Pegar primeiro tunnel (normalmente só há um)
                        public_url = tunnels[0].get("public_url")

                        return {
                            "success": True,
                            "ngrok_url": public_url,
                            "updated_at": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "success": False,
                            "error": "No ngrok tunnels found",
                            "ngrok_url": None
                        }
                else:
                    return {
                        "success": False,
                        "error": "Ngrok API not accessible",
                        "ngrok_url": None
                    }

    except Exception as e:
        logger.error(f"Error fetching ngrok URL: {e}")
        return {
            "success": False,
            "error": str(e),
            "ngrok_url": None
        }


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
