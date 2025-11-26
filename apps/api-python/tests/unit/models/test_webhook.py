"""Unit tests for Webhook and WebhookDelivery models"""

from datetime import datetime, timedelta
from infrastructure.database.models.webhook import (
    Webhook,
    WebhookDelivery,
    WebhookStatus,
    WebhookDeliveryStatus,
)


class TestWebhook:
    """Test Webhook model business logic"""

    def test_webhook_creation(self):
        """Test webhook creation with basic fields"""
        webhook = Webhook(
            name="Test TradingView Webhook",
            url_path="/webhooks/tv-123",
            secret="secret123",
            user_id="user-123",
        )

        assert webhook.name == "Test TradingView Webhook"
        assert webhook.url_path == "/webhooks/tv-123"
        assert webhook.status == WebhookStatus.ACTIVE
        assert webhook.is_public is False
        assert webhook.total_deliveries == 0
        assert webhook.successful_deliveries == 0
        assert webhook.failed_deliveries == 0
        assert webhook.consecutive_errors == 0

    def test_activate_webhook(self):
        """Test webhook activation"""
        webhook = Webhook(
            name="Test Webhook",
            url_path="/webhooks/test",
            secret="secret123",
            user_id="user-123",
            status=WebhookStatus.PAUSED,
        )

        webhook.activate()
        assert webhook.status == WebhookStatus.ACTIVE
        assert webhook.consecutive_errors == 0

    def test_pause_webhook(self):
        """Test webhook pausing"""
        webhook = Webhook(
            name="Test Webhook",
            url_path="/webhooks/test",
            secret="secret123",
            user_id="user-123",
        )

        webhook.pause()
        assert webhook.status == WebhookStatus.PAUSED

    def test_disable_webhook(self):
        """Test webhook disabling"""
        webhook = Webhook(
            name="Test Webhook",
            url_path="/webhooks/test",
            secret="secret123",
            user_id="user-123",
        )

        webhook.disable()
        assert webhook.status == WebhookStatus.DISABLED

    def test_mark_error(self):
        """Test marking webhook as error"""
        webhook = Webhook(
            name="Test Webhook",
            url_path="/webhooks/test",
            secret="secret123",
            user_id="user-123",
        )

        webhook.mark_error()
        assert webhook.status == WebhookStatus.ERROR

    def test_increment_delivery_stats_success(self):
        """Test incrementing delivery stats for successful delivery"""
        webhook = Webhook(
            name="Test Webhook",
            url_path="/webhooks/test",
            secret="secret123",
            user_id="user-123",
        )

        webhook.increment_delivery_stats(success=True)

        assert webhook.total_deliveries == 1
        assert webhook.successful_deliveries == 1
        assert webhook.failed_deliveries == 0
        assert webhook.consecutive_errors == 0
        assert webhook.last_delivery_at is not None
        assert webhook.last_success_at is not None

    def test_increment_delivery_stats_failure(self):
        """Test incrementing delivery stats for failed delivery"""
        webhook = Webhook(
            name="Test Webhook",
            url_path="/webhooks/test",
            secret="secret123",
            user_id="user-123",
        )

        webhook.increment_delivery_stats(success=False)

        assert webhook.total_deliveries == 1
        assert webhook.successful_deliveries == 0
        assert webhook.failed_deliveries == 1
        assert webhook.consecutive_errors == 1
        assert webhook.last_delivery_at is not None
        assert webhook.last_success_at is None

    def test_auto_pause_on_errors(self):
        """Test auto-pause on error threshold"""
        webhook = Webhook(
            name="Test Webhook",
            url_path="/webhooks/test",
            secret="secret123",
            user_id="user-123",
            auto_pause_on_errors=True,
            error_threshold=3,
        )

        # First two failures shouldn't pause
        webhook.increment_delivery_stats(success=False)
        webhook.increment_delivery_stats(success=False)
        assert webhook.status == WebhookStatus.ACTIVE
        assert webhook.consecutive_errors == 2

        # Third failure should trigger auto-pause
        webhook.increment_delivery_stats(success=False)
        assert webhook.status == WebhookStatus.PAUSED
        assert webhook.consecutive_errors == 3

    def test_get_success_rate(self):
        """Test success rate calculation"""
        webhook = Webhook(
            name="Test Webhook",
            url_path="/webhooks/test",
            secret="secret123",
            user_id="user-123",
        )

        # No deliveries yet
        assert webhook.get_success_rate() == 0.0

        # Add some deliveries
        webhook.increment_delivery_stats(success=True)  # 1/1 = 100%
        assert webhook.get_success_rate() == 100.0

        webhook.increment_delivery_stats(success=False)  # 1/2 = 50%
        assert webhook.get_success_rate() == 50.0

        webhook.increment_delivery_stats(success=True)  # 2/3 = 66.67%
        assert round(webhook.get_success_rate(), 2) == 66.67

    def test_is_active(self):
        """Test active status checking"""
        webhook = Webhook(
            name="Test Webhook",
            url_path="/webhooks/test",
            secret="secret123",
            user_id="user-123",
        )

        # Initially active
        assert webhook.is_active() is True

        # Pause
        webhook.pause()
        assert webhook.is_active() is False

        # Reactivate
        webhook.activate()
        assert webhook.is_active() is True

    def test_can_receive_deliveries(self):
        """Test delivery reception capability"""
        webhook = Webhook(
            name="Test Webhook",
            url_path="/webhooks/test",
            secret="secret123",
            user_id="user-123",
        )

        # Active status
        assert webhook.can_receive_deliveries() is True

        # Error status (still can receive to retry)
        webhook.mark_error()
        assert webhook.can_receive_deliveries() is True

        # Paused status
        webhook.pause()
        assert webhook.can_receive_deliveries() is False

        # Disabled status
        webhook.disable()
        assert webhook.can_receive_deliveries() is False


