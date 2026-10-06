"""Add compatibility identity and message capacity for canonical takeover rows."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021_workbench_takeover_compatibility"
down_revision: str | None = "0020_reconcile_model_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "coordination_cases",
        sa.Column("legacy_takeover_case_id", sa.Uuid(), nullable=True),
    )
    op.create_unique_constraint("uq_coord_case_legacy_takeover_id", "coordination_cases", ["legacy_takeover_case_id"])
    op.alter_column(
        "coordination_messages",
        "client_id",
        existing_type=sa.String(length=100),
        type_=sa.String(length=128),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "coordination_messages",
        "client_id",
        existing_type=sa.String(length=128),
        type_=sa.String(length=100),
        existing_nullable=False,
    )
    op.drop_constraint("uq_coord_case_legacy_takeover_id", "coordination_cases", type_="unique")
    op.drop_column("coordination_cases", "legacy_takeover_case_id")
