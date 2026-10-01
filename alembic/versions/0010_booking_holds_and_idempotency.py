"""Add booking holds and idempotent booking creation metadata."""

from typing import Sequence, Union

from alembic import op


revision: str = "0010_booking_holds_idempotency"
down_revision: Union[str, None] = "0009_booking_requested_time"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create expiring holds and protect booking retries by user/key."""
    # Some development databases were bootstrapped with ORM metadata before
    # Alembic was enabled. Keep this migration safe for that already-existing
    # schema instead of asking developers to drop booking_holds.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS booking_holds (
            id uuid NOT NULL PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            schedule_id uuid NOT NULL REFERENCES doctor_schedules(id) ON DELETE RESTRICT,
            service_id uuid NOT NULL REFERENCES services(id) ON DELETE RESTRICT,
            specialty_id uuid NOT NULL REFERENCES specialties(id) ON DELETE RESTRICT,
            status varchar(16) DEFAULT 'active' NOT NULL,
            expires_at timestamptz NOT NULL,
            released_at timestamptz,
            created_at timestamptz DEFAULT now() NOT NULL,
            updated_at timestamptz DEFAULT now() NOT NULL,
            CONSTRAINT ck_booking_holds_status
                CHECK (status IN ('active', 'released', 'expired', 'consumed'))
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_booking_holds_user_id ON booking_holds (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_booking_holds_schedule_id ON booking_holds (schedule_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_booking_holds_schedule_status ON booking_holds (schedule_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_booking_holds_expires_at ON booking_holds (expires_at)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_booking_holds_active_user_schedule "
        "ON booking_holds (user_id, schedule_id) WHERE status = 'active'"
    )

    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS hold_id uuid")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS idempotency_key varchar(128)")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS idempotency_hash varchar(64)")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_bookings_hold_id_booking_holds'
            ) THEN
                ALTER TABLE bookings
                ADD CONSTRAINT fk_bookings_hold_id_booking_holds
                FOREIGN KEY (hold_id) REFERENCES booking_holds(id) ON DELETE SET NULL;
            END IF;
        END $$
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_bookings_hold_id ON bookings (hold_id)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_bookings_user_id_idempotency_key "
        "ON bookings (user_id, idempotency_key) WHERE idempotency_key IS NOT NULL"
    )


def downgrade() -> None:
    """Remove hold and idempotency metadata."""
    op.drop_index("uq_bookings_user_id_idempotency_key", table_name="bookings")
    op.drop_index("ix_bookings_hold_id", table_name="bookings")
    op.drop_constraint("fk_bookings_hold_id_booking_holds", "bookings", type_="foreignkey")
    op.drop_column("bookings", "idempotency_hash")
    op.drop_column("bookings", "idempotency_key")
    op.drop_column("bookings", "hold_id")
    op.drop_index("uq_booking_holds_active_user_schedule", table_name="booking_holds")
    op.drop_index("ix_booking_holds_expires_at", table_name="booking_holds")
    op.drop_index("ix_booking_holds_schedule_status", table_name="booking_holds")
    op.drop_index("ix_booking_holds_schedule_id", table_name="booking_holds")
    op.drop_index("ix_booking_holds_user_id", table_name="booking_holds")
    op.drop_table("booking_holds")
