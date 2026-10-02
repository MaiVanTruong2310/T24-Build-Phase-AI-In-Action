"""Remove the redundant temporary booking hold workflow."""

from typing import Sequence, Union

from alembic import op


revision: str = "0014_remove_booking_holds"
down_revision: Union[str, None] = "0013_booking_notification_kafka"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop hold persistence after pending bookings became reservations."""
    op.execute("ALTER TABLE bookings DROP CONSTRAINT IF EXISTS ck_bookings_status")
    op.execute(
        "ALTER TABLE bookings ADD CONSTRAINT ck_bookings_status "
        "CHECK (status IN ('pending_approval', 'confirmed', 'rejected', 'cancelled', 'expired'))"
    )
    op.execute("ALTER TABLE bookings DROP CONSTRAINT IF EXISTS fk_bookings_hold_id_booking_holds")
    op.execute("DROP INDEX IF EXISTS ix_bookings_hold_id")
    op.execute("ALTER TABLE bookings DROP COLUMN IF EXISTS hold_id")
    op.execute("DROP INDEX IF EXISTS ix_bookings_hold")
    op.execute("ALTER TABLE bookings DROP COLUMN IF EXISTS hold")
    op.execute("DROP TABLE IF EXISTS booking_holds")


def downgrade() -> None:
    """Hold data is intentionally not recreated by downgrade."""
    raise RuntimeError("The booking hold workflow cannot be restored automatically")
