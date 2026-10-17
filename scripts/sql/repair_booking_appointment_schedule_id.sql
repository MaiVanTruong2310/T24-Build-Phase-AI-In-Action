-- Run against the same PostgreSQL database used by the backend.
BEGIN;

ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS appointment_schedule_id UUID;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_bookings_appointment_schedule_id'
          AND conrelid = 'bookings'::regclass
    ) THEN
        ALTER TABLE bookings
            ADD CONSTRAINT fk_bookings_appointment_schedule_id
            FOREIGN KEY (appointment_schedule_id)
            REFERENCES doctor_schedules(id)
            ON DELETE RESTRICT;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS ix_bookings_appointment_schedule_id
    ON bookings (appointment_schedule_id);

COMMIT;
