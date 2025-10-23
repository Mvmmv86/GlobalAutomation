"""
Gunicorn configuration for FastAPI on Digital Ocean App Platform
Optimized for performance and concurrent request handling
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
    """Called just after a worker has been forked."""
    server.log.info(f"🔧 Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("🔄 Forking new master process")
