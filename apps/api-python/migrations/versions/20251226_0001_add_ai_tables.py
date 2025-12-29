"""Add AI Trading tables for snapshots and conversations

Revision ID: 20251226_0001
Revises: 20250819_1519_bdea0d25c631
Create Date: 2025-12-26 00:01:00.000000

Tables:
- ai_daily_snapshots: Daily performance snapshots
- ai_bot_snapshots: Individual bot performance snapshots
- ai_strategy_snapshots: Strategy performance snapshots
- ai_conversations: AI chat conversation history
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251226_0001"
down_revision: Union[str, None] = "bdea0d25c631"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create AI-related tables"""

    # Create ai_daily_snapshots table
    # Stores daily aggregated performance data for AI analysis
    op.create_table(
        "ai_daily_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date"),
    )
    op.create_index(
        "ix_ai_daily_snapshots_date",
        "ai_daily_snapshots",
        ["date"],
        unique=True
    )

    # Create ai_bot_snapshots table
    # Stores per-bot daily performance data
    op.create_table(
        "ai_bot_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bot_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bot_id", "date", name="uq_ai_bot_snapshots_bot_date"),
    )
    op.create_index(
        "ix_ai_bot_snapshots_bot_id",
        "ai_bot_snapshots",
        ["bot_id"]
    )
    op.create_index(
        "ix_ai_bot_snapshots_date",
        "ai_bot_snapshots",
        ["date"]
    )
    op.create_index(
        "ix_ai_bot_snapshots_bot_date",
        "ai_bot_snapshots",
        ["bot_id", "date"]
    )

    # Create ai_strategy_snapshots table
    # Stores per-strategy daily performance data
    op.create_table(
        "ai_strategy_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("strategy_id", "date", name="uq_ai_strategy_snapshots_strategy_date"),
    )
    op.create_index(
        "ix_ai_strategy_snapshots_strategy_id",
        "ai_strategy_snapshots",
        ["strategy_id"]
    )
    op.create_index(
        "ix_ai_strategy_snapshots_date",
        "ai_strategy_snapshots",
        ["date"]
    )
    op.create_index(
        "ix_ai_strategy_snapshots_strategy_date",
        "ai_strategy_snapshots",
        ["strategy_id", "date"]
    )

    # Create ai_conversations table
    # Stores AI chat conversations for context and history
    op.create_table(
        "ai_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", sa.String(length=100), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("context_type", sa.String(length=50), nullable=False),
        sa.Column("context_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("messages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_conversations_conversation_id",
        "ai_conversations",
        ["conversation_id"],
        unique=True
    )
    op.create_index(
        "ix_ai_conversations_user_id",
        "ai_conversations",
        ["user_id"]
    )
    op.create_index(
        "ix_ai_conversations_context_type",
        "ai_conversations",
        ["context_type"]
    )
    op.create_index(
        "ix_ai_conversations_created_at",
        "ai_conversations",
        ["created_at"]
    )

    # Create ai_strategy_evaluations table
    # Stores strategy evaluation results from the AI
    op.create_table(
        "ai_strategy_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("robustness_score", sa.Float(), nullable=False),
        sa.Column("institutional_grade", sa.String(length=10), nullable=False),
        sa.Column("evaluation_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("backtest_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_strategy_evaluations_strategy_id",
        "ai_strategy_evaluations",
        ["strategy_id"]
    )
    op.create_index(
        "ix_ai_strategy_evaluations_created_at",
        "ai_strategy_evaluations",
        ["created_at"]
    )
    op.create_index(
        "ix_ai_strategy_evaluations_grade",
        "ai_strategy_evaluations",
        ["institutional_grade"]
    )

    # Create ai_bot_analyses table
    # Stores bot analysis results from the AI
    op.create_table(
        "ai_bot_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bot_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("health_score", sa.Float(), nullable=False),
        sa.Column("risk_assessment", sa.String(length=50), nullable=False),
        sa.Column("analysis_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_bot_analyses_bot_id",
        "ai_bot_analyses",
        ["bot_id"]
    )
    op.create_index(
        "ix_ai_bot_analyses_created_at",
        "ai_bot_analyses",
        ["created_at"]
    )


def downgrade() -> None:
    """Drop AI-related tables"""
    op.drop_table("ai_bot_analyses")
    op.drop_table("ai_strategy_evaluations")
    op.drop_table("ai_conversations")
    op.drop_table("ai_strategy_snapshots")
    op.drop_table("ai_bot_snapshots")
    op.drop_table("ai_daily_snapshots")
