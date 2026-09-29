"""Allow patients to request a time before staff publishes a schedule."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0009_booking_requested_time"
down_revision: Union[str, None] = "0008_booking_approval_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Store the requested doctor, facility and time on every booking."""
    op.add_column("bookings", sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("bookings", sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("bookings", sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bookings", sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("bookings", "schedule_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)

    op.execute(
        sa.text(
            """
            UPDATE bookings AS b
            SET doctor_id = s.doctor_id,
                facility_id = s.facility_id,
                starts_at = s.starts_at,
                ends_at = s.ends_at
            FROM doctor_schedules AS s
            WHERE b.schedule_id = s.id
            """
        )
    )

    op.alter_column("bookings", "doctor_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("bookings", "facility_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("bookings", "starts_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    op.alter_column("bookings", "ends_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    op.create_foreign_key(
        "fk_bookings_doctor_id_doctors",
        "bookings",
        "doctors",
        ["doctor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_bookings_facility_id_facilities",
        "bookings",
        "facilities",
        ["facility_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_bookings_doctor_id", "bookings", ["doctor_id"])
    op.create_index("ix_bookings_facility_id", "bookings", ["facility_id"])
    op.create_index("ix_bookings_starts_at", "bookings", ["starts_at"])


def downgrade() -> None:
    """Revert requested-time booking storage."""
    op.drop_index("ix_bookings_starts_at", table_name="bookings")
    op.drop_index("ix_bookings_facility_id", table_name="bookings")
    op.drop_index("ix_bookings_doctor_id", table_name="bookings")
    op.drop_constraint("fk_bookings_facility_id_facilities", "bookings", type_="foreignkey")
    op.drop_constraint("fk_bookings_doctor_id_doctors", "bookings", type_="foreignkey")
    op.drop_column("bookings", "ends_at")
    op.drop_column("bookings", "starts_at")
    op.drop_column("bookings", "facility_id")
    op.drop_column("bookings", "doctor_id")
    op.alter_column("bookings", "schedule_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
