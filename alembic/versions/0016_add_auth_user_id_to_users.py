"""Link application users to the external auth provider identity."""

from typing import Sequence, Union

from alembic import op


revision: str = "0016_add_auth_user_id_to_users"
down_revision: Union[str, None] = "0015_coordinator_workbench"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_user_id UUID")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_auth_user_id
        ON users (auth_user_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_auth_user_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS auth_user_id")
