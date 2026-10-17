"""Allow staff private-examination bookings without a service."""

from collections.abc import Sequence

from alembic import op

revision: str = "0030_private_booking_service"
down_revision: str | None = "0029_staff_agent_read_views"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("bookings", "service_id", nullable=True)


def downgrade() -> None:
    op.alter_column("bookings", "service_id", nullable=False)
