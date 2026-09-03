"""add runtime skill registry

Revision ID: 008_skill_registry
Revises: 007_conversation_run_lease
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "008_skill_registry"
down_revision = "007_conversation_run_lease"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skill_registry",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("skill_code", sa.String(100), nullable=False, unique=True),
        sa.Column("skill_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("skill_type", sa.String(20), nullable=False, server_default="local"),
        sa.Column("handler", sa.String(100), nullable=False),
        sa.Column(
            "input_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "output_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "execution_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("skill_type = 'local'", name="ck_skill_registry_type"),
    )
    op.create_index("ix_skill_registry_enabled", "skill_registry", ["enabled"])
    op.create_table(
        "agent_skills",
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "skill_id",
            sa.BigInteger(),
            sa.ForeignKey("skill_registry.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("agent_skills")
    op.drop_index("ix_skill_registry_enabled", table_name="skill_registry")
    op.drop_table("skill_registry")