"""Initial schema - users, exchange_accounts, webhooks, orders, positions

Revision ID: 001
Revises:
Create Date: 2025-08-16 10:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to this revision"""

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("totp_secret", sa.String(length=32), nullable=True),
        sa.Column("totp_enabled", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_is_active"), "users", ["is_active"], unique=False)

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("prefix", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False),
        sa.Column("rate_limit_per_hour", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prefix"),
    )
    op.create_index(
        op.f("ix_api_keys_is_active"), "api_keys", ["is_active"], unique=False
    )
    op.create_index(
        op.f("ix_api_keys_key_hash"), "api_keys", ["key_hash"], unique=False
    )
    op.create_index(op.f("ix_api_keys_prefix"), "api_keys", ["prefix"], unique=True)

    # Create exchange_accounts table
    op.create_table(
        "exchange_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "exchange", sa.Enum("binance", "bybit", name="exchangetype"), nullable=False
        ),
        sa.Column("api_key", sa.String(length=512), nullable=False),
        sa.Column("secret_key", sa.String(length=512), nullable=False),
        sa.Column("passphrase", sa.String(length=512), nullable=True),
        sa.Column("testnet", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_exchange_accounts_exchange"),
        "exchange_accounts",
        ["exchange"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exchange_accounts_is_active"),
        "exchange_accounts",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        op.f("ix_exchange_accounts_testnet"),
        "exchange_accounts",
        ["testnet"],
        unique=False,
    )

    # Create webhooks table
    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url_path", sa.String(length=255), nullable=False),
        sa.Column("secret", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "paused", "disabled", "error", name="webhookstatus"),
            nullable=False,
        ),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False),
        sa.Column("rate_limit_per_hour", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("retry_delay_seconds", sa.Integer(), nullable=False),
        sa.Column("allowed_ips", sa.Text(), nullable=True),
        sa.Column("required_headers", sa.Text(), nullable=True),
        sa.Column("payload_validation_schema", sa.Text(), nullable=True),
        sa.Column("total_deliveries", sa.Integer(), nullable=False),
        sa.Column("successful_deliveries", sa.Integer(), nullable=False),
        sa.Column("failed_deliveries", sa.Integer(), nullable=False),
        sa.Column("last_delivery_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_pause_on_errors", sa.Boolean(), nullable=False),
        sa.Column("error_threshold", sa.Integer(), nullable=False),
        sa.Column("consecutive_errors", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url_path"),
    )
    op.create_index(op.f("ix_webhooks_url_path"), "webhooks", ["url_path"], unique=True)

    # Create webhook_deliveries table
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "processing",
                "success",
                "failed",
                "retrying",
                name="webhookdeliverystatus",
            ),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("headers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_duration_ms", sa.Integer(), nullable=True),
        sa.Column("hmac_valid", sa.Boolean(), nullable=True),
        sa.Column("ip_allowed", sa.Boolean(), nullable=True),
        sa.Column("headers_valid", sa.Boolean(), nullable=True),
        sa.Column("payload_valid", sa.Boolean(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "error_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("orders_created", sa.Integer(), nullable=False),
        sa.Column("orders_executed", sa.Integer(), nullable=False),
        sa.Column("orders_failed", sa.Integer(), nullable=False),
        sa.Column("webhook_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["webhook_id"], ["webhooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create orders table
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("client_order_id", sa.String(length=255), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("side", sa.Enum("buy", "sell", name="orderside"), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "market",
                "limit",
                "stop_loss",
                "take_profit",
                "stop_limit",
                name="ordertype",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "submitted",
                "open",
                "partially_filled",
                "filled",
                "canceled",
                "rejected",
                "expired",
                "failed",
                name="orderstatus",
            ),
            nullable=False,
        ),
        sa.Column(
            "quantity", postgresql.NUMERIC(precision=20, scale=8), nullable=False
        ),
        sa.Column("price", postgresql.NUMERIC(precision=20, scale=8), nullable=True),
        sa.Column(
            "stop_price", postgresql.NUMERIC(precision=20, scale=8), nullable=True
        ),
        sa.Column(
            "filled_quantity", postgresql.NUMERIC(precision=20, scale=8), nullable=False
        ),
        sa.Column(
            "average_fill_price",
            postgresql.NUMERIC(precision=20, scale=8),
            nullable=True,
        ),
        sa.Column(
            "fees_paid", postgresql.NUMERIC(precision=20, scale=8), nullable=False
        ),
        sa.Column("fee_currency", sa.String(length=10), nullable=True),
        sa.Column(
            "time_in_force",
            sa.Enum("gtc", "ioc", "fok", "gtd", name="timeinforce"),
            nullable=False,
        ),
        sa.Column("good_till_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_fill_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_fill_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("webhook_delivery_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column(
            "original_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column(
            "exchange_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("reduce_only", sa.Boolean(), nullable=False),
        sa.Column("post_only", sa.Boolean(), nullable=False),
        sa.Column(
            "exchange_account_id", postgresql.UUID(as_uuid=False), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["exchange_account_id"], ["exchange_accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["webhook_delivery_id"], ["webhook_deliveries.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_order_id"),
    )
    op.create_index(
        op.f("ix_orders_client_order_id"), "orders", ["client_order_id"], unique=True
    )
    op.create_index(
        op.f("ix_orders_external_id"), "orders", ["external_id"], unique=False
    )
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)
    op.create_index(op.f("ix_orders_symbol"), "orders", ["symbol"], unique=False)

    # Create positions table
    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column(
            "side", sa.Enum("long", "short", name="positionside"), nullable=False
        ),
        sa.Column(
            "status",
            sa.Enum("open", "closed", "closing", "liquidated", name="positionstatus"),
            nullable=False,
        ),
        sa.Column("size", postgresql.NUMERIC(precision=20, scale=8), nullable=False),
        sa.Column(
            "entry_price", postgresql.NUMERIC(precision=20, scale=8), nullable=False
        ),
        sa.Column(
            "mark_price", postgresql.NUMERIC(precision=20, scale=8), nullable=True
        ),
        sa.Column(
            "unrealized_pnl", postgresql.NUMERIC(precision=20, scale=8), nullable=False
        ),
        sa.Column(
            "realized_pnl", postgresql.NUMERIC(precision=20, scale=8), nullable=False
        ),
        sa.Column(
            "initial_margin", postgresql.NUMERIC(precision=20, scale=8), nullable=False
        ),
        sa.Column(
            "maintenance_margin",
            postgresql.NUMERIC(precision=20, scale=8),
            nullable=False,
        ),
        sa.Column("leverage", postgresql.NUMERIC(precision=5, scale=2), nullable=False),
        sa.Column(
            "liquidation_price",
            postgresql.NUMERIC(precision=20, scale=8),
            nullable=True,
        ),
        sa.Column(
            "bankruptcy_price", postgresql.NUMERIC(precision=20, scale=8), nullable=True
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_update_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "total_fees", postgresql.NUMERIC(precision=20, scale=8), nullable=False
        ),
        sa.Column(
            "funding_fees", postgresql.NUMERIC(precision=20, scale=8), nullable=False
        ),
        sa.Column(
            "exchange_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "exchange_account_id", postgresql.UUID(as_uuid=False), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["exchange_account_id"], ["exchange_accounts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_positions_external_id"), "positions", ["external_id"], unique=False
    )
    op.create_index(op.f("ix_positions_status"), "positions", ["status"], unique=False)
    op.create_index(op.f("ix_positions_symbol"), "positions", ["symbol"], unique=False)


def downgrade() -> None:
    """Downgrade from this revision"""

    # Drop tables in reverse order
    op.drop_table("positions")
    op.drop_table("orders")
    op.drop_table("webhook_deliveries")
    op.drop_table("webhooks")
    op.drop_table("exchange_accounts")
    op.drop_table("api_keys")
    op.drop_table("users")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS positionstatus")
    op.execute("DROP TYPE IF EXISTS positionside")
    op.execute("DROP TYPE IF EXISTS timeinforce")
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("DROP TYPE IF EXISTS ordertype")
    op.execute("DROP TYPE IF EXISTS orderside")
    op.execute("DROP TYPE IF EXISTS webhookdeliverystatus")
    op.execute("DROP TYPE IF EXISTS webhookstatus")
    op.execute("DROP TYPE IF EXISTS exchangetype")
