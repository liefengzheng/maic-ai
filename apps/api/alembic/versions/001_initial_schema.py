"""create initial MAIC AI schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-08-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.create_table("users", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("email", sa.String(320), nullable=False), sa.Column("display_name", sa.String(80), nullable=False), sa.Column("avatar_url", sa.Text()), sa.Column("password_hash", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.UniqueConstraint("email", name="uq_users_email"))
    op.create_table("oauth_accounts", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("provider", sa.String(32), nullable=False), sa.Column("provider_account_id", sa.String(255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.UniqueConstraint("provider", "provider_account_id", name="uq_oauth_provider_account"))
    op.create_table("subscriptions", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("plan", sa.String(32), nullable=False), sa.Column("status", sa.String(32), nullable=False, server_default="active"), sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("ends_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_table("usage_ledger", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("amount", sa.Numeric(14, 4), nullable=False), sa.Column("reason", sa.String(64), nullable=False), sa.Column("reference_id", sa.String(128)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_table("workshop_slots", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False), sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False), sa.Column("capacity", sa.SmallInteger(), nullable=False, server_default="1"), sa.Column("remaining_seats", sa.SmallInteger(), nullable=False, server_default="1"), sa.Column("location", sa.String(120), nullable=False, server_default="线上沟通"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_table("workshop_bookings", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("slot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workshop_slots.id", ondelete="RESTRICT"), nullable=False), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("name", sa.String(80), nullable=False), sa.Column("organization", sa.String(120)), sa.Column("contact", sa.String(120), nullable=False), sa.Column("attendee_count", sa.SmallInteger(), nullable=False), sa.Column("topic", sa.String(160), nullable=False), sa.Column("note", sa.Text()), sa.Column("status", sa.String(32), nullable=False, server_default="pending"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_table("conversations", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(160), nullable=False, server_default="新对话"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_table("chat_messages", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")), sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(16), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"])
    op.create_index("ix_usage_ledger_user_created", "usage_ledger", ["user_id", "created_at"])
    op.create_index("ix_conversations_user_updated", "conversations", ["user_id", "updated_at"])
    op.create_index("ix_chat_messages_conversation_created", "chat_messages", ["conversation_id", "created_at"])

def downgrade() -> None:
    op.drop_table("chat_messages"); op.drop_table("conversations"); op.drop_table("workshop_bookings"); op.drop_table("workshop_slots"); op.drop_table("usage_ledger"); op.drop_table("subscriptions"); op.drop_table("oauth_accounts"); op.drop_table("users")