"""Unit tests for Position model"""

from decimal import Decimal
from infrastructure.database.models.position import (
    Position,
    PositionSide,
    PositionStatus,
)


class TestPosition:
    """Test Position model business logic"""

    def test_position_creation(self):
        """Test position creation with basic fields"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        assert position.symbol == "BTCUSDT"
        assert position.side == PositionSide.LONG
        assert position.status == PositionStatus.OPEN
        assert position.size == Decimal("0.001")
        assert position.entry_price == Decimal("50000")
        assert position.unrealized_pnl == Decimal("0")
        assert position.realized_pnl == Decimal("0")
        assert position.total_fees == Decimal("0")
        assert position.funding_fees == Decimal("0")

    def test_update_size(self):
        """Test updating position size"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        # Increase position size
        position.update_size(Decimal("0.002"), Decimal("51000"))

        # New average entry price should be calculated
        # (0.001 * 50000 + 0.001 * 51000) / 0.002 = 50500
        assert position.size == Decimal("0.002")
        assert position.entry_price == Decimal("50500")
        assert position.last_update_at is not None

    def test_update_size_to_zero_closes_position(self):
        """Test that updating size to zero closes position"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        position.update_size(Decimal("0"), Decimal("51000"))

        assert position.status == PositionStatus.CLOSED
        assert position.closed_at is not None

    def test_update_pnl(self):
        """Test updating PnL values"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        # Update unrealized PnL
        position.update_pnl(unrealized=Decimal("100"))
        assert position.unrealized_pnl == Decimal("100")

        # Update both unrealized and realized PnL
        position.update_pnl(unrealized=Decimal("150"), realized=Decimal("50"))
        assert position.unrealized_pnl == Decimal("150")
        assert position.realized_pnl == Decimal("50")

        # Update again - realized should accumulate
        position.update_pnl(unrealized=Decimal("200"), realized=Decimal("25"))
        assert position.unrealized_pnl == Decimal("200")
        assert position.realized_pnl == Decimal("75")

    def test_update_margin(self):
        """Test updating margin requirements"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        position.update_margin(Decimal("600"), Decimal("300"))

        assert position.initial_margin == Decimal("600")
        assert position.maintenance_margin == Decimal("300")
        assert position.last_update_at is not None

    def test_update_liquidation_price(self):
        """Test updating liquidation price"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        position.update_liquidation_price(Decimal("45000"))

        assert position.liquidation_price == Decimal("45000")
        assert position.last_update_at is not None

    def test_update_mark_price_long_position(self):
        """Test updating mark price for long position"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        # Mark price above entry price = profit
        position.update_mark_price(Decimal("51000"))

        assert position.mark_price == Decimal("51000")
        # (51000 - 50000) * 0.001 = 1.0
        assert position.unrealized_pnl == Decimal("1.0")

        # Mark price below entry price = loss
        position.update_mark_price(Decimal("49000"))

        assert position.mark_price == Decimal("49000")
        # (49000 - 50000) * 0.001 = -1.0
        assert position.unrealized_pnl == Decimal("-1.0")

    def test_update_mark_price_short_position(self):
        """Test updating mark price for short position"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.SHORT,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        # Mark price below entry price = profit for short
        position.update_mark_price(Decimal("49000"))

        assert position.mark_price == Decimal("49000")
        # (50000 - 49000) * 0.001 = 1.0
        assert position.unrealized_pnl == Decimal("1.0")

        # Mark price above entry price = loss for short
        position.update_mark_price(Decimal("51000"))

        assert position.mark_price == Decimal("51000")
        # (50000 - 51000) * 0.001 = -1.0
        assert position.unrealized_pnl == Decimal("-1.0")

    def test_add_fee(self):
        """Test adding fees to position"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        # Add trading fee
        position.add_fee(Decimal("0.1"), "trading")
        assert position.total_fees == Decimal("0.1")
        assert position.funding_fees == Decimal("0")

        # Add funding fee
        position.add_fee(Decimal("0.05"), "funding")
        assert position.total_fees == Decimal("0.15")
        assert position.funding_fees == Decimal("0.05")

    def test_close_position(self):
        """Test closing position"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        final_pnl = Decimal("100")
        position.close(final_pnl)

        assert position.status == PositionStatus.CLOSED
        assert position.closed_at is not None
        assert position.realized_pnl == Decimal("100")
        assert position.unrealized_pnl == Decimal("0")

    def test_mark_closing(self):
        """Test marking position as closing"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        position.mark_closing()

        assert position.status == PositionStatus.CLOSING
        assert position.last_update_at is not None

    def test_liquidate_long_position(self):
        """Test liquidating long position"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        liquidation_price = Decimal("45000")
        position.liquidate(liquidation_price)

        assert position.status == PositionStatus.LIQUIDATED
        assert position.closed_at is not None
        # (45000 - 50000) * 0.001 = -5.0
        assert position.realized_pnl == Decimal("-5.0")
        assert position.unrealized_pnl == Decimal("0")

    def test_liquidate_short_position(self):
        """Test liquidating short position"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.SHORT,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        liquidation_price = Decimal("55000")
        position.liquidate(liquidation_price)

        assert position.status == PositionStatus.LIQUIDATED
        assert position.closed_at is not None
        # (50000 - 55000) * 0.001 = -5.0
        assert position.realized_pnl == Decimal("-5.0")
        assert position.unrealized_pnl == Decimal("0")

    def test_get_total_pnl(self):
        """Test getting total PnL"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        position.update_pnl(unrealized=Decimal("100"), realized=Decimal("50"))

        assert position.get_total_pnl() == Decimal("150")

    def test_get_pnl_percentage(self):
        """Test getting PnL percentage"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        # 100 PnL on 500 initial margin = 20%
        position.update_pnl(unrealized=Decimal("100"))
        assert position.get_pnl_percentage() == 20.0

        # -50 PnL on 500 initial margin = -10%
        position.update_pnl(unrealized=Decimal("-50"))
        assert position.get_pnl_percentage() == -10.0

    def test_get_roe(self):
        """Test getting Return on Equity"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        position.update_pnl(unrealized=Decimal("150"), realized=Decimal("50"))

        # Total PnL is 200, initial margin is 500 = 40% ROE
        assert position.get_roe() == 40.0

    def test_is_profitable(self):
        """Test checking if position is profitable"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        # Initially no PnL
        assert position.is_profitable() is False

        # Positive PnL
        position.update_pnl(unrealized=Decimal("100"))
        assert position.is_profitable() is True

        # Negative PnL
        position.update_pnl(unrealized=Decimal("-50"))
        assert position.is_profitable() is False

    def test_is_at_risk_long_position(self):
        """Test risk checking for long position"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        position.liquidation_price = Decimal("45000")

        # No mark price set
        assert position.is_at_risk() is False

        # Mark price far from liquidation (not at risk)
        position.mark_price = Decimal("49000")
        assert position.is_at_risk() is False

        # Mark price close to liquidation (at risk)
        # Entry: 50000, Liquidation: 45000, Mark: 46000
        # Risk = (50000 - 46000) / (50000 - 45000) * 100 = 80%
        position.mark_price = Decimal("46000")
        assert position.is_at_risk() is True

    def test_is_open(self):
        """Test checking if position is open"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        # Initially open
        assert position.is_open() is True

        # Closing status is still open
        position.mark_closing()
        assert position.is_open() is True

        # Closed status is not open
        position.close()
        assert position.is_open() is False

    def test_is_closed(self):
        """Test checking if position is closed"""
        position = Position(
            symbol="BTCUSDT",
            side=PositionSide.LONG,
            size=Decimal("0.001"),
            entry_price=Decimal("50000"),
            initial_margin=Decimal("500"),
            maintenance_margin=Decimal("250"),
            leverage=Decimal("10"),
            exchange_account_id="account-123",
        )

        # Initially not closed
        assert position.is_closed() is False

        # Open status is not closed
        assert position.is_closed() is False

        # Closed status is closed
        position.close()
        assert position.is_closed() is True

        # Liquidated status is closed
        position.status = PositionStatus.LIQUIDATED
        assert position.is_closed() is True

    def test_position_enums(self):
        """Test position enum values"""
        # PositionSide
        assert PositionSide.LONG == "long"
        assert PositionSide.SHORT == "short"

        # PositionStatus
        assert PositionStatus.OPEN == "open"
        assert PositionStatus.CLOSED == "closed"
        assert PositionStatus.CLOSING == "closing"
        assert PositionStatus.LIQUIDATED == "liquidated"
