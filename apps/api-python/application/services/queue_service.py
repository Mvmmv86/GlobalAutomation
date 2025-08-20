"""Queue service for managing background tasks"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from celery.result import AsyncResult
from celery import states

from infrastructure.queue.celery_app import celery_app
from infrastructure.queue.tasks import (
    process_webhook_task,
    execute_trading_order_task,
    health_check_accounts_task,
    cleanup_old_data_task,
    test_task,
)

logger = logging.getLogger(__name__)


class QueueService:
    """Service for managing background task queues"""

    def __init__(self):
        self.celery = celery_app

    async def enqueue_webhook_processing(
        self,
        webhook_path: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        signature: Optional[str] = None,
        priority: int = 5,
    ) -> str:
        """Enqueue webhook processing task"""

        try:
            task = process_webhook_task.apply_async(
                args=[webhook_path, payload, headers, signature],
                queue="webhooks",
                priority=priority,
            )

            logger.info(f"Webhook processing enqueued: {task.id}")
            return task.id

        except Exception as e:
            logger.error(f"Failed to enqueue webhook processing: {str(e)}")
            raise

    async def enqueue_trading_order(
        self,
        delivery_id: str,
        webhook_data: Dict[str, Any],
        user_id: Optional[str] = None,
        priority: int = 8,  # Higher priority for trading
    ) -> str:
        """Enqueue trading order execution task"""

        try:
            task = execute_trading_order_task.apply_async(
                args=[delivery_id, webhook_data, user_id],
                queue="trading",
                priority=priority,
            )

            logger.info(f"Trading order enqueued: {task.id}")
            return task.id

        except Exception as e:
            logger.error(f"Failed to enqueue trading order: {str(e)}")
            raise

    async def trigger_health_check(self) -> str:
        """Trigger immediate health check for all accounts"""

        try:
            task = health_check_accounts_task.apply_async(queue="monitoring")

            logger.info(f"Health check triggered: {task.id}")
            return task.id

        except Exception as e:
            logger.error(f"Failed to trigger health check: {str(e)}")
            raise

    async def trigger_cleanup(self, days_old: int = 30) -> str:
        """Trigger data cleanup task"""

        try:
            task = cleanup_old_data_task.apply_async(
                args=[days_old], queue="maintenance"
            )

            logger.info(f"Cleanup triggered: {task.id}")
            return task.id

        except Exception as e:
            logger.error(f"Failed to trigger cleanup: {str(e)}")
            raise

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific task"""

        try:
            result = AsyncResult(task_id, app=self.celery)

            status_info = {
                "task_id": task_id,
                "status": result.status,
                "result": result.result if result.ready() else None,
                "traceback": result.traceback if result.failed() else None,
                "date_done": result.date_done.isoformat() if result.date_done else None,
            }

            # Add additional info based on status
            if result.status == states.PENDING:
                status_info["info"] = "Task is waiting to be processed"
            elif result.status == states.STARTED:
                status_info["info"] = "Task has been started"
            elif result.status == states.SUCCESS:
                status_info["info"] = "Task completed successfully"
            elif result.status == states.FAILURE:
                status_info["info"] = "Task failed"
                status_info["error"] = (
                    str(result.result) if result.result else "Unknown error"
                )
            elif result.status == states.RETRY:
                status_info["info"] = "Task is being retried"
            elif result.status == states.REVOKED:
                status_info["info"] = "Task was revoked"

            return status_info

        except Exception as e:
            logger.error(f"Failed to get task status: {str(e)}")
            return {"task_id": task_id, "status": "ERROR", "error": str(e)}

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about all queues"""

        try:
            inspect = self.celery.control.inspect()

            # Get active tasks
            active = inspect.active() or {}

            # Get scheduled tasks
            scheduled = inspect.scheduled() or {}

            # Get reserved tasks
            reserved = inspect.reserved() or {}

            # Get registered tasks
            registered = inspect.registered() or {}

            # Get worker stats
            stats = inspect.stats() or {}

            # Calculate totals
            total_active = sum(len(tasks) for tasks in active.values())
            total_scheduled = sum(len(tasks) for tasks in scheduled.values())
            total_reserved = sum(len(tasks) for tasks in reserved.values())

            return {
                "queues": {
                    "active_tasks": total_active,
                    "scheduled_tasks": total_scheduled,
                    "reserved_tasks": total_reserved,
                },
                "workers": {
                    "count": len(stats),
                    "names": list(stats.keys()) if stats else [],
                },
                "task_types": {
                    "registered_count": len(
                        set().union(*(registered.values() if registered else []))
                    ),
                    "registered_tasks": list(
                        set().union(*(registered.values() if registered else []))
                    ),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get queue stats: {str(e)}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def get_worker_status(self) -> Dict[str, Any]:
        """Get status of Celery workers"""

        try:
            inspect = self.celery.control.inspect()

            # Ping workers to see which are online
            ping_result = inspect.ping() or {}

            # Get worker stats
            stats = inspect.stats() or {}

            workers = {}
            for worker_name in ping_result.keys():
                worker_info = {
                    "online": ping_result.get(worker_name, {}).get("ok") == "pong",
                    "stats": stats.get(worker_name, {}),
                }

                # Add queue information
                if worker_name in stats:
                    worker_stats = stats[worker_name]
                    worker_info["queues"] = worker_stats.get("pool", {}).get(
                        "max-concurrency", 0
                    )
                    worker_info["processed_tasks"] = worker_stats.get("total", {})

                workers[worker_name] = worker_info

            return {
                "workers": workers,
                "total_workers": len(workers),
                "online_workers": sum(
                    1 for w in workers.values() if w.get("online", False)
                ),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get worker status: {str(e)}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running or pending task"""

        try:
            self.celery.control.revoke(task_id, terminate=True)
            logger.info(f"Task cancelled: {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {str(e)}")
            return False

    def purge_queue(self, queue_name: str) -> int:
        """Purge all pending tasks from a specific queue"""

        try:
            # This is a dangerous operation, should be used carefully
            result = self.celery.control.purge()
            logger.warning(f"Queue {queue_name} purged")
            return result

        except Exception as e:
            logger.error(f"Failed to purge queue {queue_name}: {str(e)}")
            return 0

    async def test_queue_connection(self) -> Dict[str, Any]:
        """Test queue connection and basic functionality"""

        try:
            # Send a test task
            task = test_task.apply_async(
                args=["Queue connection test"], queue="default"
            )

            # Wait a bit for the task to complete
            import asyncio

            await asyncio.sleep(2)

            # Check result
            result = self.get_task_status(task.id)

            return {
                "connection": "ok",
                "test_task_id": task.id,
                "test_result": result,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Queue connection test failed: {str(e)}")
            return {
                "connection": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def get_task_history(
        self, limit: int = 100, offset: int = 0, status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get task execution history (requires result backend)"""

        try:
            # This would require a more sophisticated result backend
            # For now, return basic info
            inspect = self.celery.control.inspect()

            # Get recent active and reserved tasks
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}

            all_tasks = []

            # Add active tasks
            for worker, tasks in active.items():
                for task in tasks:
                    all_tasks.append(
                        {
                            "task_id": task.get("id"),
                            "name": task.get("name"),
                            "args": task.get("args", []),
                            "kwargs": task.get("kwargs", {}),
                            "status": "ACTIVE",
                            "worker": worker,
                            "timestamp": task.get("time_start"),
                        }
                    )

            # Add reserved tasks
            for worker, tasks in reserved.items():
                for task in tasks:
                    all_tasks.append(
                        {
                            "task_id": task.get("id"),
                            "name": task.get("name"),
                            "args": task.get("args", []),
                            "kwargs": task.get("kwargs", {}),
                            "status": "RESERVED",
                            "worker": worker,
                            "timestamp": None,
                        }
                    )

            # Apply filters and pagination
            if status_filter:
                all_tasks = [
                    t for t in all_tasks if t["status"] == status_filter.upper()
                ]

            # Sort by timestamp (newest first)
            all_tasks.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

            return all_tasks[offset : offset + limit]

        except Exception as e:
            logger.error(f"Failed to get task history: {str(e)}")
            return []
