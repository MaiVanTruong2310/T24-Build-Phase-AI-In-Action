"""Add staff review metadata and approval workflow states."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0008_booking_approval_workflow"
down_revision: Union[str, None] = "0007_booking_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Persist staff decisions without changing existing booking decisions."""
    op.alter_column("bookings", "status", server_default="pending_approval")
    op.add_column("bookings", sa.Column("staff_note", sa.Text(), nullable=True))
    op.add_column("bookings", sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("bookings", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_bookings_reviewed_by_users",
        "bookings",
        "users",
        ["reviewed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_bookings_reviewed_by", "bookings", ["reviewed_by"])
    op.create_check_constraint(
        "ck_bookings_status",
        "bookings",
        "status IN ('pending_approval', 'confirmed', 'rejected', 'cancelled')",
    )


def downgrade() -> None:
    """Remove staff review metadata and approval status constraint."""
    op.drop_constraint("ck_bookings_status", "bookings", type_="check")
    op.drop_index("ix_bookings_reviewed_by", table_name="bookings")
    op.drop_constraint("fk_bookings_reviewed_by_users", "bookings", type_="foreignkey")
    op.drop_column("bookings", "reviewed_at")
    op.drop_column("bookings", "reviewed_by")
    op.drop_column("bookings", "staff_note")
    op.alter_column("bookings", "status", server_default="confirmed")
