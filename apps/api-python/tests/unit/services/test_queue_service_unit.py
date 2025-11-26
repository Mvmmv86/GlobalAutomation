"""Unit tests for QueueService without external dependencies"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from celery import states


class TestQueueServiceUnit:
    """Unit tests for QueueService"""

    @pytest.fixture
    def mock_celery_app(self):
        """Mock Celery app"""
        mock_app = MagicMock()
        mock_app.control.inspect.return_value = MagicMock()
        mock_app.control.revoke = MagicMock()
        mock_app.control.purge.return_value = 5
        return mock_app

    @pytest.fixture
    def queue_service(self, mock_celery_app):
        """QueueService with mocked dependencies"""
        with patch("application.services.queue_service.celery_app", mock_celery_app):
            from application.services.queue_service import QueueService

            return QueueService()

    @pytest.mark.asyncio
    async def test_enqueue_webhook_processing(self, queue_service):
        """Test enqueuing webhook processing"""
        with patch(
            "application.services.queue_service.process_webhook_task"
        ) as mock_task:
            mock_task.apply_async.return_value.id = "webhook-task-123"

            task_id = await queue_service.enqueue_webhook_processing(
                webhook_path="test-webhook",
                payload={"ticker": "BTCUSDT"},
                headers={"content-type": "application/json"},
                signature="test-sig",
                priority=5,
            )

            assert task_id == "webhook-task-123"
            mock_task.apply_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_trading_order(self, queue_service):
        """Test enqueuing trading order"""
        with patch(
            "application.services.queue_service.execute_trading_order_task"
        ) as mock_task:
            mock_task.apply_async.return_value.id = "trading-task-123"

            task_id = await queue_service.enqueue_trading_order(
                delivery_id="delivery-123",
                webhook_data={"ticker": "BTCUSDT"},
                user_id="user-456",
            )

            assert task_id == "trading-task-123"
            mock_task.apply_async.assert_called_once()

    def test_get_task_status(self, queue_service):
        """Test getting task status"""
        mock_result = MagicMock()
        mock_result.status = states.SUCCESS
        mock_result.result = {"message": "completed"}
        mock_result.ready.return_value = True
        mock_result.failed.return_value = False
        mock_result.traceback = None
        mock_result.date_done = datetime.utcnow()

        with patch(
            "application.services.queue_service.AsyncResult", return_value=mock_result
        ):
            status = queue_service.get_task_status("test-task-123")

            assert status["task_id"] == "test-task-123"
            assert status["status"] == states.SUCCESS
            assert status["info"] == "Task completed successfully"

    def test_get_queue_stats(self, queue_service):
        """Test getting queue statistics"""
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = {"worker1": [{"id": "task1"}]}
        mock_inspect.scheduled.return_value = {"worker1": [{"id": "task2"}]}
        mock_inspect.reserved.return_value = {"worker1": [{"id": "task3"}]}
        mock_inspect.registered.return_value = {"worker1": ["task.type1"]}
        mock_inspect.stats.return_value = {"worker1": {"total": 100}}

        queue_service.celery.control.inspect.return_value = mock_inspect

        stats = queue_service.get_queue_stats()

        assert stats["queues"]["active_tasks"] == 1
        assert stats["queues"]["scheduled_tasks"] == 1
        assert stats["queues"]["reserved_tasks"] == 1
        assert stats["workers"]["count"] == 1

    def test_cancel_task(self, queue_service):
        """Test cancelling a task"""
        result = queue_service.cancel_task("task-to-cancel")

        assert result is True
        queue_service.celery.control.revoke.assert_called_once_with(
            "task-to-cancel", terminate=True
        )

    def test_purge_queue(self, queue_service):
        """Test purging a queue"""
        result = queue_service.purge_queue("test_queue")

        assert result == 5
        queue_service.celery.control.purge.assert_called_once()

    def test_get_worker_status(self, queue_service):
        """Test getting worker status"""
        mock_inspect = MagicMock()
        mock_inspect.ping.return_value = {"worker1": {"ok": "pong"}}
        mock_inspect.stats.return_value = {
            "worker1": {"pool": {"max-concurrency": 4}, "total": {"completed": 100}}
        }

        queue_service.celery.control.inspect.return_value = mock_inspect

        status = queue_service.get_worker_status()

        assert status["total_workers"] == 1
        assert status["online_workers"] == 1
        assert status["workers"]["worker1"]["online"] is True

    def test_get_task_history(self, queue_service):
        """Test getting task history"""
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = {
            "worker1": [{"id": "active-task", "name": "test.task"}]
        }
        mock_inspect.reserved.return_value = {
            "worker1": [{"id": "reserved-task", "name": "test.task2"}]
        }

        queue_service.celery.control.inspect.return_value = mock_inspect

        history = queue_service.get_task_history()

        assert len(history) == 2
        assert any(t["task_id"] == "active-task" for t in history)
        assert any(t["task_id"] == "reserved-task" for t in history)

    @pytest.mark.asyncio
    async def test_trigger_health_check(self, queue_service):
        """Test triggering health check"""
        with patch(
            "application.services.queue_service.health_check_accounts_task"
        ) as mock_task:
            mock_task.apply_async.return_value.id = "health-task-123"

            task_id = await queue_service.trigger_health_check()

            assert task_id == "health-task-123"
            mock_task.apply_async.assert_called_once_with(queue="monitoring")

    @pytest.mark.asyncio
    async def test_trigger_cleanup(self, queue_service):
        """Test triggering cleanup"""
        with patch(
            "application.services.queue_service.cleanup_old_data_task"
        ) as mock_task:
            mock_task.apply_async.return_value.id = "cleanup-task-123"

            task_id = await queue_service.trigger_cleanup(30)

            assert task_id == "cleanup-task-123"
            mock_task.apply_async.assert_called_once_with(
                args=[30], queue="maintenance"
            )

    def test_get_task_status_pending(self, queue_service):
        """Test getting status of pending task"""
        mock_result = MagicMock()
        mock_result.status = states.PENDING
        mock_result.ready.return_value = False
        mock_result.failed.return_value = False
        mock_result.result = None
        mock_result.traceback = None
        mock_result.date_done = None

        with patch(
            "application.services.queue_service.AsyncResult", return_value=mock_result
        ):
            status = queue_service.get_task_status("pending-task")

            assert status["status"] == states.PENDING
            assert status["info"] == "Task is waiting to be processed"

    def test_get_task_status_failed(self, queue_service):
        """Test getting status of failed task"""
        mock_result = MagicMock()
        mock_result.status = states.FAILURE
        mock_result.ready.return_value = True
        mock_result.failed.return_value = True
        mock_result.result = Exception("Task failed")
        mock_result.traceback = "Error traceback"
        mock_result.date_done = datetime.utcnow()

        with patch(
            "application.services.queue_service.AsyncResult", return_value=mock_result
        ):
            status = queue_service.get_task_status("failed-task")

            assert status["status"] == states.FAILURE
            assert status["info"] == "Task failed"
            assert "Task failed" in status["error"]

    def test_get_task_status_error(self, queue_service):
        """Test get_task_status when an error occurs"""
        with patch(
            "application.services.queue_service.AsyncResult",
            side_effect=Exception("Connection error"),
        ):
            status = queue_service.get_task_status("error-task")

            assert status["status"] == "ERROR"
            assert "Connection error" in status["error"]

    def test_cancel_task_failure(self, queue_service):
        """Test task cancellation failure"""
        queue_service.celery.control.revoke.side_effect = Exception("Control error")

        result = queue_service.cancel_task("task-to-cancel")

        assert result is False

    def test_get_queue_stats_error(self, queue_service):
        """Test get_queue_stats when an error occurs"""
        queue_service.celery.control.inspect.side_effect = Exception(
            "Inspection failed"
        )

        stats = queue_service.get_queue_stats()

        assert "error" in stats
        assert "Inspection failed" in stats["error"]

    def test_get_worker_status_error(self, queue_service):
        """Test get_worker_status when an error occurs"""
        queue_service.celery.control.inspect.side_effect = Exception(
            "Worker status failed"
        )

        status = queue_service.get_worker_status()

        assert "error" in status
        assert "Worker status failed" in status["error"]
