"""Add AI News Digests table and is_important field to strategies

Revision ID: 20251226_0002
Revises: 20251226_0001
Create Date: 2025-12-26 02:00:00.000000

Tables:
- ai_news_digests: Daily news aggregations for AI context

Fields:
- strategies.is_important: Flag for important strategies that trigger alerts
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251226_0002"
down_revision: Union[str, None] = "20251226_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create news digests table and add is_important field"""

    # Create ai_news_digests table
    op.create_table(
        "ai_news_digests",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date"),
    )
    op.create_index(
        "ix_ai_news_digests_date",
        "ai_news_digests",
        ["date"],
        unique=True
    )

    # Add is_important field to strategies table
    op.add_column(
        "strategies",
        sa.Column("is_important", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )
    op.create_index(
        "ix_strategies_is_important",
        "strategies",
        ["is_important"],
        postgresql_where=sa.text("is_important = true")
    )


def downgrade() -> None:
    """Remove news digests table and is_important field"""

    # Drop is_important field
    op.drop_index("ix_strategies_is_important", table_name="strategies")
    op.drop_column("strategies", "is_important")

    # Drop ai_news_digests table
    op.drop_index("ix_ai_news_digests_date", table_name="ai_news_digests")
    op.drop_table("ai_news_digests")
