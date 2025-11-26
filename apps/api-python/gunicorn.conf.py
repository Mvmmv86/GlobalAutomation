"""
Gunicorn configuration for FastAPI on Digital Ocean App Platform
Optimized for performance and concurrent request handling

CRITICAL FIX (2025-10-23):
- post_fork hook reconnects database after worker fork
- Fixes deadlock issue with preload_app=True + asyncpg
- Each worker gets independent database connection (fork-safe)
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8080"

# Worker processes
# Recommended: 2-4 workers for production
# Formula: (2 x $num_cores) + 1
workers = int(os.getenv("GUNICORN_WORKERS", "2"))

# Worker class - CRITICAL: Use Uvicorn workers for FastAPI
worker_class = "uvicorn.workers.UvicornWorker"

# Worker temporary directory
# CRITICAL: Use /dev/shm for better performance on Digital Ocean
worker_tmp_dir = "/dev/shm"

# Timeout settings
# Graceful timeout for workers
timeout = 300  # 2 minutes (increased from default 30s for exchange account creation)
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Process naming
proc_name = "globalautomation-api"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Worker restart settings
max_requests = 1000  # Restart worker after 1000 requests (prevents memory leaks)
max_requests_jitter = 50  # Add randomness to avoid all workers restarting at once

# Preload app for faster worker spawning
preload_app = True

# Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("🚀 Starting Gunicorn server")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info(f"✅ Gunicorn ready with {workers} workers")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("👋 Gunicorn shutting down")

def worker_int(worker):
    """Called when a worker receives INT or QUIT signal."""
    worker.log.info(f"⚠️ Worker {worker.pid} received INT/QUIT")

def post_fork(server, worker):
    """
    Called just after a worker has been forked.
    CRITICAL: Reconnect to database to avoid fork-safety issues with asyncpg.
    """
    server.log.info(f"🔧 Worker spawned (pid: {worker.pid})")

    # SOLUÇÃO: Reconectar ao banco após fork
    # Cada worker terá sua própria conexão independente
    import asyncio
    from infrastructure.database.connection_transaction_mode import transaction_db

    async def reconnect_db():
        """Reconectar ao banco no worker filho (fork-safe)"""
        try:
            # Tentar fechar conexão herdada do processo pai
            try:
                await transaction_db.disconnect()
                server.log.info(f"🔌 Worker {worker.pid}: Fechou conexão herdada do pai")
            except Exception as e:
                server.log.info(f"⚠️ Worker {worker.pid}: Sem conexão do pai para fechar ({e})")

            # Criar NOVA conexão para este worker (fork-safe)
            await transaction_db.connect()
            server.log.info(f"✅ Worker {worker.pid}: Reconectado ao banco com sucesso")

        except Exception as e:
            server.log.error(f"❌ Worker {worker.pid}: Erro ao reconectar ao banco: {e}")
            raise

    # Executar reconexão de forma síncrona no contexto do worker
    try:
        # Criar novo event loop para este worker
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(reconnect_db())
        loop.close()
        server.log.info(f"🎉 Worker {worker.pid}: Pronto para processar requests")
    except Exception as e:
        server.log.error(f"💥 Worker {worker.pid}: FALHA CRÍTICA na reconexão: {e}")
        raise

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("🔄 Forking new master process")
