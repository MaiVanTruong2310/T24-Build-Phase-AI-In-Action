"""Allow retained expired bookings in the booking lifecycle."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_booking_expiry_status"
down_revision: str | None = "0018_chat_takeover"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


BOOKING_STATUSES = "'pending_approval', 'confirmed', 'rejected', 'cancelled', 'expired'"


def upgrade() -> None:
    """Permit the expiry worker to persist the documented terminal state."""
    op.drop_constraint("ck_bookings_status", "bookings", type_="check")
    op.create_check_constraint(
        "ck_bookings_status",
        "bookings",
        f"status IN ({BOOKING_STATUSES})",
    )


def downgrade() -> None:
    """Refuse to remove a status still used by retained booking history."""
    bind = op.get_bind()
    expired_count = bind.execute(sa.text("SELECT count(*) FROM bookings WHERE status = 'expired'")).scalar_one()
    if expired_count:
        raise RuntimeError(
            "Cannot downgrade booking expiry status while expired bookings exist; "
            "archive or resolve those records first."
        )

    op.drop_constraint("ck_bookings_status", "bookings", type_="check")
    op.create_check_constraint(
        "ck_bookings_status",
        "bookings",
        "status IN ('pending_approval', 'confirmed', 'rejected', 'cancelled')",
    )
