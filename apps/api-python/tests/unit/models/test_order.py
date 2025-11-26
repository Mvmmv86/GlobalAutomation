"""Unit tests for Order model"""

from decimal import Decimal
from datetime import datetime, timedelta
from infrastructure.database.models.order import (
    Order,
    OrderType,
    OrderSide,
    OrderStatus,
    TimeInForce,
)


class TestOrder:
    """Test Order model business logic"""

    def test_order_creation(self):
        """Test order creation with basic fields"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=Decimal("0.001"),
            exchange_account_id="account-123",
        )

        assert order.client_order_id == "order-123"
        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.BUY
        assert order.type == OrderType.MARKET
        assert order.status == OrderStatus.PENDING
        assert order.quantity == Decimal("0.001")
        assert order.filled_quantity == Decimal("0")
        assert order.fees_paid == Decimal("0")
        assert order.retry_count == 0

    def test_submit_order(self):
        """Test submitting order to exchange"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=Decimal("0.001"),
            exchange_account_id="account-123",
        )

        external_id = "exchange-order-456"
        order.submit(external_id)

        assert order.status == OrderStatus.SUBMITTED
        assert order.external_id == external_id
        assert order.submitted_at is not None

    def test_mark_open(self):
        """Test marking order as open"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=Decimal("0.001"),
            price=Decimal("50000"),
            exchange_account_id="account-123",
        )

        order.mark_open()
        assert order.status == OrderStatus.OPEN

    def test_add_fill_partial(self):
        """Test adding partial fill"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=Decimal("0.002"),
            price=Decimal("50000"),
            exchange_account_id="account-123",
        )

        # First partial fill
        order.add_fill(
            quantity=Decimal("0.001"),
            price=Decimal("50000"),
            fee=Decimal("0.1"),
            fee_currency="USDT",
        )

        assert order.filled_quantity == Decimal("0.001")
        assert order.average_fill_price == Decimal("50000")
        assert order.fees_paid == Decimal("0.1")
        assert order.fee_currency == "USDT"
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.first_fill_at is not None
        assert order.last_fill_at is not None

        # Second partial fill at different price
        order.add_fill(quantity=Decimal("0.001"), price=Decimal("50100"))

        assert order.filled_quantity == Decimal("0.002")
        assert order.average_fill_price == Decimal(
            "50050"
        )  # Average of 50000 and 50100
        assert order.status == OrderStatus.FILLED
        assert order.completed_at is not None

    def test_add_fill_complete(self):
        """Test adding fill that completes the order"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=Decimal("0.001"),
            exchange_account_id="account-123",
        )

        # Complete fill
        order.add_fill(quantity=Decimal("0.001"), price=Decimal("50000"))

        assert order.filled_quantity == Decimal("0.001")
        assert order.status == OrderStatus.FILLED
        assert order.completed_at is not None

    def test_cancel_order(self):
        """Test canceling order"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=Decimal("0.001"),
            price=Decimal("50000"),
            exchange_account_id="account-123",
        )

        reason = "User requested cancellation"
        order.cancel(reason)

        assert order.status == OrderStatus.CANCELED
        assert order.completed_at is not None
        assert order.error_message == reason

    def test_reject_order(self):
        """Test rejecting order"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=Decimal("0.001"),
            price=Decimal("50000"),
            exchange_account_id="account-123",
        )

        reason = "Insufficient balance"
        error_code = "INSUFFICIENT_BALANCE"
        order.reject(reason, error_code)

        assert order.status == OrderStatus.REJECTED
        assert order.completed_at is not None
        assert order.error_message == reason
        assert order.error_code == error_code

    def test_mark_failed(self):
        """Test marking order as failed"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=Decimal("0.001"),
            exchange_account_id="account-123",
        )

        error = "Network timeout"
        error_code = "TIMEOUT"
        order.mark_failed(error, error_code)

        assert order.status == OrderStatus.FAILED
        assert order.completed_at is not None
        assert order.error_message == error
        assert order.error_code == error_code

    def test_mark_expired(self):
        """Test marking order as expired"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=Decimal("0.001"),
            price=Decimal("50000"),
            time_in_force=TimeInForce.GTD,
            good_till_date=datetime.now() + timedelta(hours=1),
            exchange_account_id="account-123",
        )

        order.mark_expired()

        assert order.status == OrderStatus.EXPIRED
        assert order.completed_at is not None

    def test_increment_retry(self):
        """Test incrementing retry counter"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            quantity=Decimal("0.001"),
            exchange_account_id="account-123",
        )

        assert order.retry_count == 0

        order.increment_retry()
        assert order.retry_count == 1

        order.increment_retry()
        assert order.retry_count == 2

    def test_get_remaining_quantity(self):
        """Test getting remaining unfilled quantity"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=Decimal("0.002"),
            price=Decimal("50000"),
            exchange_account_id="account-123",
        )

        # Initially all quantity remaining
        assert order.get_remaining_quantity() == Decimal("0.002")

        # After partial fill
        order.add_fill(Decimal("0.001"), Decimal("50000"))
        assert order.get_remaining_quantity() == Decimal("0.001")

        # After complete fill
        order.add_fill(Decimal("0.001"), Decimal("50000"))
        assert order.get_remaining_quantity() == Decimal("0")

    def test_get_fill_percentage(self):
        """Test getting fill percentage"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=Decimal("0.002"),
            price=Decimal("50000"),
            exchange_account_id="account-123",
        )

        # Initially 0% filled
        assert order.get_fill_percentage() == 0.0

        # After 50% fill
        order.add_fill(Decimal("0.001"), Decimal("50000"))
        assert order.get_fill_percentage() == 50.0

        # After 100% fill
        order.add_fill(Decimal("0.001"), Decimal("50000"))
        assert order.get_fill_percentage() == 100.0

    def test_is_open(self):
        """Test checking if order is open"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=Decimal("0.002"),
            price=Decimal("50000"),
            exchange_account_id="account-123",
        )

        # Pending order is not open
        assert order.is_open() is False

        # Open order
        order.mark_open()
        assert order.is_open() is True

        # Partially filled order is still open
        order.add_fill(Decimal("0.001"), Decimal("50000"))
        assert order.is_open() is True

        # Completely filled order is not open
        order.add_fill(Decimal("0.001"), Decimal("50000"))
        assert order.is_open() is False

    def test_is_completed(self):
        """Test checking if order is completed"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=Decimal("0.001"),
            price=Decimal("50000"),
            exchange_account_id="account-123",
        )

        # Pending order is not completed
        assert order.is_completed() is False

        # Open order is not completed
        order.mark_open()
        assert order.is_completed() is False

        # Filled order is completed
        order.add_fill(Decimal("0.001"), Decimal("50000"))
        assert order.is_completed() is True

        # Reset and test other completion states
        order.status = OrderStatus.CANCELED
        assert order.is_completed() is True

        order.status = OrderStatus.REJECTED
        assert order.is_completed() is True

        order.status = OrderStatus.EXPIRED
        assert order.is_completed() is True

        order.status = OrderStatus.FAILED
        assert order.is_completed() is True

    def test_is_fillable(self):
        """Test checking if order can receive fills"""
        order = Order(
            client_order_id="order-123",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.LIMIT,
            quantity=Decimal("0.002"),
            price=Decimal("50000"),
            exchange_account_id="account-123",
        )

        # Pending order is not fillable
        assert order.is_fillable() is False

        # Open order is fillable
        order.mark_open()
        assert order.is_fillable() is True

        # Partially filled order is fillable
        order.add_fill(Decimal("0.001"), Decimal("50000"))
        assert order.is_fillable() is True

        # Completely filled order is not fillable
        order.add_fill(Decimal("0.001"), Decimal("50000"))
        assert order.is_fillable() is False

    def test_order_enums(self):
        """Test order enum values"""
        # OrderType
        assert OrderType.MARKET == "market"
        assert OrderType.LIMIT == "limit"
        assert OrderType.STOP_LOSS == "stop_loss"
        assert OrderType.TAKE_PROFIT == "take_profit"
        assert OrderType.STOP_LIMIT == "stop_limit"

        # OrderSide
        assert OrderSide.BUY == "buy"
        assert OrderSide.SELL == "sell"

        # OrderStatus
        assert OrderStatus.PENDING == "pending"
        assert OrderStatus.SUBMITTED == "submitted"
        assert OrderStatus.OPEN == "open"
        assert OrderStatus.PARTIALLY_FILLED == "partially_filled"
        assert OrderStatus.FILLED == "filled"
        assert OrderStatus.CANCELED == "canceled"
        assert OrderStatus.REJECTED == "rejected"
        assert OrderStatus.EXPIRED == "expired"
        assert OrderStatus.FAILED == "failed"

        # TimeInForce
        assert TimeInForce.GTC == "gtc"
        assert TimeInForce.IOC == "ioc"
        assert TimeInForce.FOK == "fok"
        assert TimeInForce.GTD == "gtd"
