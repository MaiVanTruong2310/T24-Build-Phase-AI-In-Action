"""Reconcile drifted databases with current booking and doctor models."""

from collections.abc import Sequence

from alembic import op

revision: str = "0020_reconcile_model_schema"
down_revision: str | None = "0019_booking_expiry_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add missing mapped fields and indexes without removing legacy data."""
    _add_booking_fields()
    _add_doctor_fields()
    _tighten_required_booking_fields()
    _add_missing_foreign_keys()
    _validate_unique_index_data()
    _add_missing_indexes()
    _add_historical_doctor_constraints()


def _add_booking_fields() -> None:
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS patient_profile_id UUID")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS requested_by_user_id UUID")
    op.execute("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS hold_id UUID")


def _add_doctor_fields() -> None:
    op.execute("ALTER TABLE doctor_facilities ADD COLUMN IF NOT EXISTS position VARCHAR(160)")
    op.execute("ALTER TABLE doctor_facilities ADD COLUMN IF NOT EXISTS is_primary BOOLEAN")
    op.execute("UPDATE doctor_facilities SET is_primary = false WHERE is_primary IS NULL")
    op.execute("ALTER TABLE doctor_facilities ALTER COLUMN is_primary SET DEFAULT false")
    op.execute("ALTER TABLE doctor_facilities ALTER COLUMN is_primary SET NOT NULL")

    op.execute("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS professional_role VARCHAR(40)")
    _backfill_professional_role()
    op.execute("ALTER TABLE doctors ALTER COLUMN professional_role SET DEFAULT 'Bác sĩ'")
    op.execute("ALTER TABLE doctors ALTER COLUMN professional_role SET NOT NULL")

    for name in ("honors", "academic_ranks", "degrees"):
        _add_doctor_array(name, "VARCHAR(80)[]")
    _add_doctor_array("languages", "TEXT[]")
    for name in ("education", "work_history", "awards"):
        _add_doctor_array(name, "TEXT[]")

    op.execute("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS position VARCHAR(160)")
    op.execute("ALTER TABLE doctors ADD COLUMN IF NOT EXISTS experience_years INTEGER")


def _add_doctor_array(name: str, sql_type: str) -> None:
    """Restore an array field with safe values for records already in the table."""
    op.execute(f"ALTER TABLE doctors ADD COLUMN IF NOT EXISTS {name} {sql_type}")
    op.execute(f"UPDATE doctors SET {name} = '{{}}'::{sql_type} WHERE {name} IS NULL")
    op.execute(f"ALTER TABLE doctors ALTER COLUMN {name} SET DEFAULT '{{}}'::{sql_type}")
    op.execute(f"ALTER TABLE doctors ALTER COLUMN {name} SET NOT NULL")


def _backfill_professional_role() -> None:
    nurse = "\u0110i\u1ec1u d\u01b0\u1ee1ng"
    pharmacist = "D\u01b0\u1ee3c s\u0129"
    technician = "K\u1ef9 thu\u1eadt vi\u00ean"
    specialist = "Chuy\u00ean gia"
    physician = "B\u00e1c s\u0129"
    op.execute(
        f"""
        UPDATE doctors
        SET professional_role = CASE
            WHEN title ILIKE '%{nurse}%' THEN '{nurse}'
            WHEN title ILIKE '%{pharmacist}%' THEN '{pharmacist}'
            WHEN title ILIKE '%{technician}%' THEN '{technician}'
            WHEN title ILIKE '%{specialist}%' THEN '{specialist}'
            ELSE '{physician}'
        END
        WHERE professional_role IS NULL
        """
    )


