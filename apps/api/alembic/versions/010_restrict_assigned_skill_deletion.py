"""prevent deletion of assigned skills

Revision ID: 010_restrict_skill_delete
Revises: 009_remove_tools_and_mcp
Create Date: 2026-09-01
"""

from alembic import op


revision = "010_restrict_skill_delete"
down_revision = "009_remove_tools_and_mcp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "agent_skills_skill_id_fkey",
        "agent_skills",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_agent_skills_skill_id",
        "agent_skills",
        "skill_registry",
        ["skill_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_agent_skills_skill_id",
        "agent_skills",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "agent_skills_skill_id_fkey",
        "agent_skills",
        "skill_registry",
        ["skill_id"],
        ["id"],
        ondelete="CASCADE",
    )