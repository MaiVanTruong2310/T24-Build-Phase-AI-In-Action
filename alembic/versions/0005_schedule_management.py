"""Add schedule ownership and cancellation fields.

Revision ID: 0005_schedule_management
Revises: 44837e30b196
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0005_schedule_management"
down_revision: Union[str, None] = "44837e30b196"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable actor references and the cancellation reason."""
    op.add_column(
        "doctor_schedules",
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "doctor_schedules",
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "doctor_schedules",
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_doctor_schedules_created_by", "doctor_schedules", ["created_by"])
    op.create_index("ix_doctor_schedules_updated_by", "doctor_schedules", ["updated_by"])
    op.create_foreign_key(
        "fk_doctor_schedules_created_by_users",
        "doctor_schedules",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_doctor_schedules_updated_by_users",
        "doctor_schedules",
        "users",
        ["updated_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove schedule ownership and cancellation fields."""
    op.drop_constraint("fk_doctor_schedules_updated_by_users", "doctor_schedules", type_="foreignkey")
    op.drop_constraint("fk_doctor_schedules_created_by_users", "doctor_schedules", type_="foreignkey")
    op.drop_index("ix_doctor_schedules_updated_by", table_name="doctor_schedules")
    op.drop_index("ix_doctor_schedules_created_by", table_name="doctor_schedules")
    op.drop_column("doctor_schedules", "cancellation_reason")
    op.drop_column("doctor_schedules", "updated_by")
    op.drop_column("doctor_schedules", "created_by")
