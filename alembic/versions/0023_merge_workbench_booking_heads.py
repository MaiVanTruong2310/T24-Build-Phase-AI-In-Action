"""Merge the workbench compatibility and booking expiry migration branches."""

from collections.abc import Sequence

revision: str = "0023_merge_workbench_booking_heads"
down_revision: str | Sequence[str] | None = (
    "0021_workbench_takeover_compatibility",
    "0022_booking_expired_at",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge revision history; both parent migrations own their schema changes."""


def downgrade() -> None:
    """A merge revision has no independent schema changes."""
