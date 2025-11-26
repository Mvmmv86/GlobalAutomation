"""Tests for TradingViewService"""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from application.services.tradingview_service import TradingViewService
from infrastructure.database.models.webhook import (
    Webhook,
    WebhookDelivery,
    WebhookDeliveryStatus,
)
from presentation.schemas.tradingview import (
    TradingViewOrderWebhook,
    TradingViewPositionWebhook,
    TradingViewSignalWebhook,
    WebhookValidationError,
)


class TestTradingViewService:
    """Test cases for TradingViewService"""

    @pytest.fixture
    def mock_webhook_repo(self):
        """Mock WebhookRepository"""
        return AsyncMock()

    @pytest.fixture
    def mock_webhook_delivery_repo(self):
        """Mock WebhookDeliveryRepository"""
        return AsyncMock()

    @pytest.fixture
    def mock_user_repo(self):
        """Mock UserRepository"""
        return AsyncMock()

    @pytest.fixture
    def mock_order_repo(self):
        """Mock OrderRepository"""
        return AsyncMock()

    @pytest.fixture
    def tradingview_service(
        self,
        mock_webhook_repo,
        mock_webhook_delivery_repo,
        mock_user_repo,
        mock_order_repo,
    ):
        """TradingViewService instance with mocked repositories"""
        return TradingViewService(
            mock_webhook_repo,
            mock_webhook_delivery_repo,
            mock_user_repo,
            mock_order_repo,
        )

    @pytest.fixture
    def sample_webhook(self):
        """Sample webhook for testing"""
        return Webhook(
            id=str(uuid4()),
            url_path="test-webhook",
            name="Test Webhook",
            secret="test-secret",
            is_active=True,
            user_id=str(uuid4()),
        )

    @pytest.fixture
    def sample_delivery(self):
        """Sample webhook delivery for testing"""
        return WebhookDelivery(
            id=str(uuid4()),
            webhook_id=str(uuid4()),
            payload={"action": "buy", "ticker": "BTCUSDT"},
            headers={"content-type": "application/json"},
            status=WebhookDeliveryStatus.PENDING,
        )

    def test_verify_hmac_signature_sha256_valid(self, tradingview_service):
        """Test HMAC SHA256 signature verification with valid signature"""
        payload = '{"action":"buy","ticker":"BTCUSDT"}'
        secret = "test-secret"

        # Calculate expected signature
        import hmac
        import hashlib

        expected_signature = hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Test with sha256= prefix
        signature = f"sha256={expected_signature}"
        assert (
            tradingview_service.verify_hmac_signature(payload, signature, secret)
            is True
        )

        # Test without prefix
        assert (
            tradingview_service.verify_hmac_signature(
                payload, expected_signature, secret
            )
            is True
        )

    def test_verify_hmac_signature_sha1_valid(self, tradingview_service):
        """Test HMAC SHA1 signature verification with valid signature"""
        payload = '{"action":"buy","ticker":"BTCUSDT"}'
        secret = "test-secret"

        # Calculate expected SHA1 signature
        import hmac
        import hashlib

        expected_signature = hmac.new(
            secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1
        ).hexdigest()

        signature = f"sha1={expected_signature}"
        assert (
            tradingview_service.verify_hmac_signature(payload, signature, secret)
            is True
        )

    def test_verify_hmac_signature_invalid(self, tradingview_service):
        """Test HMAC signature verification with invalid signature"""
        payload = '{"action":"buy","ticker":"BTCUSDT"}'
        secret = "test-secret"
        invalid_signature = "sha256=invalid_signature"

        assert (
            tradingview_service.verify_hmac_signature(
                payload, invalid_signature, secret
            )
            is False
        )

    def test_verify_hmac_signature_no_secret(self, tradingview_service):
        """Test HMAC signature verification with no secret"""
        payload = '{"action":"buy","ticker":"BTCUSDT"}'
        signature = "sha256=some_signature"

        assert (
            tradingview_service.verify_hmac_signature(payload, signature, "") is False
        )
        assert tradingview_service.verify_hmac_signature(payload, "", "secret") is False

    def test_parse_tradingview_webhook_order(self, tradingview_service):
        """Test parsing order webhook"""
        payload = {
            "ticker": "BTCUSDT",
            "action": "buy",
            "quantity": "0.1",
            "order_type": "market",
            "strategy": "Test Strategy",
        }

        webhook, error = tradingview_service.parse_tradingview_webhook(payload)

        assert error is None
        assert isinstance(webhook, TradingViewOrderWebhook)
        assert webhook.ticker == "BTCUSDT"
        assert webhook.action == "buy"
        assert webhook.order_type == "market"

    def test_parse_tradingview_webhook_position(self, tradingview_service):
        """Test parsing position webhook"""
        payload = {
            "ticker": "BTCUSDT",
            "action": "close",
            "size": "0.5",
            "pnl": "100.0",
            "current_price": "50000",
        }

        webhook, error = tradingview_service.parse_tradingview_webhook(payload)

        assert error is None
        assert isinstance(webhook, TradingViewPositionWebhook)
        assert webhook.ticker == "BTCUSDT"
        assert webhook.action == "close"

    def test_parse_tradingview_webhook_signal(self, tradingview_service):
        """Test parsing signal webhook"""
        payload = {
            "ticker": "BTCUSDT",
            "action": "buy",
            "signal_strength": "strong",
            "rsi": 30.5,
            "trend": "bullish",
        }

        webhook, error = tradingview_service.parse_tradingview_webhook(payload)

        assert error is None
        assert isinstance(webhook, TradingViewSignalWebhook)
        assert webhook.signal_strength == "strong"
        assert webhook.rsi == 30.5

    def test_parse_tradingview_webhook_invalid(self, tradingview_service):
        """Test parsing invalid webhook payload"""
        payload = {
            "invalid_field": "value"
            # Missing required ticker and action
        }

        webhook, error = tradingview_service.parse_tradingview_webhook(payload)

        assert webhook is None
        assert isinstance(error, WebhookValidationError)
        assert error.error_type == "format"

    @pytest.mark.asyncio
    async def test_process_webhook_delivery_success(
        self,
        tradingview_service,
        mock_webhook_repo,
        mock_webhook_delivery_repo,
        sample_webhook,
    ):
        """Test successful webhook delivery processing"""
        # Setup
        webhook_path = "test-webhook"
        payload = {"ticker": "BTCUSDT", "action": "buy", "quantity": "0.1"}
        headers = {"content-type": "application/json"}

        mock_webhook_repo.get_by_url_path.return_value = sample_webhook
        mock_webhook_delivery_repo.create.return_value = AsyncMock(id=str(uuid4()))
        mock_webhook_repo.record_delivery_stats.return_value = None
        mock_webhook_delivery_repo.update.return_value = None
        mock_webhook_delivery_repo.update_delivery_status.return_value = None

        # Execute
        success, result = await tradingview_service.process_webhook_delivery(
            webhook_path, payload, headers
        )

        # Verify
        assert success is True
        assert "message" in result
        assert "delivery_id" in result
        assert result["orders_created"] >= 0

        mock_webhook_repo.get_by_url_path.assert_called_once_with(webhook_path)
        mock_webhook_delivery_repo.create.assert_called_once()
        mock_webhook_repo.record_delivery_stats.assert_called_once_with(
            sample_webhook.id, True
        )

    @pytest.mark.asyncio
    async def test_process_webhook_delivery_not_found(
        self, tradingview_service, mock_webhook_repo
    ):
        """Test webhook delivery processing with webhook not found"""
        # Setup
        webhook_path = "nonexistent-webhook"
        payload = {"ticker": "BTCUSDT", "action": "buy"}
        headers = {}

        mock_webhook_repo.get_by_url_path.return_value = None

        # Execute
        success, result = await tradingview_service.process_webhook_delivery(
            webhook_path, payload, headers
        )

        # Verify
        assert success is False
        assert result["error"] == "Webhook not found"
        assert result["code"] == "WEBHOOK_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_process_webhook_delivery_inactive(
        self, tradingview_service, mock_webhook_repo, sample_webhook
    ):
        """Test webhook delivery processing with inactive webhook"""
        # Setup
        webhook_path = "test-webhook"
        payload = {"ticker": "BTCUSDT", "action": "buy"}
        headers = {}

        sample_webhook.is_active = False
        mock_webhook_repo.get_by_url_path.return_value = sample_webhook

        # Execute
        success, result = await tradingview_service.process_webhook_delivery(
            webhook_path, payload, headers
        )

        # Verify
        assert success is False
        assert result["error"] == "Webhook is not active"
        assert result["code"] == "WEBHOOK_INACTIVE"

    @pytest.mark.asyncio
    async def test_process_webhook_delivery_invalid_signature(
        self,
        tradingview_service,
        mock_webhook_repo,
        mock_webhook_delivery_repo,
        sample_webhook,
    ):
        """Test webhook delivery processing with invalid HMAC signature"""
        # Setup
        webhook_path = "test-webhook"
        payload = {"ticker": "BTCUSDT", "action": "buy"}
        headers = {}
        signature = "sha256=invalid_signature"

        mock_webhook_repo.get_by_url_path.return_value = sample_webhook
        mock_delivery = AsyncMock(id=str(uuid4()))
        mock_webhook_delivery_repo.create.return_value = mock_delivery
        mock_webhook_delivery_repo.update_delivery_status.return_value = None

        # Execute
        success, result = await tradingview_service.process_webhook_delivery(
            webhook_path, payload, headers, signature
        )

        # Verify
        assert success is False
        assert result["error"] == "Invalid signature"
        assert result["code"] == "INVALID_SIGNATURE"

        # Verify delivery was marked as failed
        mock_webhook_delivery_repo.update_delivery_status.assert_called_with(
            mock_delivery.id,
            WebhookDeliveryStatus.FAILED,
            error_message="Invalid HMAC signature",
            error_details={"signature_provided": True},
        )

    @pytest.mark.asyncio
    async def test_process_order_webhook(self, tradingview_service, sample_webhook):
        """Test processing order-specific webhook"""
        order_webhook = TradingViewOrderWebhook(
            ticker="BTCUSDT", action="buy", quantity=0.1, order_type="market"
        )

        result = await tradingview_service._process_order_webhook(
            sample_webhook, order_webhook
        )

        assert "created" in result
        assert "executed" in result
        assert "failed" in result
        assert result["created"] == 1
        assert result["executed"] == 1  # Market orders execute immediately

    @pytest.mark.asyncio
    async def test_process_order_webhook_limit_order(
        self, tradingview_service, sample_webhook
    ):
        """Test processing limit order webhook"""
        order_webhook = TradingViewOrderWebhook(
            ticker="BTCUSDT",
            action="buy",
            quantity=0.1,
            order_type="limit",
            price=45000,
        )

        result = await tradingview_service._process_order_webhook(
            sample_webhook, order_webhook
        )

        assert result["created"] == 1
        assert result["executed"] == 0  # Limit orders don't execute immediately

    @pytest.mark.asyncio
    async def test_process_position_webhook_close(
        self, tradingview_service, sample_webhook
    ):
        """Test processing position close webhook"""
        position_webhook = TradingViewPositionWebhook(
            ticker="BTCUSDT", action="close", size=0.5, pnl=100.0
        )

        result = await tradingview_service._process_position_webhook(
            sample_webhook, position_webhook
        )

        assert result["created"] == 1
        assert result["executed"] == 1

    @pytest.mark.asyncio
    async def test_process_signal_webhook_strong(
        self, tradingview_service, sample_webhook
    ):
        """Test processing strong signal webhook"""
        signal_webhook = TradingViewSignalWebhook(
            ticker="BTCUSDT", action="buy", signal_strength="strong", rsi=25.0
        )

        result = await tradingview_service._process_signal_webhook(
            sample_webhook, signal_webhook
        )

        assert result["created"] == 1
        assert result["executed"] == 1

    @pytest.mark.asyncio
    async def test_process_signal_webhook_weak(
        self, tradingview_service, sample_webhook
    ):
        """Test processing weak signal webhook"""
        signal_webhook = TradingViewSignalWebhook(
            ticker="BTCUSDT", action="buy", signal_strength="weak", rsi=45.0
        )

        result = await tradingview_service._process_signal_webhook(
            sample_webhook, signal_webhook
        )

        assert result["created"] == 0
        assert result["executed"] == 0

    @pytest.mark.asyncio
    async def test_get_webhook_by_url_path(
        self, tradingview_service, mock_webhook_repo, sample_webhook
    ):
        """Test getting webhook by URL path"""
        url_path = "test-webhook"
        mock_webhook_repo.get_by_url_path.return_value = sample_webhook

        result = await tradingview_service.get_webhook_by_url_path(url_path)

        assert result == sample_webhook
        mock_webhook_repo.get_by_url_path.assert_called_once_with(url_path)

    @pytest.mark.asyncio
    async def test_get_delivery_status(
        self, tradingview_service, mock_webhook_delivery_repo, sample_delivery
    ):
        """Test getting delivery status"""
        delivery_id = uuid4()
        mock_webhook_delivery_repo.get.return_value = sample_delivery

        result = await tradingview_service.get_delivery_status(delivery_id)

        assert result == sample_delivery
        mock_webhook_delivery_repo.get.assert_called_once_with(delivery_id)

    @pytest.mark.asyncio
    async def test_retry_failed_delivery_success(
        self, tradingview_service, mock_webhook_delivery_repo, sample_delivery
    ):
        """Test successfully retrying failed delivery"""
        delivery_id = uuid4()
        sample_delivery.status = WebhookDeliveryStatus.FAILED

        mock_webhook_delivery_repo.get.return_value = sample_delivery
        mock_webhook_delivery_repo.update_delivery_status.return_value = None
        mock_webhook_delivery_repo.schedule_retry.return_value = True

        result = await tradingview_service.retry_failed_delivery(delivery_id)

        assert result is True
        mock_webhook_delivery_repo.update_delivery_status.assert_called_with(
            delivery_id, WebhookDeliveryStatus.RETRYING
        )
        mock_webhook_delivery_repo.schedule_retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_failed_delivery_not_failed(
        self, tradingview_service, mock_webhook_delivery_repo, sample_delivery
    ):
        """Test retrying delivery that is not in failed state"""
        delivery_id = uuid4()
        sample_delivery.status = WebhookDeliveryStatus.SUCCESS  # Not failed

        mock_webhook_delivery_repo.get.return_value = sample_delivery

        result = await tradingview_service.retry_failed_delivery(delivery_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_webhook_stats(
        self, tradingview_service, mock_webhook_repo, mock_webhook_delivery_repo
    ):
        """Test getting webhook statistics"""
        webhook_id = uuid4()
        days = 30

        mock_performance_stats = {
            "total_webhooks": 1,
            "total_deliveries": 100,
            "successful_deliveries": 95,
            "failed_deliveries": 5,
        }

        mock_delivery_stats = {
            "average_processing_time_ms": 150.0,
            "total_orders_created": 95,
            "total_orders_executed": 90,
        }

        mock_webhook_repo.get_performance_stats.return_value = mock_performance_stats
        mock_webhook_delivery_repo.get_delivery_stats.return_value = mock_delivery_stats

        result = await tradingview_service.get_webhook_stats(webhook_id, days)

        assert "total_deliveries" in result
        assert "average_processing_time_ms" in result
        assert "period_days" in result
        assert result["period_days"] == days

        mock_webhook_repo.get_performance_stats.assert_called_once_with(None, days)
        mock_webhook_delivery_repo.get_delivery_stats.assert_called_once_with(
            webhook_id, days
        )
