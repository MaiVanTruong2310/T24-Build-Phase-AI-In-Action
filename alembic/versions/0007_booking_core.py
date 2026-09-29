"""Add service booking modes and patient bookings."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0007_booking_core"
down_revision: Union[str, None] = "0006_schedule_overlap_guard"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add explicit booking mode and direct-confirmed bookings."""
    op.add_column(
        "services",
        sa.Column("booking_mode", sa.String(length=20), server_default="group", nullable=False),
    )
    op.create_check_constraint(
        "ck_services_booking_mode",
        "services",
        "booking_mode IN ('group', 'doctor_visit')",
    )
    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("specialty_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_type", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("patient_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), server_default="confirmed", nullable=False),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["schedule_id"], ["doctor_schedules.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["specialty_id"], ["specialties.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"])
    op.create_index("ix_bookings_schedule_id", "bookings", ["schedule_id"])
    op.create_index("ix_bookings_service_id", "bookings", ["service_id"])
    op.create_index("ix_bookings_specialty_id", "bookings", ["specialty_id"])
    op.create_index("ix_bookings_status", "bookings", ["status"])
    op.create_index("ix_bookings_schedule_status", "bookings", ["schedule_id", "status"])
    op.create_index("ix_bookings_user_created_at", "bookings", ["user_id", "created_at"])


def downgrade() -> None:
    """Remove booking tables and the explicit service mode."""
    op.drop_index("ix_bookings_user_created_at", table_name="bookings")
    op.drop_index("ix_bookings_schedule_status", table_name="bookings")
    op.drop_index("ix_bookings_status", table_name="bookings")
    op.drop_index("ix_bookings_specialty_id", table_name="bookings")
    op.drop_index("ix_bookings_service_id", table_name="bookings")
    op.drop_index("ix_bookings_schedule_id", table_name="bookings")
    op.drop_index("ix_bookings_user_id", table_name="bookings")
    op.drop_table("bookings")
    op.drop_constraint("ck_services_booking_mode", "services", type_="check")
    op.drop_column("services", "booking_mode")
