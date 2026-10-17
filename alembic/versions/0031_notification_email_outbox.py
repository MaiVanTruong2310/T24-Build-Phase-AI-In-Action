"""Add durable email delivery metadata to notifications.

Revision ID: 0031_notification_email_outbox
Revises: 0030_private_booking_service
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0031_notification_email_outbox"
down_revision: str | None = "0030_private_booking_service"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS channel VARCHAR(16) NOT NULL DEFAULT 'in_app'")
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS recipient_email VARCHAR(320)")
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS last_error VARCHAR(80)")
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS processing_at TIMESTAMPTZ")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notifications_email_queue ON notifications (channel, status, available_at)"
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_email_queue", table_name="notifications")
    op.drop_column("notifications", "last_error")
    op.drop_column("notifications", "processing_at")
    op.drop_column("notifications", "attempt_count")
    op.drop_column("notifications", "recipient_email")
    op.drop_column("notifications", "channel")
