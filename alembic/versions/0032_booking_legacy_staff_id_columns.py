"""Ensure legacy booking patient and approver identifiers are mapped.

Revision ID: 0032_booking_legacy_staff_ids
Revises: 0031_notification_email_outbox
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0032_booking_legacy_staff_ids"
down_revision: str | None = "0031_notification_email_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Keep the legacy identifiers available on clean installs; live columns are preserved."""
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS patient_id UUID")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS approved_by_receptionist_id UUID")
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'bookings_patient_id_fkey'
                  AND conrelid = 'bookings'::regclass
            ) THEN
                ALTER TABLE bookings ADD CONSTRAINT bookings_patient_id_fkey
                    FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'bookings_approved_by_receptionist_id_fkey'
                  AND conrelid = 'bookings'::regclass
            ) THEN
                ALTER TABLE bookings ADD CONSTRAINT bookings_approved_by_receptionist_id_fkey
                    FOREIGN KEY (approved_by_receptionist_id) REFERENCES users(id);
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    """Keep these legacy columns on downgrade because they may contain existing application data."""
    pass
