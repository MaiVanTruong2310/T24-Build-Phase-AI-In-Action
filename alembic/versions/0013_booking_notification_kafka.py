"""Add booking approval expiry and Kafka delivery metadata."""

from typing import Sequence, Union

from alembic import op


revision: str = "0013_booking_notification_kafka"
down_revision: Union[str, None] = "0012_delivery_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Persist booking approval deadlines and notification publication state."""
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS hold boolean DEFAULT true NOT NULL")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS expired_at timestamptz")
    op.execute(
        "UPDATE bookings SET hold = (status = 'pending_approval'), expired_at = created_at + interval '24 hours'"
    )
    op.execute("ALTER TABLE bookings ALTER COLUMN expired_at SET NOT NULL")
    op.execute("ALTER TABLE bookings DROP CONSTRAINT IF EXISTS ck_bookings_status")
    op.execute(
        "ALTER TABLE bookings ADD CONSTRAINT ck_bookings_status "
        "CHECK (status IN ('pending_approval', 'confirmed', 'rejected', 'cancelled', 'expired'))"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_bookings_hold ON bookings (hold)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bookings_expired_at ON bookings (expired_at)")
    op.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS published_at timestamptz")
    op.execute(
        "UPDATE notifications SET status = 'discarded', updated_at = now() "
        "WHERE kind = 'appointment_reminder' AND dedupe_key LIKE 'booking:%:reminder:24h'"
    )


def downgrade() -> None:
    """Remove booking approval expiry and Kafka publication state."""
    op.drop_column("notifications", "published_at")
    op.drop_index("ix_bookings_expired_at", table_name="bookings")
    op.drop_index("ix_bookings_hold", table_name="bookings")
    op.drop_constraint("ck_bookings_status", "bookings", type_="check")
    op.create_check_constraint(
        "ck_bookings_status",
        "bookings",
        "status IN ('pending_approval', 'confirmed', 'rejected', 'cancelled')",
    )
    op.drop_column("bookings", "expired_at")
    op.drop_column("bookings", "hold")
