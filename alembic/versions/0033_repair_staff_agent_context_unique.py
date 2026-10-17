"""Restore the per-staff unique constraint for existing installations."""

from collections.abc import Sequence

from alembic import op

revision: str = "0033_staff_agent_context_unique"
down_revision: str | None = "0032_booking_legacy_staff_ids"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Repair databases where migration 0028 found a pre-existing table."""
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_staff_agent_context_staff'
                  AND conrelid = 'staff_agent_context'::regclass
            ) THEN
                IF EXISTS (
                    SELECT 1
                    FROM staff_agent_context
                    GROUP BY staff_id
                    HAVING count(*) > 1
                ) THEN
                    RAISE EXCEPTION
                        'Cannot restore staff_agent_context staff_id uniqueness: duplicate staff rows require manual reconciliation';
                END IF;

                ALTER TABLE staff_agent_context
                    ADD CONSTRAINT uq_staff_agent_context_staff UNIQUE (staff_id);
            END IF;
        END;
        $$
        """
    )


def downgrade() -> None:
    """Keep the invariant needed by per-staff conversation ownership."""
    pass
