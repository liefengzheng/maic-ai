"""add database-backed LLM model catalog

Revision ID: 011_model_catalog
Revises: 010_restrict_skill_delete
Create Date: 2026-09-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "011_model_catalog"
down_revision = "010_restrict_skill_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=False),
        sa.Column(
            "connection_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_llm_models_name"),
    )
    op.add_column("conversations", sa.Column("model_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key("fk_conversations_model_id", "conversations", "llm_models", ["model_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_conversations_model_id", "conversations", ["model_id"])


def downgrade() -> None:
    op.drop_index("ix_conversations_model_id", table_name="conversations")
    op.drop_constraint("fk_conversations_model_id", "conversations", type_="foreignkey")
    op.drop_column("conversations", "model_id")
    op.drop_table("llm_models")