class TestWebhookDelivery:
    """Test WebhookDelivery model business logic"""

    def test_webhook_delivery_creation(self):
        """Test webhook delivery creation"""
        delivery = WebhookDelivery(
            payload={"action": "buy", "symbol": "BTCUSDT"},
            headers={"content-type": "application/json"},
            webhook_id="webhook-123",
        )

        assert delivery.status == WebhookDeliveryStatus.PENDING
        assert delivery.payload == {"action": "buy", "symbol": "BTCUSDT"}
        assert delivery.retry_count == 0
        assert delivery.orders_created == 0
        assert delivery.orders_executed == 0
        assert delivery.orders_failed == 0

    def test_mark_processing(self):
        """Test marking delivery as processing"""
        delivery = WebhookDelivery(
            payload={"action": "buy"}, headers={}, webhook_id="webhook-123"
        )

        delivery.mark_processing()

        assert delivery.status == WebhookDeliveryStatus.PROCESSING
        assert delivery.processing_started_at is not None

    def test_mark_success(self):
        """Test marking delivery as successful"""
        delivery = WebhookDelivery(
            payload={"action": "buy"}, headers={}, webhook_id="webhook-123"
        )

        delivery.mark_processing()
        delivery.mark_success()

        assert delivery.status == WebhookDeliveryStatus.SUCCESS
        assert delivery.processing_completed_at is not None
        assert delivery.processing_duration_ms is not None
        assert delivery.processing_duration_ms >= 0

    def test_mark_failed(self):
        """Test marking delivery as failed"""
        delivery = WebhookDelivery(
            payload={"action": "buy"}, headers={}, webhook_id="webhook-123"
        )

        error_msg = "Invalid payload format"
        error_details = {"field": "action", "issue": "missing required field"}

        delivery.mark_processing()
        delivery.mark_failed(error_msg, error_details)

        assert delivery.status == WebhookDeliveryStatus.FAILED
        assert delivery.processing_completed_at is not None
        assert delivery.error_message == error_msg
        assert delivery.error_details == error_details
        assert delivery.processing_duration_ms is not None

    def test_schedule_retry(self):
        """Test scheduling delivery for retry"""
        delivery = WebhookDelivery(
            payload={"action": "buy"}, headers={}, webhook_id="webhook-123"
        )

        delay_seconds = 60
        delivery.schedule_retry(delay_seconds)

        assert delivery.status == WebhookDeliveryStatus.RETRYING
        assert delivery.retry_count == 1
        assert delivery.next_retry_at is not None

        # Schedule another retry
        delivery.schedule_retry(delay_seconds)
        assert delivery.retry_count == 2

    def test_set_validation_results(self):
        """Test setting validation results"""
        delivery = WebhookDelivery(
            payload={"action": "buy"}, headers={}, webhook_id="webhook-123"
        )

        delivery.set_validation_results(
            hmac_valid=True, ip_allowed=True, headers_valid=False, payload_valid=True
        )

        assert delivery.hmac_valid is True
        assert delivery.ip_allowed is True
        assert delivery.headers_valid is False
        assert delivery.payload_valid is True

    def test_update_order_stats(self):
        """Test updating order statistics"""
        delivery = WebhookDelivery(
            payload={"action": "buy"}, headers={}, webhook_id="webhook-123"
        )

        delivery.update_order_stats(created=3, executed=2, failed=1)

        assert delivery.orders_created == 3
        assert delivery.orders_executed == 2
        assert delivery.orders_failed == 1

    def test_is_ready_for_retry(self):
        """Test retry readiness checking"""
        delivery = WebhookDelivery(
            payload={"action": "buy"}, headers={}, webhook_id="webhook-123"
        )

        # Not in retrying status
        assert delivery.is_ready_for_retry() is False

        # Schedule retry in future
        future_time = datetime.now() + timedelta(minutes=5)
        delivery.status = WebhookDeliveryStatus.RETRYING
        delivery.next_retry_at = future_time
        assert delivery.is_ready_for_retry() is False

        # Schedule retry in past
        past_time = datetime.now() - timedelta(minutes=5)
        delivery.next_retry_at = past_time
        assert delivery.is_ready_for_retry() is True
