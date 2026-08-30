"""add tenant-scoped agent catalog

Revision ID: 002_tenant_agent_catalog
Revises: 001_initial_schema
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "002_tenant_agent_catalog"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def _uuid() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
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
    )


def upgrade() -> None:
    op.create_table(
        "tenants",
        _uuid(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        *_timestamps(),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
        sa.CheckConstraint("status IN ('active', 'suspended')", name="ck_tenants_status"),
    )

    op.add_column("users", sa.Column("tenant_id", postgresql.UUID(as_uuid=True)))
    op.execute("""
        INSERT INTO tenants (id, name, slug)
        SELECT gen_random_uuid(), display_name || ' Workspace', 'user-' || id::text
        FROM users
    """)
    op.execute("""
        UPDATE users AS users
        SET tenant_id = tenants.id
        FROM tenants
        WHERE tenants.slug = 'user-' || users.id::text
          AND users.tenant_id IS NULL
    """)
    op.alter_column("users", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_users_tenant_id",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.create_table(
        "agents",
        _uuid(),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_agents_tenant_slug"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_agents_id_tenant"),
    )
    op.create_index("ix_agents_tenant_enabled", "agents", ["tenant_id", "enabled"])

    op.create_table(
        "tools",
        _uuid(),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("handler", sa.String(255), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_tools_tenant_slug"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_tools_id_tenant"),
    )
    op.create_index("ix_tools_tenant_enabled", "tools", ["tenant_id", "enabled"])

    op.create_table(
        "mcp_servers",
        _uuid(),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("transport", sa.String(32), nullable=False, server_default="http"),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_mcp_servers_tenant_slug"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_mcp_servers_id_tenant"),
        sa.CheckConstraint("transport IN ('http', 'sse')", name="ck_mcp_servers_transport"),
    )
    op.create_index(
        "ix_mcp_servers_tenant_enabled",
        "mcp_servers",
        ["tenant_id", "enabled"],
    )

    op.create_table(
        "agent_tools",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["agent_id", "tenant_id"],
            ["agents.id", "agents.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tool_id", "tenant_id"],
            ["tools.id", "tools.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("agent_id", "tool_id", name="pk_agent_tools"),
    )

    op.create_table(
        "agent_mcp_servers",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mcp_server_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["agent_id", "tenant_id"],
            ["agents.id", "agents.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["mcp_server_id", "tenant_id"],
            ["mcp_servers.id", "mcp_servers.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("agent_id", "mcp_server_id", name="pk_agent_mcp_servers"),
    )

    op.create_table(
        "super_agents",
        _uuid(),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_super_agents_tenant_slug"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_super_agents_id_tenant"),
    )
    op.create_index(
        "ix_super_agents_tenant_enabled",
        "super_agents",
        ["tenant_id", "enabled"],
    )

    op.create_table(
        "super_agent_members",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("super_agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["super_agent_id", "tenant_id"],
            ["super_agents.id", "super_agents.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id", "tenant_id"],
            ["agents.id", "agents.tenant_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("super_agent_id", "agent_id", name="pk_super_agent_members"),
        sa.UniqueConstraint("super_agent_id", "position", name="uq_super_agent_members_position"),
    )


def downgrade() -> None:
    op.drop_table("super_agent_members")
    op.drop_index("ix_super_agents_tenant_enabled", table_name="super_agents")
    op.drop_table("super_agents")
    op.drop_table("agent_mcp_servers")
    op.drop_table("agent_tools")
    op.drop_index("ix_mcp_servers_tenant_enabled", table_name="mcp_servers")
    op.drop_table("mcp_servers")
    op.drop_index("ix_tools_tenant_enabled", table_name="tools")
    op.drop_table("tools")
    op.drop_index("ix_agents_tenant_enabled", table_name="agents")
    op.drop_table("agents")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_column("users", "tenant_id")
    op.drop_table("tenants")