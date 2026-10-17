"""Add schedule ownership and cancellation fields.

Revision ID: 0005_schedule_management
Revises: 44837e30b196
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_schedule_management"
down_revision: str | None = "44837e30b196"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add schedule metadata while tolerating columns already present in the database."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("doctor_schedules")}
    for name, type_ in (
        ("created_by", postgresql.UUID(as_uuid=True)),
        ("updated_by", postgresql.UUID(as_uuid=True)),
        ("cancellation_reason", sa.Text()),
    ):
        if name not in columns:
            op.add_column("doctor_schedules", sa.Column(name, type_, nullable=True))

    indexes = {index["name"] for index in inspector.get_indexes("doctor_schedules")}
    for name, column in (
        ("ix_doctor_schedules_created_by", "created_by"),
        ("ix_doctor_schedules_updated_by", "updated_by"),
    ):
        if name not in indexes:
            op.create_index(name, "doctor_schedules", [column])

    foreign_keys = {key["name"] for key in inspector.get_foreign_keys("doctor_schedules")}
    for name, column in (
        ("fk_doctor_schedules_created_by_users", "created_by"),
        ("fk_doctor_schedules_updated_by_users", "updated_by"),
    ):
        if name not in foreign_keys:
            op.create_foreign_key(name, "doctor_schedules", "users", [column], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    """Remove schedule ownership and cancellation fields."""
    op.drop_constraint("fk_doctor_schedules_updated_by_users", "doctor_schedules", type_="foreignkey")
    op.drop_constraint("fk_doctor_schedules_created_by_users", "doctor_schedules", type_="foreignkey")
    op.drop_index("ix_doctor_schedules_updated_by", table_name="doctor_schedules")
    op.drop_index("ix_doctor_schedules_created_by", table_name="doctor_schedules")
    op.drop_column("doctor_schedules", "cancellation_reason")
    op.drop_column("doctor_schedules", "updated_by")
    op.drop_column("doctor_schedules", "created_by")
