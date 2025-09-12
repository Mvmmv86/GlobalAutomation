"""Celery application configuration"""

import os
from celery import Celery
from kombu import Queue

# Create Celery app
celery_app = Celery("trading_platform")

# Configuration
celery_app.conf.update(
    # Broker settings
    broker_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    result_backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    # Result settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    # Routing
    task_routes={
        "infrastructure.queue.tasks.process_webhook_task": {"queue": "webhooks"},
        "infrastructure.queue.tasks.execute_trading_order_task": {"queue": "trading"},
        "infrastructure.queue.tasks.health_check_accounts_task": {
            "queue": "monitoring"
        },
        "infrastructure.queue.tasks.cleanup_old_data_task": {"queue": "maintenance"},
    },
    # Queue definitions
    task_default_queue="default",
    task_queues=(
        Queue("default", routing_key="default"),
        Queue("webhooks", routing_key="webhooks"),
        Queue("trading", routing_key="trading"),
        Queue("monitoring", routing_key="monitoring"),
        Queue("maintenance", routing_key="maintenance"),
    ),
    # Retry settings
    task_default_retry_delay=60,  # 60 seconds
    task_max_retries=3,
    # Beat settings (for periodic tasks)
    beat_schedule={
        "health-check-accounts": {
            "task": "infrastructure.queue.tasks.health_check_accounts_task",
            "schedule": 300.0,  # Every 5 minutes
            "options": {"queue": "monitoring"},
        },
        "cleanup-old-data": {
            "task": "infrastructure.queue.tasks.cleanup_old_data_task",
            "schedule": 3600.0,  # Every hour
            "options": {"queue": "maintenance"},
        },
    },
    # Security
    worker_hijack_root_logger=False,
    worker_log_color=False,
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    # Performance
    broker_pool_limit=10,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 3600,
        "fanout_prefix": True,
        "fanout_patterns": True,
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["infrastructure.queue.tasks"])

if __name__ == "__main__":
    celery_app.start()
