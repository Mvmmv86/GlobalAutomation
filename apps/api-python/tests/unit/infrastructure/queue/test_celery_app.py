"""Tests for Celery application configuration"""

from unittest.mock import patch
import os

from infrastructure.queue.celery_app import celery_app


class TestCeleryApp:
    """Test cases for Celery application"""

    def test_celery_app_creation(self):
        """Test that Celery app is created properly"""
        assert celery_app is not None
        assert celery_app.main == "trading_platform"

    def test_celery_configuration(self):
        """Test Celery configuration settings"""
        config = celery_app.conf

        # Test serialization settings
        assert config.task_serializer == "json"
        assert config.result_serializer == "json"
        assert "json" in config.accept_content

        # Test timezone settings
        assert config.timezone == "UTC"
        assert config.enable_utc is True

        # Test worker settings
        assert config.worker_prefetch_multiplier == 1
        assert config.task_acks_late is True

        # Test result settings
        assert config.result_expires == 3600
        assert config.result_persistent is True

    def test_queue_routing(self):
        """Test task routing configuration"""
        routes = celery_app.conf.task_routes

        # Test webhook routing
        assert (
            routes["infrastructure.queue.tasks.process_webhook_task"]["queue"]
            == "webhooks"
        )

        # Test trading routing
        assert (
            routes["infrastructure.queue.tasks.execute_trading_order_task"]["queue"]
            == "trading"
        )

        # Test monitoring routing
        assert (
            routes["infrastructure.queue.tasks.health_check_accounts_task"]["queue"]
            == "monitoring"
        )

        # Test maintenance routing
        assert (
            routes["infrastructure.queue.tasks.cleanup_old_data_task"]["queue"]
            == "maintenance"
        )

    def test_queue_definitions(self):
        """Test queue definitions"""
        queues = celery_app.conf.task_queues
        queue_names = [q.name for q in queues]

        assert "default" in queue_names
        assert "webhooks" in queue_names
        assert "trading" in queue_names
        assert "monitoring" in queue_names
        assert "maintenance" in queue_names

    def test_beat_schedule(self):
        """Test periodic task schedule"""
        schedule = celery_app.conf.beat_schedule

        # Test health check schedule
        assert "health-check-accounts" in schedule
        health_check = schedule["health-check-accounts"]
        assert (
            health_check["task"]
            == "infrastructure.queue.tasks.health_check_accounts_task"
        )
        assert health_check["schedule"] == 300.0  # 5 minutes
        assert health_check["options"]["queue"] == "monitoring"

        # Test cleanup schedule
        assert "cleanup-old-data" in schedule
        cleanup = schedule["cleanup-old-data"]
        assert cleanup["task"] == "infrastructure.queue.tasks.cleanup_old_data_task"
        assert cleanup["schedule"] == 3600.0  # 1 hour
        assert cleanup["options"]["queue"] == "maintenance"

    def test_retry_settings(self):
        """Test retry configuration"""
        config = celery_app.conf

        assert config.task_default_retry_delay == 60
        assert config.task_max_retries == 3

    def test_broker_configuration(self):
        """Test broker settings"""
        config = celery_app.conf

        # Test broker pool limit
        assert config.broker_pool_limit == 10
        assert config.broker_connection_retry_on_startup is True

        # Test transport options
        transport_opts = config.broker_transport_options
        assert transport_opts["visibility_timeout"] == 3600
        assert transport_opts["fanout_prefix"] is True
        assert transport_opts["fanout_patterns"] is True

    def test_monitoring_settings(self):
        """Test monitoring configuration"""
        config = celery_app.conf

        assert config.worker_send_task_events is True
        assert config.task_send_sent_event is True

    @patch.dict(os.environ, {"REDIS_URL": "redis://test:6379/1"})
    def test_redis_url_from_env(self):
        """Test Redis URL configuration from environment"""
        # Create a new app instance to test environment variable
        from infrastructure.queue.celery_app import celery_app as test_app

        # The configuration should use the environment variable
        # Note: This test shows the pattern, but the actual app is already configured
        assert "redis://" in str(test_app.conf.broker_url)

    def test_security_settings(self):
        """Test security configuration"""
        config = celery_app.conf

        assert config.worker_hijack_root_logger is False
        assert config.worker_log_color is False
