"""FastAPI main application - Entry point"""

import structlog
import json
from datetime import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from fastapi import FastAPI, Request, Query
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


# 📊 ENDPOINTS PARA FRONTEND - VISUALIZAÇÃO DE ORDENS
@app.get("/api/v1/orders")
async def get_orders(
    limit: int = Query(default=50, description="Limite de ordens a retornar"),
    exchange_account_id: str = Query(default=None, description="ID da conta de exchange"),
    date_from: str = Query(default=None, description="Data inicial (YYYY-MM-DD)"),
    date_to: str = Query(default=None, description="Data final (YYYY-MM-DD)")
):
    """Lista ordens com filtros para o frontend"""
    try:
        # Construir query dinamicamente baseada nos filtros
        base_query = """
            SELECT
                t.id, t.symbol, t.side, t.order_type, t.quantity, t.price, t.status,
                t.exchange, t.exchange_order_id, t.filled_quantity, t.average_price,
                t.created_at, t.updated_at
            FROM trading_orders t
        """

        conditions = []
        params = {}
        joins = []

        # Filtro por exchange account - primeiro buscar o nome da exchange
        param_values = []
        if exchange_account_id:
            # Buscar o nome da exchange baseado no UUID
            try:
                exchange_account = await transaction_db.fetchrow(
                    "SELECT exchange FROM exchange_accounts WHERE id = $1",
                    exchange_account_id
                )
                if exchange_account:
                    param_values.append(exchange_account['exchange'])
                    conditions.append(f"t.exchange = ${len(param_values)}")
            except Exception as e:
                print(f"❌ Erro ao buscar exchange account: {e}")
                # Se não encontrar a conta, não aplicar filtro

        # Filtro por data
        if date_from:
            param_values.append(date_from)
            conditions.append(f"DATE(t.created_at) >= ${len(param_values)}")

        if date_to:
            param_values.append(date_to)
            conditions.append(f"DATE(t.created_at) <= ${len(param_values)}")

        # Adicionar WHERE se houver condições
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        # Adicionar ordenação e limite
        base_query += " ORDER BY t.created_at DESC"
        if limit:
            base_query += f" LIMIT {limit}"

        print(f"🔍 Orders Query: {base_query}")
        print(f"🔍 Orders Params: {param_values}")

        orders = await transaction_db.fetch(base_query, *param_values)

        # Converter para formato JSON serializable
        orders_list = []
        for order in orders:
            orders_list.append(
                {
                    "id": order["id"],
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
                    "created_at": order["created_at"].isoformat()
                    if order["created_at"]
                    else None,
                    "updated_at": order["updated_at"].isoformat()
                    if order["updated_at"]
                    else None,
                }
            )

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
