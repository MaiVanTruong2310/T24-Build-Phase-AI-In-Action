"""Restore the optional local password hash on drifted user tables.

Revision ID: 0026_users_password_hash_compat
Revises: 0025_booking_appointment_schedules
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0026_users_password_hash_compat"
down_revision: str | None = "0025_booking_appointment_schedules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable field expected by User when the baseline table pre-existed."""
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(512)")


def downgrade() -> None:
    """Keep credential data because this compatibility revision may find a pre-existing field."""
    raise RuntimeError("Cannot safely downgrade password_hash compatibility without risking credential data")
