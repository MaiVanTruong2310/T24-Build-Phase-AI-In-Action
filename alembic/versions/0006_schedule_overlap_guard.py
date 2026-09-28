"""Prevent overlapping schedules for the same doctor.

Revision ID: 0006_schedule_overlap_guard
Revises: 0005_schedule_management
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0006_schedule_overlap_guard"
down_revision: Union[str, None] = "0005_schedule_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a PostgreSQL exclusion constraint for active schedule ranges."""
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute(
        """
        ALTER TABLE doctor_schedules
        ADD CONSTRAINT excl_doctor_schedule_time
        EXCLUDE USING gist (
            doctor_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        )
        WHERE (status <> 'cancelled')
        """
    )


def downgrade() -> None:
    """Remove the active schedule overlap guard."""
    op.drop_constraint("excl_doctor_schedule_time", "doctor_schedules", type_="exclude")
