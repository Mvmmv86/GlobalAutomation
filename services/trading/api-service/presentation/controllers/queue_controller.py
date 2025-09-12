"""Queue management controller"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel
from uuid import UUID

from application.services.queue_service import QueueService
from presentation.middleware.auth import get_current_user_id
from infrastructure.config.settings import get_settings


class QueueStatsResponse(BaseModel):
    """Queue statistics response"""

    queues: Dict[str, int]
    workers: Dict[str, Any]
    task_types: Dict[str, Any]
    timestamp: str


class TaskStatusResponse(BaseModel):
    """Task status response"""

    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    info: Optional[str] = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    date_done: Optional[str] = None


class WorkerStatusResponse(BaseModel):
    """Worker status response"""

    workers: Dict[str, Any]
    total_workers: int
    online_workers: int
    timestamp: str


class TaskHistoryResponse(BaseModel):
    """Task history response"""

    tasks: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int


class QueueTestResponse(BaseModel):
    """Queue connection test response"""

    connection: str
    test_task_id: Optional[str] = None
    test_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str


def get_queue_service() -> QueueService:
    """Get QueueService instance"""
    return QueueService()


def create_queue_router() -> APIRouter:
    """Create queue management router"""

    router = APIRouter(prefix="/admin/queue", tags=["Queue Management"])

    @router.get("/stats", response_model=QueueStatsResponse)
    async def get_queue_statistics(
        current_user_id: UUID = Depends(get_current_user_id),
        queue_service: QueueService = Depends(get_queue_service),
    ):
        """
        Get queue statistics

        - **Authentication required**
        - **Admin access required**
        - **Returns comprehensive queue metrics**
        """
        try:
            stats = queue_service.get_queue_stats()

            return QueueStatsResponse(
                queues=stats.get("queues", {}),
                workers=stats.get("workers", {}),
                task_types=stats.get("task_types", {}),
                timestamp=stats.get("timestamp", ""),
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get queue stats: {str(e)}",
            )

    @router.get("/workers", response_model=WorkerStatusResponse)
    async def get_worker_status(
        current_user_id: UUID = Depends(get_current_user_id),
        queue_service: QueueService = Depends(get_queue_service),
    ):
        """
        Get worker status

        - **Authentication required**
        - **Admin access required**
        - **Returns worker health and metrics**
        """
        try:
            status_info = queue_service.get_worker_status()

            return WorkerStatusResponse(
                workers=status_info.get("workers", {}),
                total_workers=status_info.get("total_workers", 0),
                online_workers=status_info.get("online_workers", 0),
                timestamp=status_info.get("timestamp", ""),
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get worker status: {str(e)}",
            )

    @router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
    async def get_task_status(
        task_id: str,
        current_user_id: UUID = Depends(get_current_user_id),
        queue_service: QueueService = Depends(get_queue_service),
    ):
        """
        Get status of a specific task

        - **Authentication required**
        - **Returns detailed task information**
        """
        try:
            task_status = queue_service.get_task_status(task_id)

            return TaskStatusResponse(
                task_id=task_status.get("task_id", task_id),
                status=task_status.get("status", "UNKNOWN"),
                result=task_status.get("result"),
                info=task_status.get("info"),
                error=task_status.get("error"),
                traceback=task_status.get("traceback"),
                date_done=task_status.get("date_done"),
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get task status: {str(e)}",
            )

    @router.delete("/tasks/{task_id}")
    async def cancel_task(
        task_id: str,
        current_user_id: UUID = Depends(get_current_user_id),
        queue_service: QueueService = Depends(get_queue_service),
    ):
        """
        Cancel a running or pending task

        - **Authentication required**
        - **Admin access required**
        - **Terminates task execution**
        """
        try:
            success = queue_service.cancel_task(task_id)

            if success:
                return {"message": f"Task {task_id} cancelled successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to cancel task {task_id}",
                )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error cancelling task: {str(e)}",
            )

    @router.get("/tasks", response_model=TaskHistoryResponse)
    async def get_task_history(
        limit: int = Query(50, ge=1, le=500, description="Number of tasks to return"),
        offset: int = Query(0, ge=0, description="Number of tasks to skip"),
        status_filter: Optional[str] = Query(None, description="Filter by task status"),
        current_user_id: UUID = Depends(get_current_user_id),
        queue_service: QueueService = Depends(get_queue_service),
    ):
        """
        Get task execution history

        - **Authentication required**
        - **Admin access required**
        - **Supports pagination and filtering**
        """
        try:
            tasks = queue_service.get_task_history(
                limit=limit, offset=offset, status_filter=status_filter
            )

            return TaskHistoryResponse(
                tasks=tasks, total=len(tasks), limit=limit, offset=offset
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get task history: {str(e)}",
            )

    @router.post("/health-check")
    async def trigger_health_check(
        current_user_id: UUID = Depends(get_current_user_id),
        queue_service: QueueService = Depends(get_queue_service),
    ):
        """
        Trigger immediate health check for all exchange accounts

        - **Authentication required**
        - **Admin access required**
        - **Enqueues health check task**
        """
        try:
            task_id = await queue_service.trigger_health_check()

            return {
                "message": "Health check triggered successfully",
                "task_id": task_id,
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to trigger health check: {str(e)}",
            )

    @router.post("/cleanup")
    async def trigger_cleanup(
        days_old: int = Query(
            30, ge=1, le=365, description="Clean data older than X days"
        ),
        current_user_id: UUID = Depends(get_current_user_id),
        queue_service: QueueService = Depends(get_queue_service),
    ):
        """
        Trigger data cleanup task

        - **Authentication required**
        - **Admin access required**
        - **Cleans old webhook deliveries and orders**
        """
        try:
            task_id = await queue_service.trigger_cleanup(days_old)

            return {
                "message": f"Cleanup triggered for data older than {days_old} days",
                "task_id": task_id,
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to trigger cleanup: {str(e)}",
            )

    @router.post("/test", response_model=QueueTestResponse)
    async def test_queue_connection(
        current_user_id: UUID = Depends(get_current_user_id),
        queue_service: QueueService = Depends(get_queue_service),
    ):
        """
        Test queue connection and functionality

        - **Authentication required**
        - **Admin access required**
        - **Sends test task and checks result**
        """
        try:
            result = await queue_service.test_queue_connection()

            return QueueTestResponse(
                connection=result.get("connection", "unknown"),
                test_task_id=result.get("test_task_id"),
                test_result=result.get("test_result"),
                error=result.get("error"),
                timestamp=result.get("timestamp", ""),
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Queue test failed: {str(e)}",
            )

    @router.delete("/queues/{queue_name}/purge")
    async def purge_queue(
        queue_name: str,
        current_user_id: UUID = Depends(get_current_user_id),
        queue_service: QueueService = Depends(get_queue_service),
    ):
        """
        Purge all pending tasks from a queue

        - **Authentication required**
        - **Admin access required**
        - **⚠️ DANGEROUS: Removes all pending tasks**
        """
        try:
            # Only allow purging in development/test environments
            settings = get_settings()
            if settings.environment == "production":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Queue purging is not allowed in production",
                )

            purged_count = queue_service.purge_queue(queue_name)

            return {
                "message": f"Queue {queue_name} purged successfully",
                "purged_tasks": purged_count,
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to purge queue: {str(e)}",
            )

    return router
