"""Add persistent human-in-the-loop chat takeover workflow."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0018_chat_takeover"
down_revision: Union[str, None] = "0017_add_patient_details_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    json_type = postgresql.JSONB()

    op.create_table(
        "chat_takeover_cases",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("patient_user_id", uuid_type, nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("workflow_status", sa.String(length=64), nullable=False),
        sa.Column("summary", json_type, nullable=True),
        sa.Column("assigned_staff_id", uuid_type, nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_staff_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_user_id", "session_id", name="uq_chat_takeover_case_patient_session"),
    )
    op.create_index("ix_chat_takeover_cases_status_created", "chat_takeover_cases", ["status", "created_at"])
    op.create_index("ix_chat_takeover_cases_assigned", "chat_takeover_cases", ["assigned_staff_id", "status"])
    op.create_index("ix_chat_takeover_cases_patient_user_id", "chat_takeover_cases", ["patient_user_id"])
    op.create_index("ix_chat_takeover_cases_status", "chat_takeover_cases", ["status"])

    op.create_table(
        "chat_takeover_messages",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_id", uuid_type, nullable=False),
        sa.Column("author_type", sa.String(length=16), nullable=False),
        sa.Column("author_user_id", uuid_type, nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("client_message_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["case_id"], ["chat_takeover_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "client_message_id", name="uq_chat_takeover_message_client_id"),
    )
    op.create_index("ix_chat_takeover_messages_case_created", "chat_takeover_messages", ["case_id", "created_at"])

    op.create_table(
        "chat_takeover_audit_events",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_id", uuid_type, nullable=False),
        sa.Column("actor_user_id", uuid_type, nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("metadata", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["case_id"], ["chat_takeover_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_takeover_audit_case_created", "chat_takeover_audit_events", ["case_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_takeover_audit_case_created", table_name="chat_takeover_audit_events")
    op.drop_table("chat_takeover_audit_events")
    op.drop_index("ix_chat_takeover_messages_case_created", table_name="chat_takeover_messages")
    op.drop_table("chat_takeover_messages")
    op.drop_index("ix_chat_takeover_cases_status", table_name="chat_takeover_cases")
    op.drop_index("ix_chat_takeover_cases_patient_user_id", table_name="chat_takeover_cases")
    op.drop_index("ix_chat_takeover_cases_assigned", table_name="chat_takeover_cases")
    op.drop_index("ix_chat_takeover_cases_status_created", table_name="chat_takeover_cases")
    op.drop_table("chat_takeover_cases")
