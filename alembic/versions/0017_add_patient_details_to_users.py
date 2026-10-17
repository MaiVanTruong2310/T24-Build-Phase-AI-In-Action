"""Store structured patient profile details on users."""

from typing import Sequence, Union

from alembic import op


revision: str = "0017_add_patient_details_to_users"
down_revision: Union[str, None] = "0016_add_auth_user_id_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS patient_details JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS patient_details")
