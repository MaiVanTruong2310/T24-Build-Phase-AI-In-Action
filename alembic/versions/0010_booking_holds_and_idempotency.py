"""Add booking holds and idempotent booking creation metadata."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0010_booking_holds_idempotency"
down_revision: Union[str, None] = "0009_booking_requested_time"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create expiring holds and protect booking retries by user/key."""
    op.create_table(
        "booking_holds",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("specialty_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["schedule_id"], ["doctor_schedules.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["specialty_id"], ["specialties.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('active', 'released', 'expired', 'consumed')", name="ck_booking_holds_status"),
    )
    op.create_index("ix_booking_holds_user_id", "booking_holds", ["user_id"])
    op.create_index("ix_booking_holds_schedule_id", "booking_holds", ["schedule_id"])
    op.create_index("ix_booking_holds_schedule_status", "booking_holds", ["schedule_id", "status"])
    op.create_index("ix_booking_holds_expires_at", "booking_holds", ["expires_at"])
    op.create_index(
        "uq_booking_holds_active_user_schedule",
        "booking_holds",
        ["user_id", "schedule_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.add_column("bookings", sa.Column("hold_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("bookings", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("bookings", sa.Column("idempotency_hash", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_bookings_hold_id_booking_holds",
        "bookings",
        "booking_holds",
        ["hold_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_bookings_hold_id", "bookings", ["hold_id"], unique=True)
    op.create_index(
        "uq_bookings_user_id_idempotency_key",
        "bookings",
        ["user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove hold and idempotency metadata."""
    op.drop_index("uq_bookings_user_id_idempotency_key", table_name="bookings")
    op.drop_index("ix_bookings_hold_id", table_name="bookings")
    op.drop_constraint("fk_bookings_hold_id_booking_holds", "bookings", type_="foreignkey")
    op.drop_column("bookings", "idempotency_hash")
    op.drop_column("bookings", "idempotency_key")
    op.drop_column("bookings", "hold_id")
    op.drop_index("uq_booking_holds_active_user_schedule", table_name="booking_holds")
    op.drop_index("ix_booking_holds_expires_at", table_name="booking_holds")
    op.drop_index("ix_booking_holds_schedule_status", table_name="booking_holds")
    op.drop_index("ix_booking_holds_schedule_id", table_name="booking_holds")
    op.drop_index("ix_booking_holds_user_id", table_name="booking_holds")
    op.drop_table("booking_holds")
