"""Add AI Alerts table for chat notifications

Revision ID: 20251227_0001
Revises: 20251226_0002
Create Date: 2025-12-27 00:01:00.000000

Tables:
- ai_alerts: Stores alerts for the AI chat system
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251227_0001"
down_revision: Union[str, None] = "20251226_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ai_alerts table"""

    op.create_table(
        "ai_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("type", sa.String(length=50), nullable=False),  # critical, warning, info, success
        sa.Column("category", sa.String(length=50), nullable=False),  # trade, news, strategy, system, market
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=True),  # null = global alert
        sa.Column("strategy_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("bot_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index for unread alerts
    op.create_index(
        "ix_ai_alerts_unread",
        "ai_alerts",
        ["is_read", "created_at"],
        postgresql_where=sa.text("is_read = false")
    )

    # Index for user alerts
    op.create_index(
        "ix_ai_alerts_user_id",
        "ai_alerts",
        ["user_id"]
    )

    # Index by category
    op.create_index(
        "ix_ai_alerts_category",
        "ai_alerts",
        ["category"]
    )

    # Index by type
    op.create_index(
        "ix_ai_alerts_type",
        "ai_alerts",
        ["type"]
    )

    # Index for recent alerts
    op.create_index(
        "ix_ai_alerts_created_at",
        "ai_alerts",
        ["created_at"]
    )


def downgrade() -> None:
    """Drop ai_alerts table"""
    op.drop_table("ai_alerts")
