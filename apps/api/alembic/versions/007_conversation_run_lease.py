"""prevent concurrent runs in one conversation

Revision ID: 007_conversation_run_lease
Revises: 006_global_agent_catalog
Create Date: 2026-08-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "007_conversation_run_lease"
down_revision = "006_global_agent_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_runs",
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("conversation_runs")