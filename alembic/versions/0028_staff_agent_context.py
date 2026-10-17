"""Create one private assistant conversation context per staff member."""

from collections.abc import Sequence

from alembic import op

revision: str = "0028_staff_agent_context"
down_revision: str | None = "0027_merge_schedule_and_copilot_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create missing unified conversation tables, then add staff ownership."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY,
            category VARCHAR(32) NOT NULL DEFAULT 'PATIENT_SUPPORT',
            mode VARCHAR(32) NOT NULL DEFAULT 'AI',
            status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
            patient_id UUID REFERENCES users(id) ON DELETE RESTRICT,
            created_by_type VARCHAR(32) NOT NULL DEFAULT 'PATIENT',
            created_by_id UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            closed_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_participants (
            id UUID PRIMARY KEY,
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            participant_type VARCHAR(32) NOT NULL,
            participant_id UUID,
            role VARCHAR(64),
            joined_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY,
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            sender_type VARCHAR(32) NOT NULL,
            sender_id UUID,
            message_type VARCHAR(32) NOT NULL DEFAULT 'TEXT',
            content TEXT,
            metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS handoffs (
            id UUID PRIMARY KEY,
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            from_actor_type VARCHAR(32) NOT NULL DEFAULT 'AGENT',
            to_actor_type VARCHAR(32) NOT NULL DEFAULT 'STAFF',
            reason VARCHAR(64) NOT NULL DEFAULT 'MANUAL_REVIEW',
            agent_confidence NUMERIC,
            requested_by_type VARCHAR(32) NOT NULL DEFAULT 'AGENT',
            requested_by_id UUID,
            assigned_staff_id UUID REFERENCES users(id) ON DELETE SET NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'REQUESTED',
            requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            accepted_at TIMESTAMPTZ,
            resolved_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS patient_chat_context (
            conversation_id UUID PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
            patient_id UUID REFERENCES users(id) ON DELETE RESTRICT,
            booking_id UUID,
            specialty_id UUID,
            current_stage VARCHAR(64) NOT NULL DEFAULT 'GENERAL_SUPPORT',
            context_data JSONB,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_conversations_patient_created ON conversations (patient_id, created_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversations_status ON conversations (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversations_category ON conversations (category)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_participants_conv_type ON conversation_participants (conversation_id, participant_type)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_conv_created ON messages (conversation_id, created_at)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS staff_agent_context (
            conversation_id UUID PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
            staff_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            context_patient_id UUID REFERENCES users(id) ON DELETE SET NULL,
            context_booking_id UUID,
            context_department_id UUID,
            task_type VARCHAR(64),
            context_data JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_staff_agent_context_staff UNIQUE (staff_id)
        )
        """
    )


def downgrade() -> None:
    """Refuse to drop persistent staff conversation context automatically."""
    raise RuntimeError("Staff assistant context contains durable conversation ownership; use a forward migration.")
