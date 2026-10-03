"""Add schedule business types and notes for doctor busy periods."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0015_schedule_types_and_notes"
down_revision: Union[str, None] = "0014_remove_booking_holds"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Store consultation and non-bookable doctor schedule blocks together."""
    op.add_column(
        "doctor_schedules",
        sa.Column("type", sa.String(length=16), nullable=True, server_default="consultation"),
    )
    op.add_column("doctor_schedules", sa.Column("note", sa.Text(), nullable=True))
    op.execute("UPDATE doctor_schedules SET type = 'consultation' WHERE type IS NULL")
    op.alter_column("doctor_schedules", "type", nullable=False, server_default="consultation")
    op.alter_column("doctor_schedules", "facility_id", nullable=True)
    op.create_check_constraint(
        "ck_doctor_schedule_type",
        "doctor_schedules",
        "type IN ('consultation', 'busy', 'leave', 'other')",
    )
    op.execute("ALTER TABLE doctor_schedules DROP CONSTRAINT IF EXISTS excl_doctor_schedule_time")
    op.execute(
        """
        ALTER TABLE doctor_schedules
        ADD CONSTRAINT excl_doctor_schedule_time
        EXCLUDE USING gist (
            doctor_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        )
        WHERE (status <> 'cancelled' AND type = 'consultation')
        """
    )


def downgrade() -> None:
    """Refuse an unsafe downgrade when global busy schedules exist."""
    raise RuntimeError(
        "Downgrading schedule types is unsafe because busy schedules and nullable facilities cannot be restored automatically"
    )
