"""remove tools and MCP servers

Revision ID: 009_remove_tools_and_mcp
Revises: 008_skill_registry
Create Date: 2026-09-01
"""

from alembic import op


revision = "009_remove_tools_and_mcp"
down_revision = "008_skill_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("agent_mcp_servers")
    op.drop_table("agent_tools")
    op.drop_table("mcp_servers")
    op.drop_table("tools")


def downgrade() -> None:
    raise RuntimeError("Tool and MCP Server removal cannot be downgraded")