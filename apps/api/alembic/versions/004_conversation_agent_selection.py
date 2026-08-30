"""persist the Agent selected for each conversation

Revision ID: 004_conversation_agent_selection
Revises: 003_agent_user_ownership
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "004_conversation_agent_selection"
down_revision = "003_agent_user_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("tenant_id", postgresql.UUID(as_uuid=True)))
    op.add_column("conversations", sa.Column("agent_id", postgresql.UUID(as_uuid=True)))
    op.add_column("conversations", sa.Column("super_agent_id", postgresql.UUID(as_uuid=True)))
    op.execute("""
        UPDATE conversations
        SET tenant_id = users.tenant_id
        FROM users
        WHERE users.id = conversations.user_id
    """)
    op.alter_column("conversations", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_conversations_tenant_id",
        "conversations",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_conversations_agent_tenant",
        "conversations",
        "agents",
        ["agent_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_conversations_super_agent_tenant",
        "conversations",
        "super_agents",
        ["super_agent_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_conversations_single_agent_target",
        "conversations",
        "agent_id IS NULL OR super_agent_id IS NULL",
    )
    op.create_index("ix_conversations_agent_id", "conversations", ["agent_id"])
    op.create_index("ix_conversations_super_agent_id", "conversations", ["super_agent_id"])


def downgrade() -> None:
    op.drop_index("ix_conversations_super_agent_id", table_name="conversations")
    op.drop_index("ix_conversations_agent_id", table_name="conversations")
    op.drop_constraint("ck_conversations_single_agent_target", "conversations", type_="check")
    op.drop_constraint("fk_conversations_super_agent_tenant", "conversations", type_="foreignkey")
    op.drop_constraint("fk_conversations_agent_tenant", "conversations", type_="foreignkey")
    op.drop_constraint("fk_conversations_tenant_id", "conversations", type_="foreignkey")
    op.drop_column("conversations", "super_agent_id")
    op.drop_column("conversations", "agent_id")
    op.drop_column("conversations", "tenant_id")