def _tighten_required_booking_fields() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM bookings WHERE doctor_id IS NULL) THEN
                RAISE EXCEPTION 'Cannot require bookings.doctor_id: NULL rows exist';
            END IF;
            IF EXISTS (SELECT 1 FROM bookings WHERE facility_id IS NULL) THEN
                RAISE EXCEPTION 'Cannot require bookings.facility_id: NULL rows exist';
            END IF;
            IF EXISTS (SELECT 1 FROM bookings WHERE starts_at IS NULL) THEN
                RAISE EXCEPTION 'Cannot require bookings.starts_at: NULL rows exist';
            END IF;
            IF EXISTS (SELECT 1 FROM bookings WHERE ends_at IS NULL) THEN
                RAISE EXCEPTION 'Cannot require bookings.ends_at: NULL rows exist';
            END IF;
            IF EXISTS (SELECT 1 FROM doctor_schedules WHERE facility_id IS NULL) THEN
                RAISE EXCEPTION 'Cannot require doctor_schedules.facility_id: NULL rows exist';
            END IF;
        END $$;
        """
    )
    for table_name, column_name in (
        ("bookings", "doctor_id"),
        ("bookings", "facility_id"),
        ("bookings", "starts_at"),
        ("bookings", "ends_at"),
        ("doctor_schedules", "facility_id"),
    ):
        op.alter_column(table_name, column_name, nullable=False)


def _add_missing_foreign_keys() -> None:
    constraints = (
        (
            "fk_bookings_patient_profile_id_patient_profiles",
            "patient_profile_id",
            "patient_profiles",
            "RESTRICT",
        ),
        ("fk_bookings_requested_by_user_id_users", "requested_by_user_id", "users", "RESTRICT"),
        ("fk_bookings_hold_id_booking_holds", "hold_id", "booking_holds", "SET NULL"),
    )
    for name, column_name, referred_table, on_delete in constraints:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = '{name}' AND conrelid = 'bookings'::regclass
                ) THEN
                    ALTER TABLE bookings ADD CONSTRAINT {name}
                    FOREIGN KEY ({column_name}) REFERENCES {referred_table}(id) ON DELETE {on_delete};
                END IF;
            END $$;
            """
        )


def _validate_unique_index_data() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM bookings
                WHERE hold_id IS NOT NULL
                GROUP BY hold_id HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'Cannot add unique bookings.hold_id index: duplicate hold IDs exist';
            END IF;
            IF EXISTS (
                SELECT 1 FROM doctor_facilities
                WHERE is_primary
                GROUP BY doctor_id HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'Cannot add primary doctor-facility index: multiple primary locations exist';
            END IF;
        END $$;
        """
    )


def _add_missing_indexes() -> None:
    statements = (
        "CREATE INDEX IF NOT EXISTS ix_bookings_patient_profile_id ON bookings (patient_profile_id)",
        "CREATE INDEX IF NOT EXISTS ix_bookings_requested_by_user_id ON bookings (requested_by_user_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_bookings_hold_id ON bookings (hold_id)",
        "CREATE INDEX IF NOT EXISTS ix_chat_takeover_cases_assigned_staff_id ON chat_takeover_cases (assigned_staff_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_doctor_facility_primary ON doctor_facilities (doctor_id) WHERE is_primary",
        "CREATE INDEX IF NOT EXISTS ix_doctor_facilities_facility_dates ON doctor_facilities (facility_id, active_from, active_to)",
        "CREATE INDEX IF NOT EXISTS ix_doctors_honors_gin ON doctors USING gin (honors)",
        "CREATE INDEX IF NOT EXISTS ix_doctors_academic_ranks_gin ON doctors USING gin (academic_ranks)",
        "CREATE INDEX IF NOT EXISTS ix_doctors_degrees_gin ON doctors USING gin (degrees)",
        "CREATE INDEX IF NOT EXISTS ix_doctors_languages_gin ON doctors USING gin (languages)",
        "CREATE INDEX IF NOT EXISTS ix_doctors_role_status ON doctors (professional_role, status, booking_enabled)",
    )
    for statement in statements:
        op.execute(statement)


def _add_historical_doctor_constraints() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM doctors
                WHERE experience_years IS NOT NULL
                  AND (experience_years < 0 OR experience_years > 80)
            ) THEN
                RAISE EXCEPTION 'Cannot add doctors experience_years constraint: out-of-range values exist';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'doctors_experience_years_check'
                  AND conrelid = 'doctors'::regclass
            ) THEN
                ALTER TABLE doctors ADD CONSTRAINT doctors_experience_years_check
                CHECK (experience_years BETWEEN 0 AND 80);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Refuse rollback because this revision may have repaired pre-existing objects."""
    raise RuntimeError(
        "Schema reconciliation cannot be safely downgraded: it conditionally restores "
        "objects that may have existed before this revision. Apply a forward migration instead."
    )
