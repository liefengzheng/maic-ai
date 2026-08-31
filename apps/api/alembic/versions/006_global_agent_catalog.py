"""replace tenant isolation with a global agent catalog

Revision ID: 006_global_agent_catalog
Revises: 005_user_roles
Create Date: 2026-08-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "006_global_agent_catalog"
down_revision = "005_user_roles"
branch_labels = None
depends_on = None


RESOURCE_TABLES = ("agents", "tools", "mcp_servers", "super_agents")


def _make_slugs_global(table_name: str, old_constraint: str) -> None:
    op.execute(f"""
        WITH duplicates AS (
            SELECT id, row_number() OVER (PARTITION BY slug ORDER BY created_at, id) AS occurrence
            FROM {table_name}
        )
        UPDATE {table_name} AS resource
        SET slug = resource.slug || '-' || replace(resource.id::text, '-', '')
        FROM duplicates
        WHERE resource.id = duplicates.id AND duplicates.occurrence > 1
    """)
    op.drop_constraint(old_constraint, table_name, type_="unique")
    op.create_unique_constraint(f"uq_{table_name}_slug", table_name, ["slug"])


def upgrade() -> None:
    op.drop_constraint("fk_conversations_agent_tenant", "conversations", type_="foreignkey")
    op.drop_constraint("fk_conversations_super_agent_tenant", "conversations", type_="foreignkey")
    op.drop_constraint("fk_conversations_tenant_id", "conversations", type_="foreignkey")
    op.create_foreign_key(
        "fk_conversations_agent_id", "conversations", "agents", ["agent_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        "fk_conversations_super_agent_id", "conversations", "super_agents", ["super_agent_id"], ["id"], ondelete="RESTRICT"
    )

    op.drop_constraint("agent_tools_agent_id_tenant_id_fkey", "agent_tools", type_="foreignkey")
    op.drop_constraint("agent_tools_tool_id_tenant_id_fkey", "agent_tools", type_="foreignkey")
    op.drop_constraint("agent_tools_tenant_id_fkey", "agent_tools", type_="foreignkey")
    op.create_foreign_key(
        "fk_agent_tools_agent_id", "agent_tools", "agents", ["agent_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_agent_tools_tool_id", "agent_tools", "tools", ["tool_id"], ["id"], ondelete="CASCADE"
    )

    op.drop_constraint("agent_mcp_servers_agent_id_tenant_id_fkey", "agent_mcp_servers", type_="foreignkey")
    op.drop_constraint("agent_mcp_servers_mcp_server_id_tenant_id_fkey", "agent_mcp_servers", type_="foreignkey")
    op.drop_constraint("agent_mcp_servers_tenant_id_fkey", "agent_mcp_servers", type_="foreignkey")
    op.create_foreign_key(
        "fk_agent_mcp_servers_agent_id", "agent_mcp_servers", "agents", ["agent_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_agent_mcp_servers_mcp_server_id", "agent_mcp_servers", "mcp_servers", ["mcp_server_id"], ["id"], ondelete="CASCADE"
    )

    op.drop_constraint("super_agent_members_super_agent_id_tenant_id_fkey", "super_agent_members", type_="foreignkey")
    op.drop_constraint("super_agent_members_agent_id_tenant_id_fkey", "super_agent_members", type_="foreignkey")
    op.drop_constraint("super_agent_members_tenant_id_fkey", "super_agent_members", type_="foreignkey")
    op.create_foreign_key(
        "fk_super_agent_members_super_agent_id", "super_agent_members", "super_agents", ["super_agent_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_super_agent_members_agent_id", "super_agent_members", "agents", ["agent_id"], ["id"], ondelete="CASCADE"
    )

    for table_name in ("agents", "super_agents"):
        op.drop_constraint(f"fk_{table_name}_owner_tenant", table_name, type_="foreignkey")
        op.drop_constraint(f"ck_{table_name}_private_has_owner", table_name, type_="check")
        op.drop_constraint(f"ck_{table_name}_visibility", table_name, type_="check")
        op.drop_index(f"ix_{table_name}_owner", table_name=table_name)
        op.create_foreign_key(
            f"fk_{table_name}_owner_user_id", table_name, "users", ["owner_user_id"], ["id"], ondelete="CASCADE"
        )
        op.create_index(f"ix_{table_name}_owner_user_id", table_name, ["owner_user_id"])
        op.drop_column(table_name, "visibility")

    _make_slugs_global("agents", "uq_agents_tenant_slug")
    _make_slugs_global("tools", "uq_tools_tenant_slug")
    _make_slugs_global("mcp_servers", "uq_mcp_servers_tenant_slug")
    _make_slugs_global("super_agents", "uq_super_agents_tenant_slug")

    op.drop_index("ix_users_tenant_role", table_name="users")
    op.create_index("ix_users_role", "users", ["role"])
    op.drop_constraint("uq_users_id_tenant", "users", type_="unique")

    op.drop_column("conversations", "tenant_id")
    op.drop_column("agent_tools", "tenant_id")
    op.drop_column("agent_mcp_servers", "tenant_id")
    op.drop_column("super_agent_members", "tenant_id")

    for table_name in RESOURCE_TABLES:
        op.drop_index(f"ix_{table_name}_tenant_enabled", table_name=table_name)
        op.drop_constraint(f"uq_{table_name}_id_tenant", table_name, type_="unique")
        op.drop_constraint(f"{table_name}_tenant_id_fkey", table_name, type_="foreignkey")
        op.drop_column(table_name, "tenant_id")
        op.create_index(f"ix_{table_name}_enabled", table_name, ["enabled"])

    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_column("users", "tenant_id")
    op.drop_table("tenants")


def downgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    tenant_id = op.get_bind().execute(
        sa.text("INSERT INTO tenants (name, slug) VALUES ('Default Workspace', 'default') RETURNING id")
    ).scalar_one()

    op.add_column("users", sa.Column("tenant_id", postgresql.UUID(as_uuid=True)))
    op.execute(sa.text("UPDATE users SET tenant_id = :id").bindparams(id=tenant_id))
    op.alter_column("users", "tenant_id", nullable=False)
    op.create_foreign_key("fk_users_tenant_id", "users", "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.drop_index("ix_users_role", table_name="users")
    op.create_index("ix_users_tenant_role", "users", ["tenant_id", "role"])
    op.create_unique_constraint("uq_users_id_tenant", "users", ["id", "tenant_id"])

    for table_name in RESOURCE_TABLES:
        op.add_column(table_name, sa.Column("tenant_id", postgresql.UUID(as_uuid=True)))
        op.execute(sa.text(f"UPDATE {table_name} SET tenant_id = :id").bindparams(id=tenant_id))
        op.alter_column(table_name, "tenant_id", nullable=False)
        op.create_foreign_key(f"{table_name}_tenant_id_fkey", table_name, "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
        op.create_unique_constraint(f"uq_{table_name}_id_tenant", table_name, ["id", "tenant_id"])
        op.drop_constraint(f"uq_{table_name}_slug", table_name, type_="unique")
        op.create_unique_constraint(f"uq_{table_name}_tenant_slug", table_name, ["tenant_id", "slug"])
        op.drop_index(f"ix_{table_name}_enabled", table_name=table_name)
        op.create_index(f"ix_{table_name}_tenant_enabled", table_name, ["tenant_id", "enabled"])

    for table_name in ("agents", "super_agents"):
        op.drop_constraint(f"fk_{table_name}_owner_user_id", table_name, type_="foreignkey")
        op.drop_index(f"ix_{table_name}_owner_user_id", table_name=table_name)
        op.add_column(table_name, sa.Column("visibility", sa.String(16), nullable=False, server_default="tenant"))
        op.create_foreign_key(
            f"fk_{table_name}_owner_tenant", table_name, "users", ["owner_user_id", "tenant_id"], ["id", "tenant_id"], ondelete="CASCADE"
        )
        op.create_check_constraint(f"ck_{table_name}_visibility", table_name, "visibility IN ('private', 'tenant')")
        op.create_check_constraint(f"ck_{table_name}_private_has_owner", table_name, "visibility = 'tenant' OR owner_user_id IS NOT NULL")
        op.create_index(f"ix_{table_name}_owner", table_name, ["tenant_id", "owner_user_id"])

    for table_name in ("agent_tools", "agent_mcp_servers", "super_agent_members", "conversations"):
        op.add_column(table_name, sa.Column("tenant_id", postgresql.UUID(as_uuid=True)))
        op.execute(sa.text(f"UPDATE {table_name} SET tenant_id = :id").bindparams(id=tenant_id))
        op.alter_column(table_name, "tenant_id", nullable=False)

    op.drop_constraint("fk_agent_tools_agent_id", "agent_tools", type_="foreignkey")
    op.drop_constraint("fk_agent_tools_tool_id", "agent_tools", type_="foreignkey")
    op.create_foreign_key("agent_tools_tenant_id_fkey", "agent_tools", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("agent_tools_agent_id_tenant_id_fkey", "agent_tools", "agents", ["agent_id", "tenant_id"], ["id", "tenant_id"], ondelete="CASCADE")
    op.create_foreign_key("agent_tools_tool_id_tenant_id_fkey", "agent_tools", "tools", ["tool_id", "tenant_id"], ["id", "tenant_id"], ondelete="CASCADE")

    op.drop_constraint("fk_agent_mcp_servers_agent_id", "agent_mcp_servers", type_="foreignkey")
    op.drop_constraint("fk_agent_mcp_servers_mcp_server_id", "agent_mcp_servers", type_="foreignkey")
    op.create_foreign_key("agent_mcp_servers_tenant_id_fkey", "agent_mcp_servers", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("agent_mcp_servers_agent_id_tenant_id_fkey", "agent_mcp_servers", "agents", ["agent_id", "tenant_id"], ["id", "tenant_id"], ondelete="CASCADE")
    op.create_foreign_key("agent_mcp_servers_mcp_server_id_tenant_id_fkey", "agent_mcp_servers", "mcp_servers", ["mcp_server_id", "tenant_id"], ["id", "tenant_id"], ondelete="CASCADE")

    op.drop_constraint("fk_super_agent_members_super_agent_id", "super_agent_members", type_="foreignkey")
    op.drop_constraint("fk_super_agent_members_agent_id", "super_agent_members", type_="foreignkey")
    op.create_foreign_key("super_agent_members_tenant_id_fkey", "super_agent_members", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("super_agent_members_super_agent_id_tenant_id_fkey", "super_agent_members", "super_agents", ["super_agent_id", "tenant_id"], ["id", "tenant_id"], ondelete="CASCADE")
    op.create_foreign_key("super_agent_members_agent_id_tenant_id_fkey", "super_agent_members", "agents", ["agent_id", "tenant_id"], ["id", "tenant_id"], ondelete="CASCADE")

    op.drop_constraint("fk_conversations_agent_id", "conversations", type_="foreignkey")
    op.drop_constraint("fk_conversations_super_agent_id", "conversations", type_="foreignkey")
    op.create_foreign_key("fk_conversations_tenant_id", "conversations", "tenants", ["tenant_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_conversations_agent_tenant", "conversations", "agents", ["agent_id", "tenant_id"], ["id", "tenant_id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_conversations_super_agent_tenant", "conversations", "super_agents", ["super_agent_id", "tenant_id"], ["id", "tenant_id"], ondelete="RESTRICT")
