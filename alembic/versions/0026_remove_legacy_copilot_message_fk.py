"""Compatibility marker for a migration already recorded by deployed databases.

Revision ID: 0026_remove_legacy_copilot_message_fk
Revises: 0024_schedule_service_and_busy_reason
"""

from collections.abc import Sequence

revision: str = "0026_remove_legacy_copilot_message_fk"
down_revision: str | None = "0024_schedule_service_and_busy_reason"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """The database version records this legacy change as already applied."""
    # Compatibility only: deployed databases with this version have already run
    # its operation; the original migration body is not present in this checkout.
    pass


def downgrade() -> None:
    """Keep deployed schemas aligned with their recorded migration history."""
    pass
