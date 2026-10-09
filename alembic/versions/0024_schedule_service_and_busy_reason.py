"""Associate schedules with services and capture busy block details.

Revision ID: 0024_schedule_service_and_busy_reason
Revises: 0023_merge_workbench_booking_heads
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0024_schedule_service_and_busy_reason"
down_revision: Union[str, None] = "0023_merge_workbench_booking_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable schedule classification fields without changing legacy rows."""
    op.add_column("doctor_schedules", sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("doctor_schedules", sa.Column("busy_reason", sa.String(length=32), nullable=True))
    op.add_column("doctor_schedules", sa.Column("note", sa.Text(), nullable=True))
    op.create_index("ix_doctor_schedules_service_id", "doctor_schedules", ["service_id"])
    op.create_foreign_key(
        "fk_doctor_schedules_service_id_services",
        "doctor_schedules",
        "services",
        ["service_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_schedule_busy_reason_valid",
        "doctor_schedules",
        "busy_reason IS NULL OR busy_reason IN ('consultation', 'other_commitment')",
    )
    op.create_check_constraint(
        "ck_schedule_busy_reason_status",
        "doctor_schedules",
        "busy_reason IS NULL OR status = 'blocked'",
    )
    op.create_check_constraint(
        "ck_schedule_note_length",
        "doctor_schedules",
        "note IS NULL OR char_length(note) <= 500",
    )


def downgrade() -> None:
    """Remove schedule classification fields."""
    op.drop_constraint("ck_schedule_note_length", "doctor_schedules", type_="check")
    op.drop_constraint("ck_schedule_busy_reason_status", "doctor_schedules", type_="check")
    op.drop_constraint("ck_schedule_busy_reason_valid", "doctor_schedules", type_="check")
    op.drop_constraint("fk_doctor_schedules_service_id_services", "doctor_schedules", type_="foreignkey")
    op.drop_index("ix_doctor_schedules_service_id", table_name="doctor_schedules")
    op.drop_column("doctor_schedules", "note")
    op.drop_column("doctor_schedules", "busy_reason")
    op.drop_column("doctor_schedules", "service_id")
