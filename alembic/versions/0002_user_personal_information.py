"""Add personal information to users."""

from alembic import op

revision = "0002_user_personal_information"
down_revision = "0001_auth_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add registration profile fields to the users table."""
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS date_of_birth DATE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(16)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS citizen_id VARCHAR(12)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS health_insurance_code VARCHAR(32)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_citizen_id ON users (citizen_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_health_insurance_code ON users (health_insurance_code)")


def downgrade() -> None:
    """Remove personal information fields from the users table."""
    op.drop_index("ix_users_health_insurance_code", table_name="users")
    op.drop_index("ix_users_citizen_id", table_name="users")
    op.drop_column("users", "health_insurance_code")
    op.drop_column("users", "citizen_id")
    op.drop_column("users", "gender")
    op.drop_column("users", "date_of_birth")
