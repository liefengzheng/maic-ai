"""associate user-designed agents with their owners

Revision ID: 003_agent_user_ownership
Revises: 002_tenant_agent_catalog
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "003_agent_user_ownership"
down_revision = "002_tenant_agent_catalog"
branch_labels = None
depends_on = None


def _add_ownership(table_name: str) -> None:
    op.add_column(
        table_name,
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        table_name,
        sa.Column(
            "visibility",
            sa.String(16),
            nullable=False,
            server_default="private",
        ),
    )
    op.create_foreign_key(
        f"fk_{table_name}_owner_tenant",
        table_name,
        "users",
        ["owner_user_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        f"ck_{table_name}_visibility",
        table_name,
        "visibility IN ('private', 'tenant')",
    )
    op.create_check_constraint(
        f"ck_{table_name}_private_has_owner",
        table_name,
        "visibility = 'tenant' OR owner_user_id IS NOT NULL",
    )
    op.create_index(
        f"ix_{table_name}_owner",
        table_name,
        ["tenant_id", "owner_user_id"],
    )


def _backfill_owner(table_name: str) -> None:
    op.execute(f"""
        UPDATE {table_name} AS resource
        SET owner_user_id = (
            SELECT users.id
            FROM users
            WHERE users.tenant_id = resource.tenant_id
            ORDER BY users.created_at, users.id
            LIMIT 1
        )
        WHERE resource.owner_user_id IS NULL
    """)
    op.execute(f"""
        UPDATE {table_name}
        SET visibility = 'tenant'
        WHERE owner_user_id IS NULL
    """)


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_users_id_tenant",
        "users",
        ["id", "tenant_id"],
    )

    _add_ownership("agents")
    _backfill_owner("agents")
    _add_ownership("super_agents")
    _backfill_owner("super_agents")


def _drop_ownership(table_name: str) -> None:
    op.drop_index(f"ix_{table_name}_owner", table_name=table_name)
    op.drop_constraint(
        f"ck_{table_name}_private_has_owner",
        table_name,
        type_="check",
    )
    op.drop_constraint(
        f"ck_{table_name}_visibility",
        table_name,
        type_="check",
    )
    op.drop_constraint(
        f"fk_{table_name}_owner_tenant",
        table_name,
        type_="foreignkey",
    )
    op.drop_column(table_name, "visibility")
    op.drop_column(table_name, "owner_user_id")


def downgrade() -> None:
    _drop_ownership("super_agents")
    _drop_ownership("agents")
    op.drop_constraint("uq_users_id_tenant", "users", type_="unique")