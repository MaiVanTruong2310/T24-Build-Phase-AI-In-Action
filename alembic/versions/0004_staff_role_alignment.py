"""Rename the coordinator role to staff."""

from alembic import op

revision = "0004_staff_role_alignment"
down_revision = "0003_medical_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Migrate existing coordinator users to the canonical staff role."""
    op.execute("UPDATE users SET role = 'staff' WHERE role = 'coordinator'")


def downgrade() -> None:
    """Restore the legacy coordinator role during rollback."""
    op.execute("UPDATE users SET role = 'coordinator' WHERE role = 'staff'")
