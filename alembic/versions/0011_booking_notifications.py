"""Add transactional booking notifications and reminder outbox rows."""

from typing import Sequence, Union

from alembic import op


revision: str = "0011_booking_notifications"
down_revision: Union[str, None] = "0010_booking_holds_idempotency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create durable in-app notifications and scheduled reminders."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id uuid NOT NULL PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            booking_id uuid REFERENCES bookings(id) ON DELETE SET NULL,
            kind varchar(32) NOT NULL,
            status varchar(16) DEFAULT 'pending' NOT NULL,
            title varchar(200) NOT NULL,
            message text NOT NULL,
            dedupe_key varchar(160) NOT NULL,
            available_at timestamptz NOT NULL,
            delivered_at timestamptz,
            read_at timestamptz,
            created_at timestamptz DEFAULT now() NOT NULL,
            updated_at timestamptz DEFAULT now() NOT NULL,
            CONSTRAINT ck_notifications_status
                CHECK (status IN ('pending', 'delivered', 'discarded'))
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_booking_id ON notifications (booking_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_kind ON notifications (kind)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_status ON notifications (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notifications_available_at ON notifications (available_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_status_available "
        "ON notifications (user_id, status, available_at)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_notifications_user_dedupe_key ON notifications (user_id, dedupe_key)"
    )
    # Older Alembic bootstrap databases used VARCHAR(32), which is shorter
    # than the newer revision identifiers.
    op.execute("ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)")


def downgrade() -> None:
    """Remove notification and reminder persistence."""
    op.drop_index("uq_notifications_user_dedupe_key", table_name="notifications")
    op.drop_index("ix_notifications_user_status_available", table_name="notifications")
    op.drop_index("ix_notifications_available_at", table_name="notifications")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_kind", table_name="notifications")
    op.drop_index("ix_notifications_booking_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
