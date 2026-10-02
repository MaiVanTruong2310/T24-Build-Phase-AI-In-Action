"""Add delivery metadata used by the independent notification consumer."""

from typing import Sequence, Union

from alembic import op


revision: str = "0012_notification_delivery_metadata"
down_revision: Union[str, None] = "0011_booking_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add provider metadata, retry state, and the dead-letter flag."""
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS channel varchar(32) DEFAULT 'in_app' NOT NULL")
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS provider varchar(64) DEFAULT 'database' NOT NULL")
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS attempt_count integer DEFAULT 0 NOT NULL")
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS error text")
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS dead_letter boolean DEFAULT false NOT NULL")
    op.execute("ALTER TABLE notifications DROP CONSTRAINT IF EXISTS ck_notifications_status")
    op.execute(
        "ALTER TABLE notifications ADD CONSTRAINT ck_notifications_status "
        "CHECK (status IN ('pending', 'processing', 'delivered', 'failed', 'discarded'))"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notifications_delivery_queue "
        "ON notifications (status, available_at, dead_letter)"
    )


def downgrade() -> None:
    """Remove consumer delivery metadata."""
    op.drop_index("ix_notifications_delivery_queue", table_name="notifications")
    op.drop_constraint("ck_notifications_status", "notifications", type_="check")
    op.create_check_constraint(
        "ck_notifications_status",
        "notifications",
        "status IN ('pending', 'delivered', 'discarded')",
    )
    op.drop_column("notifications", "dead_letter")
    op.drop_column("notifications", "error")
    op.drop_column("notifications", "attempt_count")
    op.drop_column("notifications", "provider")
    op.drop_column("notifications", "channel")
