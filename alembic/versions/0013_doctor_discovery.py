"""Structured doctor discovery fields and facility assignments."""

from alembic import op

revision = "0013_doctor_discovery"
down_revision = "0012_consultation_coordination"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name in ("honors", "academic_ranks", "degrees"):
        op.execute(f"ALTER TABLE doctors ADD COLUMN {name} varchar(80)[] NOT NULL DEFAULT '{{}}'")
    for name in ("education", "work_history", "awards"):
        op.execute(f"ALTER TABLE doctors ADD COLUMN {name} text[] NOT NULL DEFAULT '{{}}'")
    op.execute("ALTER TABLE doctors ADD COLUMN position varchar(160)")
    op.execute("ALTER TABLE doctors ADD COLUMN experience_years integer CHECK (experience_years BETWEEN 0 AND 80)")
    op.execute("ALTER TABLE doctor_facilities ADD COLUMN position varchar(160)")
    op.execute("ALTER TABLE doctor_facilities ADD COLUMN is_primary boolean NOT NULL DEFAULT false")
    op.execute("CREATE INDEX ix_doctors_honors_gin ON doctors USING gin (honors)")
    op.execute("CREATE INDEX ix_doctors_academic_ranks_gin ON doctors USING gin (academic_ranks)")
    op.execute("CREATE INDEX ix_doctors_degrees_gin ON doctors USING gin (degrees)")
    op.execute("CREATE INDEX ix_doctors_languages_gin ON doctors USING gin (languages)")
    op.execute("CREATE INDEX ix_doctor_facilities_facility_dates ON doctor_facilities (facility_id, active_from, active_to)")
    op.execute("CREATE UNIQUE INDEX uq_doctor_facility_primary ON doctor_facilities (doctor_id) WHERE is_primary")


def downgrade() -> None:
    op.execute("DROP INDEX uq_doctor_facility_primary")
    op.execute("DROP INDEX ix_doctor_facilities_facility_dates")
    for name in ("degrees", "academic_ranks", "honors"):
        op.execute(f"DROP INDEX ix_doctors_{name}_gin")
    op.execute("ALTER TABLE doctor_facilities DROP COLUMN is_primary")
    op.execute("ALTER TABLE doctor_facilities DROP COLUMN position")
    for name in ("awards", "work_history", "education", "experience_years", "position", "degrees", "academic_ranks", "honors"):
        op.execute(f"ALTER TABLE doctors DROP COLUMN {name}")
