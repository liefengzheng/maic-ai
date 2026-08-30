"""distinguish tenant admins from regular users

Revision ID: 005_user_roles
Revises: 004_conversation_agent_selection
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa


revision = "005_user_roles"
down_revision = "004_conversation_agent_selection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(16), nullable=False, server_default="user"),
    )
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('admin', 'user')",
    )
    op.execute("""
        UPDATE users
        SET role = 'admin'
        WHERE id IN (
            SELECT owner_user_id FROM agents WHERE owner_user_id IS NOT NULL
            UNION
            SELECT owner_user_id FROM super_agents WHERE owner_user_id IS NOT NULL
            UNION
            SELECT id
            FROM (
                SELECT DISTINCT ON (tenant_id) id
                FROM users
                ORDER BY tenant_id, created_at, id
            ) AS first_tenant_users
        )
    """)
    op.create_index("ix_users_tenant_role", "users", ["tenant_id", "role"])


def downgrade() -> None:
    op.drop_index("ix_users_tenant_role", table_name="users")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")