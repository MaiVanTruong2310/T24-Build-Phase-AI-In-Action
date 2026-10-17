"""Merge the schedule and deployed Copilot migration branches.

Revision ID: 0027_merge_schedule_and_copilot_heads
Revises: 0026_remove_legacy_copilot_message_fk, 0026_users_password_hash_compat
"""

from collections.abc import Sequence

revision: str = "0027_merge_schedule_and_copilot_heads"
down_revision: tuple[str, str] = (
    "0026_remove_legacy_copilot_message_fk",
    "0026_users_password_hash_compat",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge both schema histories without additional changes."""


def downgrade() -> None:
    """Merge revisions have no independent schema operation to reverse."""
