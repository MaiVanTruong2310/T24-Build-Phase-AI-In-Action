"""Link finalized appointment schedules to their bookings.

Revision ID: 0025_booking_appointment_schedules
Revises: 0024_schedule_service_and_busy_reason
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025_booking_appointment_schedules"
down_revision: str | None = "0024_schedule_service_and_busy_reason"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store remaining capacity and associate each appointment with its booking."""
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS appointment_schedule_id UUID")
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_bookings_appointment_schedule_id'
                  AND conrelid = 'bookings'::regclass
            ) THEN
                ALTER TABLE bookings ADD CONSTRAINT fk_bookings_appointment_schedule_id
                    FOREIGN KEY (appointment_schedule_id) REFERENCES doctor_schedules(id) ON DELETE RESTRICT;
            END IF;
        END $$
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_bookings_appointment_schedule_id ON bookings (appointment_schedule_id)"
    )
    op.execute(
        """
        UPDATE doctor_schedules AS schedule
        SET capacity = GREATEST(
            schedule.capacity - (
                SELECT COUNT(*) FROM bookings
                WHERE bookings.schedule_id = schedule.id
                  AND bookings.status IN ('confirmed', 'attended')
            ),
            0
        )
        WHERE schedule.status = 'available'
        """
    )
    # Capacity slots can now have multiple linked appointment rows. Conflicts
    # between reusable staff schedules are checked under a doctor row lock.
    op.execute("ALTER TABLE doctor_schedules DROP CONSTRAINT IF EXISTS excl_doctor_schedule_time")


def downgrade() -> None:
    """Refuse downgrade if linked appointments or overlaps would be discarded."""
    connection = op.get_bind()
    linked_count = connection.scalar(sa.text("SELECT COUNT(*) FROM bookings WHERE appointment_schedule_id IS NOT NULL"))
    if linked_count:
        raise RuntimeError("Cannot downgrade while appointment schedules are linked to bookings")

    op.execute(
        """
        UPDATE doctor_schedules AS schedule
        SET capacity = schedule.capacity + (
            SELECT COUNT(*) FROM bookings
            WHERE bookings.schedule_id = schedule.id
              AND bookings.status IN ('confirmed', 'attended')
        )
        WHERE schedule.status = 'available'
        """
    )
    op.execute(
        """
        ALTER TABLE doctor_schedules
        ADD CONSTRAINT excl_doctor_schedule_time
        EXCLUDE USING gist (
            doctor_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        ) WHERE (status <> 'cancelled')
        """
    )
    op.drop_index("ix_bookings_appointment_schedule_id", table_name="bookings")
    op.drop_constraint("fk_bookings_appointment_schedule_id", "bookings", type_="foreignkey")
    op.drop_column("bookings", "appointment_schedule_id")
