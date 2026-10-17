"""Bảng ui_visibility: admin bật/tắt hiển thị từng thành phần giao diện người dùng."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0034_ui_visibility"
down_revision: str | None = "0033_staff_agent_context_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ui_visibility",
        sa.Column("key", sa.String(length=120), primary_key=True),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("ui_visibility", if_exists=True)
