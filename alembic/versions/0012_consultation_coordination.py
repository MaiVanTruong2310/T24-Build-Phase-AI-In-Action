"""Recurring shifts, dated five-slot sessions and HITL consultation requests."""

from alembic import op

revision = "0012_consultation_coordination"
down_revision = "0011_booking_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE weekly_shifts (
          id uuid PRIMARY KEY, doctor_id uuid NOT NULL REFERENCES doctors(id) ON DELETE RESTRICT,
          facility_id uuid NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,
          weekday integer NOT NULL CHECK (weekday BETWEEN 0 AND 6),
          period varchar(12) NOT NULL CHECK (period IN ('morning','afternoon')),
          start_time time NOT NULL, slot_minutes integer NOT NULL CHECK (slot_minutes BETWEEN 5 AND 240),
          slot_count integer NOT NULL CHECK (slot_count BETWEEN 1 AND 20),
          effective_from date NOT NULL, effective_until date, active boolean NOT NULL DEFAULT true,
          CONSTRAINT uq_weekly_shift_doctor_day_period UNIQUE (doctor_id, weekday, period)
        )
    """)
    op.execute("CREATE INDEX ix_weekly_shifts_doctor_id ON weekly_shifts(doctor_id)")
    op.execute("""
        CREATE TABLE consultation_sessions (
          id uuid PRIMARY KEY, weekly_shift_id uuid NOT NULL REFERENCES weekly_shifts(id) ON DELETE RESTRICT,
          doctor_id uuid NOT NULL REFERENCES doctors(id) ON DELETE RESTRICT,
          facility_id uuid NOT NULL REFERENCES facilities(id) ON DELETE RESTRICT,
          session_date date NOT NULL,
          period varchar(12) NOT NULL CHECK (period IN ('morning','afternoon')),
          status varchar(16) NOT NULL DEFAULT 'open', created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT uq_consultation_session_doctor_date_period UNIQUE (doctor_id, session_date, period)
        )
    """)
    op.execute("CREATE INDEX ix_consultation_sessions_doctor_id ON consultation_sessions(doctor_id)")
    op.execute("CREATE INDEX ix_consultation_sessions_session_date ON consultation_sessions(session_date)")
    op.execute("""
        CREATE TABLE consultation_slots (
          id uuid PRIMARY KEY,
          session_id uuid NOT NULL REFERENCES consultation_sessions(id) ON DELETE RESTRICT,
          schedule_id uuid NOT NULL REFERENCES doctor_schedules(id) ON DELETE RESTRICT,
          ordinal integer NOT NULL,
          CONSTRAINT uq_consultation_slot_ordinal UNIQUE (session_id, ordinal),
          CONSTRAINT uq_consultation_slot_schedule UNIQUE (schedule_id)
        )
    """)
    op.execute("CREATE INDEX ix_consultation_slots_session_id ON consultation_slots(session_id)")
    op.execute("""
        CREATE TABLE consultation_requests (
          id uuid PRIMARY KEY, patient_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
          session_id uuid NOT NULL REFERENCES consultation_sessions(id) ON DELETE RESTRICT,
          service_id uuid NOT NULL REFERENCES services(id) ON DELETE RESTRICT,
          specialty_id uuid NOT NULL REFERENCES specialties(id) ON DELETE RESTRICT,
          encounter_type varchar(20) NOT NULL DEFAULT 'in_person',
          reason text NOT NULL, patient_note text, status varchar(16) NOT NULL DEFAULT 'pending',
          assigned_slot_id uuid REFERENCES consultation_slots(id) ON DELETE RESTRICT,
          booking_id uuid UNIQUE REFERENCES bookings(id) ON DELETE RESTRICT,
          staff_note text, reviewed_by uuid REFERENCES users(id) ON DELETE SET NULL,
          reviewed_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_consultation_requests_session_status ON consultation_requests(session_id,status)")
    op.execute("CREATE INDEX ix_consultation_requests_patient_created ON consultation_requests(patient_id,created_at)")
    op.execute("CREATE UNIQUE INDEX uq_consultation_requests_active_patient_session ON consultation_requests(patient_id,session_id) WHERE status IN ('pending','confirmed')")
    op.execute("CREATE UNIQUE INDEX uq_consultation_requests_confirmed_slot ON consultation_requests(assigned_slot_id) WHERE status = 'confirmed'")
    op.execute("""
        CREATE TABLE consultation_request_events (
          id uuid PRIMARY KEY,
          request_id uuid NOT NULL REFERENCES consultation_requests(id) ON DELETE RESTRICT,
          actor_id uuid REFERENCES users(id) ON DELETE SET NULL,
          action varchar(32) NOT NULL, note text,
          created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_consultation_request_events_request_id ON consultation_request_events(request_id)")
    for table in ("weekly_shifts", "consultation_sessions", "consultation_slots", "consultation_requests", "consultation_request_events"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM anon, authenticated")


def downgrade() -> None:
    for table in ("consultation_request_events", "consultation_requests", "consultation_slots", "consultation_sessions", "weekly_shifts"):
        op.execute(f"DROP TABLE {table}")
