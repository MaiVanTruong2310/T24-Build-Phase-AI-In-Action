"""Restore the documented booking approval deadline field."""

from collections.abc import Sequence

from alembic import op

revision: str = "0022_booking_expired_at"
down_revision: str | None = "0021_chat_history_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the deadline where missing and backfill pending/expired rows only."""
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS expired_at TIMESTAMP WITH TIME ZONE")
    op.execute(
        """
        UPDATE bookings
        SET expired_at = created_at + INTERVAL '24 hours'
        WHERE expired_at IS NULL AND status IN ('pending_approval', 'expired')
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_bookings_expired_at ON bookings (expired_at)")


def downgrade() -> None:
    """Avoid dropping a legacy column that may predate this revision."""
    raise RuntimeError(
        "Cannot safely downgrade booking expired_at: the column may have existed before this revision. "
        "Apply a forward migration if rollback is required."
    )
