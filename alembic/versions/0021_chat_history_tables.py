"""Create durable authenticated chat history tables."""

from collections.abc import Sequence

from alembic import op

revision: str = "0021_chat_history_tables"
down_revision: str | None = "0020_reconcile_model_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the tables required by ChatHistoryService without replacing data."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_conversations (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_id VARCHAR(200) NOT NULL,
            title VARCHAR(200) NOT NULL,
            patient_profile_id UUID REFERENCES patient_profiles(id) ON DELETE RESTRICT,
            checkpoint JSONB NOT NULL DEFAULT '{}'::jsonb,
            lease_token UUID,
            busy_until TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_chat_conversations_user_session UNIQUE (user_id, session_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_turns (
            id UUID PRIMARY KEY,
            conversation_id UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
            request_id UUID NOT NULL,
            user_text TEXT NOT NULL,
            assistant_text TEXT,
            result JSONB,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_chat_turns_conversation_request UNIQUE (conversation_id, request_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_conversations_user_updated ON chat_conversations (user_id, updated_at DESC, id DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_turns_conversation_created ON chat_turns (conversation_id, created_at DESC, id DESC)"
    )


def downgrade() -> None:
    """Refuse destructive rollback of durable chat history."""
    raise RuntimeError("Chat history tables contain durable user data; apply a forward migration instead.")
