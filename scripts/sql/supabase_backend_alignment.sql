-- Align the legacy crawled Supabase schema with P-124 without discarding source data.

-- Run this one-off bootstrap against the intended Supabase DATABASE_URL, not the old EC2 database.

-- Empty legacy bookings are required. A transaction protects against partial application.

BEGIN;

SET LOCAL lock_timeout = '10s';

SET LOCAL statement_timeout = '60s';

SET LOCAL search_path = public, extensions;

SELECT pg_advisory_xact_lock(hashtext('p124_supabase_backend_alignment_v1'));

LOCK TABLE public.bookings, public.doctor_schedules IN ACCESS EXCLUSIVE MODE;

DO $$ BEGIN IF EXISTS (SELECT 1 FROM public.bookings) AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='bookings' AND column_name='user_id') THEN RAISE EXCEPTION 'Legacy bookings must be mapped before this migration'; END IF; END $$;

CREATE SCHEMA IF NOT EXISTS backend_migration_backup;

CREATE SCHEMA IF NOT EXISTS source_archive;

REVOKE ALL ON SCHEMA backend_migration_backup, source_archive FROM PUBLIC, anon, authenticated;

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE IF NOT EXISTS backend_migration_backup."doctors_20261002" AS TABLE public."doctors";

CREATE TABLE IF NOT EXISTS backend_migration_backup."facilities_20261002" AS TABLE public."facilities";

CREATE TABLE IF NOT EXISTS backend_migration_backup."services_20261002" AS TABLE public."services";

CREATE TABLE IF NOT EXISTS backend_migration_backup."specialties_20261002" AS TABLE public."specialties";

CREATE TABLE IF NOT EXISTS backend_migration_backup."users_20261002" AS TABLE public."users";

CREATE TABLE IF NOT EXISTS backend_migration_backup."doctor_facilities_20261002" AS TABLE public."doctor_facilities";

CREATE TABLE IF NOT EXISTS backend_migration_backup."doctor_schedules_20261002" AS TABLE public."doctor_schedules";

CREATE TABLE IF NOT EXISTS backend_migration_backup."doctor_services_20261002" AS TABLE public."doctor_services";

CREATE TABLE IF NOT EXISTS backend_migration_backup."doctor_specialties_20261002" AS TABLE public."doctor_specialties";

CREATE TABLE IF NOT EXISTS backend_migration_backup."otp_challenges_20261002" AS TABLE public."otp_challenges";

CREATE TABLE IF NOT EXISTS backend_migration_backup."refresh_sessions_20261002" AS TABLE public."refresh_sessions";

CREATE TABLE IF NOT EXISTS backend_migration_backup."bookings_20261002" AS TABLE public."bookings";

REVOKE ALL ON ALL TABLES IN SCHEMA backend_migration_backup FROM PUBLIC, anon, authenticated;

-- Preserve unverified crawl schedules, including their original IDs and status, outside the booking catalog.

CREATE TABLE IF NOT EXISTS source_archive.doctor_schedules AS SELECT * FROM public.doctor_schedules WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS source_archive_schedule_id ON source_archive.doctor_schedules (id);

INSERT INTO source_archive.doctor_schedules ("id", "doctor_id", "facility_id", "service_id", "starts_at", "ends_at", "capacity", "status", "source_system", "external_schedule_id", "version", "updated_at") SELECT s."id", s."doctor_id", s."facility_id", s."service_id", s."starts_at", s."ends_at", s."capacity", s."status", s."source_system", s."external_schedule_id", s."version", s."updated_at" FROM public.doctor_schedules s WHERE (s.facility_id IS NULL OR s.doctor_id IS NULL OR s.ends_at <= s.starts_at OR s.capacity IS NULL OR s.capacity < 0) ON CONFLICT (id) DO NOTHING;

DO $$ BEGIN IF EXISTS (SELECT 1 FROM public.bookings b JOIN public.doctor_schedules s ON s.id=b.schedule_id WHERE (s.facility_id IS NULL OR s.doctor_id IS NULL OR s.ends_at <= s.starts_at OR s.capacity IS NULL OR s.capacity < 0)) THEN RAISE EXCEPTION 'A booking refers to an invalid source schedule'; END IF; END $$;

DELETE FROM public.doctor_schedules s WHERE (s.facility_id IS NULL OR s.doctor_id IS NULL OR s.ends_at <= s.starts_at OR s.capacity IS NULL OR s.capacity < 0) AND EXISTS (SELECT 1 FROM source_archive.doctor_schedules a WHERE a.id=s.id);

REVOKE ALL ON ALL TABLES IN SCHEMA source_archive FROM PUBLIC, anon, authenticated;

COMMENT ON TABLE source_archive.doctor_schedules IS 'Original crawl schedules missing verified facility or valid slot data; not bookable. Restore only after source verification.';

ALTER TABLE public."facilities" ALTER COLUMN "code" TYPE VARCHAR(64);

ALTER TABLE public."facilities" ALTER COLUMN "name" TYPE VARCHAR(200);

ALTER TABLE public."facilities" ADD COLUMN IF NOT EXISTS "description" TEXT;

ALTER TABLE public."facilities" ALTER COLUMN "phone" TYPE VARCHAR(32);

ALTER TABLE public."facilities" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITH TIME ZONE;

ALTER TABLE public."facilities" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMP WITH TIME ZONE;

ALTER TABLE public."services" ALTER COLUMN "code" TYPE VARCHAR(64);

ALTER TABLE public."services" ALTER COLUMN "name" TYPE VARCHAR(200);

ALTER TABLE public."services" ADD COLUMN IF NOT EXISTS "description" TEXT;

ALTER TABLE public."services" ADD COLUMN IF NOT EXISTS "duration_minutes" INTEGER;

ALTER TABLE public."services" ADD COLUMN IF NOT EXISTS "original_price" NUMERIC(12, 2);

ALTER TABLE public."services" ADD COLUMN IF NOT EXISTS "category" VARCHAR(100);

ALTER TABLE public."services" ADD COLUMN IF NOT EXISTS "booking_mode" VARCHAR(20);

ALTER TABLE public."services" ADD COLUMN IF NOT EXISTS "features" JSON;

ALTER TABLE public."services" ADD COLUMN IF NOT EXISTS "patient_count" INTEGER;

ALTER TABLE public."services" ADD COLUMN IF NOT EXISTS "satisfaction_rate" FLOAT;

ALTER TABLE public."services" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITH TIME ZONE;

ALTER TABLE public."services" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMP WITH TIME ZONE;

CREATE TABLE IF NOT EXISTS catalog_audit_events (
	id UUID NOT NULL, 
	actor_id UUID, 
	entity_type VARCHAR(64) NOT NULL, 
	entity_id UUID NOT NULL, 
	action VARCHAR(64) NOT NULL, 
	payload JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
);

ALTER TABLE public."doctor_schedules" ALTER COLUMN "source_system" TYPE VARCHAR(64);

ALTER TABLE public."doctor_schedules" ALTER COLUMN "external_schedule_id" TYPE VARCHAR(128);

ALTER TABLE public."doctor_schedules" ADD COLUMN IF NOT EXISTS "created_by" UUID;

ALTER TABLE public."doctor_schedules" ADD COLUMN IF NOT EXISTS "updated_by" UUID;

ALTER TABLE public."doctor_schedules" ADD COLUMN IF NOT EXISTS "cancellation_reason" TEXT;

ALTER TABLE public."doctor_schedules" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITH TIME ZONE;

CREATE TABLE IF NOT EXISTS booking_holds (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	schedule_id UUID NOT NULL, 
	service_id UUID NOT NULL, 
	specialty_id UUID NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	released_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(schedule_id) REFERENCES doctor_schedules (id) ON DELETE RESTRICT, 
	FOREIGN KEY(service_id) REFERENCES services (id) ON DELETE RESTRICT, 
	FOREIGN KEY(specialty_id) REFERENCES specialties (id) ON DELETE RESTRICT
);

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "user_id" UUID;

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "hold_id" UUID;

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "facility_id" UUID;

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "starts_at" TIMESTAMP WITH TIME ZONE;

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "ends_at" TIMESTAMP WITH TIME ZONE;

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "service_id" UUID;

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "encounter_type" VARCHAR(20);

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "reason" TEXT;

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "patient_note" TEXT;

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "cancellation_reason" TEXT;

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "staff_note" TEXT;

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "idempotency_key" VARCHAR(128);

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "idempotency_hash" VARCHAR(64);

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "reviewed_by" UUID;

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "reviewed_at" TIMESTAMP WITH TIME ZONE;

ALTER TABLE public."bookings" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMP WITH TIME ZONE;

CREATE TABLE IF NOT EXISTS notifications (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	booking_id UUID, 
	kind VARCHAR(32) NOT NULL, 
	status VARCHAR(16) DEFAULT 'pending' NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	message TEXT NOT NULL, 
	dedupe_key VARCHAR(160) NOT NULL, 
	available_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	delivered_at TIMESTAMP WITH TIME ZONE, 
	read_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(booking_id) REFERENCES bookings (id) ON DELETE SET NULL
);

ALTER TABLE public."doctor_schedules" DROP CONSTRAINT IF EXISTS "doctor_schedules_status_check";

ALTER TABLE public."bookings" DROP CONSTRAINT IF EXISTS "bookings_status_check";

ALTER TABLE public."users" DROP CONSTRAINT IF EXISTS "users_role_check";

ALTER TABLE public."doctors" DROP CONSTRAINT IF EXISTS "doctors_review_status_check";

UPDATE public.doctors SET review_status='needs_review' WHERE review_status='pending';

UPDATE public.users SET role=CASE role WHEN 'PATIENT' THEN 'patient' WHEN 'ADMIN' THEN 'staff' WHEN 'DOCTOR' THEN 'staff' WHEN 'RECEPTIONIST' THEN 'staff' ELSE role END;

UPDATE public.bookings SET status=CASE status WHEN 'PENDING_APPROVAL' THEN 'pending_approval' WHEN 'APPROVED' THEN 'confirmed' WHEN 'REJECTED' THEN 'rejected' WHEN 'CANCELLED' THEN 'cancelled' ELSE status END;

ALTER TABLE public.bookings ALTER COLUMN booking_code SET DEFAULT ('BK-' || replace(gen_random_uuid()::text, '-', '')::varchar(27));

-- No inferred service assignment, appointment duration or availability is added.

ALTER TABLE public."doctors" ALTER COLUMN "id" SET NOT NULL;

UPDATE public."doctors" SET "code"='DOC-' || id::text WHERE "code" IS NULL;

ALTER TABLE public."doctors" ALTER COLUMN "code" SET NOT NULL;

ALTER TABLE public."doctors" ALTER COLUMN "full_name" SET NOT NULL;

UPDATE public."doctors" SET "status"='inactive' WHERE "status" IS NULL;

ALTER TABLE public."doctors" ALTER COLUMN "status" SET DEFAULT 'inactive';

ALTER TABLE public."doctors" ALTER COLUMN "status" SET NOT NULL;

UPDATE public."doctors" SET "review_status"='needs_review' WHERE "review_status" IS NULL;

ALTER TABLE public."doctors" ALTER COLUMN "review_status" SET DEFAULT 'needs_review';

ALTER TABLE public."doctors" ALTER COLUMN "review_status" SET NOT NULL;

UPDATE public."doctors" SET "booking_enabled"=false WHERE "booking_enabled" IS NULL;

ALTER TABLE public."doctors" ALTER COLUMN "booking_enabled" SET DEFAULT false;

ALTER TABLE public."doctors" ALTER COLUMN "booking_enabled" SET NOT NULL;

UPDATE public."doctors" SET "created_at"=now() WHERE "created_at" IS NULL;

ALTER TABLE public."doctors" ALTER COLUMN "created_at" SET DEFAULT now();

ALTER TABLE public."doctors" ALTER COLUMN "created_at" SET NOT NULL;

UPDATE public."doctors" SET "updated_at"=now() WHERE "updated_at" IS NULL;

ALTER TABLE public."doctors" ALTER COLUMN "updated_at" SET DEFAULT now();

ALTER TABLE public."doctors" ALTER COLUMN "updated_at" SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ix_doctors_code ON doctors (code);

ALTER TABLE public."facilities" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."facilities" ALTER COLUMN "code" SET NOT NULL;

ALTER TABLE public."facilities" ALTER COLUMN "name" SET NOT NULL;

UPDATE public."facilities" SET "status"='inactive' WHERE "status" IS NULL;

ALTER TABLE public."facilities" ALTER COLUMN "status" SET DEFAULT 'inactive';

ALTER TABLE public."facilities" ALTER COLUMN "status" SET NOT NULL;

UPDATE public."facilities" SET "created_at"=now() WHERE "created_at" IS NULL;

ALTER TABLE public."facilities" ALTER COLUMN "created_at" SET DEFAULT now();

ALTER TABLE public."facilities" ALTER COLUMN "created_at" SET NOT NULL;

UPDATE public."facilities" SET "updated_at"=now() WHERE "updated_at" IS NULL;

ALTER TABLE public."facilities" ALTER COLUMN "updated_at" SET DEFAULT now();

ALTER TABLE public."facilities" ALTER COLUMN "updated_at" SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ix_facilities_code ON facilities (code);

ALTER TABLE public."services" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."services" ALTER COLUMN "code" SET NOT NULL;

ALTER TABLE public."services" ALTER COLUMN "name" SET NOT NULL;

UPDATE public."services" SET "booking_mode"='group' WHERE "booking_mode" IS NULL;

ALTER TABLE public."services" ALTER COLUMN "booking_mode" SET DEFAULT 'group';

ALTER TABLE public."services" ALTER COLUMN "booking_mode" SET NOT NULL;

UPDATE public."services" SET "status"='inactive' WHERE "status" IS NULL;

ALTER TABLE public."services" ALTER COLUMN "status" SET DEFAULT 'inactive';

ALTER TABLE public."services" ALTER COLUMN "status" SET NOT NULL;

UPDATE public."services" SET "created_at"=now() WHERE "created_at" IS NULL;

ALTER TABLE public."services" ALTER COLUMN "created_at" SET DEFAULT now();

ALTER TABLE public."services" ALTER COLUMN "created_at" SET NOT NULL;

UPDATE public."services" SET "updated_at"=now() WHERE "updated_at" IS NULL;

ALTER TABLE public."services" ALTER COLUMN "updated_at" SET DEFAULT now();

ALTER TABLE public."services" ALTER COLUMN "updated_at" SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ix_services_code ON services (code);

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.services'::regclass AND conname='ck_services_booking_mode') THEN ALTER TABLE services ADD CONSTRAINT ck_services_booking_mode CHECK (booking_mode IN ('group', 'doctor_visit')); END IF; END $$;

ALTER TABLE public."specialties" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."specialties" ALTER COLUMN "code" SET NOT NULL;

ALTER TABLE public."specialties" ALTER COLUMN "name" SET NOT NULL;

UPDATE public."specialties" SET "status"='inactive' WHERE "status" IS NULL;

ALTER TABLE public."specialties" ALTER COLUMN "status" SET DEFAULT 'inactive';

ALTER TABLE public."specialties" ALTER COLUMN "status" SET NOT NULL;

UPDATE public."specialties" SET "created_at"=now() WHERE "created_at" IS NULL;

ALTER TABLE public."specialties" ALTER COLUMN "created_at" SET DEFAULT now();

ALTER TABLE public."specialties" ALTER COLUMN "created_at" SET NOT NULL;

UPDATE public."specialties" SET "updated_at"=now() WHERE "updated_at" IS NULL;

ALTER TABLE public."specialties" ALTER COLUMN "updated_at" SET DEFAULT now();

ALTER TABLE public."specialties" ALTER COLUMN "updated_at" SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ix_specialties_code ON specialties (code);

ALTER TABLE public."users" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."users" ALTER COLUMN "role" SET NOT NULL;

UPDATE public."users" SET "status"='pending_verification' WHERE "status" IS NULL;

ALTER TABLE public."users" ALTER COLUMN "status" SET DEFAULT 'pending_verification';

ALTER TABLE public."users" ALTER COLUMN "status" SET NOT NULL;

UPDATE public."users" SET "created_at"=now() WHERE "created_at" IS NULL;

ALTER TABLE public."users" ALTER COLUMN "created_at" SET DEFAULT now();

ALTER TABLE public."users" ALTER COLUMN "created_at" SET NOT NULL;

UPDATE public."users" SET "updated_at"=now() WHERE "updated_at" IS NULL;

ALTER TABLE public."users" ALTER COLUMN "updated_at" SET DEFAULT now();

ALTER TABLE public."users" ALTER COLUMN "updated_at" SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_auth_user_id ON users (auth_user_id);

CREATE INDEX IF NOT EXISTS ix_users_citizen_id ON users (citizen_id);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE INDEX IF NOT EXISTS ix_users_health_insurance_code ON users (health_insurance_code);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone ON users (phone);

ALTER TABLE public."catalog_audit_events" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."catalog_audit_events" ALTER COLUMN "entity_type" SET NOT NULL;

ALTER TABLE public."catalog_audit_events" ALTER COLUMN "entity_id" SET NOT NULL;

ALTER TABLE public."catalog_audit_events" ALTER COLUMN "action" SET NOT NULL;

ALTER TABLE public."catalog_audit_events" ALTER COLUMN "payload" SET NOT NULL;

UPDATE public."catalog_audit_events" SET "created_at"=now() WHERE "created_at" IS NULL;

ALTER TABLE public."catalog_audit_events" ALTER COLUMN "created_at" SET DEFAULT now();

ALTER TABLE public."catalog_audit_events" ALTER COLUMN "created_at" SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_catalog_audit_events_actor_id ON catalog_audit_events (actor_id);

CREATE INDEX IF NOT EXISTS ix_catalog_audit_events_entity_id ON catalog_audit_events (entity_id);

CREATE INDEX IF NOT EXISTS ix_catalog_audit_events_entity_type ON catalog_audit_events (entity_type);

ALTER TABLE public."catalog_audit_events" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public."catalog_audit_events" FROM PUBLIC, anon, authenticated;

ALTER TABLE public."doctor_facilities" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."doctor_facilities" ALTER COLUMN "doctor_id" SET NOT NULL;

ALTER TABLE public."doctor_facilities" ALTER COLUMN "facility_id" SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_doctor_facilities_doctor_id ON doctor_facilities (doctor_id);

CREATE INDEX IF NOT EXISTS ix_doctor_facilities_facility_id ON doctor_facilities (facility_id);

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.doctor_facilities'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='doctor_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'doctor_facilities', fk.conname); END LOOP; END $$;

ALTER TABLE public."doctor_facilities" ADD CONSTRAINT "fk_doctor_facilities_doctor_id_doctors" FOREIGN KEY ("doctor_id") REFERENCES public."doctors" ("id") ON DELETE CASCADE;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.doctor_facilities'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='facility_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'doctor_facilities', fk.conname); END LOOP; END $$;

ALTER TABLE public."doctor_facilities" ADD CONSTRAINT "fk_doctor_facilities_facility_id_facilities" FOREIGN KEY ("facility_id") REFERENCES public."facilities" ("id") ON DELETE RESTRICT;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.doctor_facilities'::regclass AND conname='uq_doctor_facility') THEN ALTER TABLE doctor_facilities ADD CONSTRAINT uq_doctor_facility UNIQUE (doctor_id, facility_id); END IF; END $$;

ALTER TABLE public."doctor_schedules" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."doctor_schedules" ALTER COLUMN "doctor_id" SET NOT NULL;

ALTER TABLE public."doctor_schedules" ALTER COLUMN "facility_id" SET NOT NULL;

ALTER TABLE public."doctor_schedules" ALTER COLUMN "starts_at" SET NOT NULL;

ALTER TABLE public."doctor_schedules" ALTER COLUMN "ends_at" SET NOT NULL;

ALTER TABLE public."doctor_schedules" ALTER COLUMN "capacity" SET NOT NULL;

ALTER TABLE public."doctor_schedules" ALTER COLUMN "status" SET NOT NULL;

UPDATE public."doctor_schedules" SET "version"=1 WHERE "version" IS NULL;

ALTER TABLE public."doctor_schedules" ALTER COLUMN "version" SET DEFAULT 1;

ALTER TABLE public."doctor_schedules" ALTER COLUMN "version" SET NOT NULL;

UPDATE public."doctor_schedules" SET "created_at"=now() WHERE "created_at" IS NULL;

ALTER TABLE public."doctor_schedules" ALTER COLUMN "created_at" SET DEFAULT now();

ALTER TABLE public."doctor_schedules" ALTER COLUMN "created_at" SET NOT NULL;

UPDATE public."doctor_schedules" SET "updated_at"=now() WHERE "updated_at" IS NULL;

ALTER TABLE public."doctor_schedules" ALTER COLUMN "updated_at" SET DEFAULT now();

ALTER TABLE public."doctor_schedules" ALTER COLUMN "updated_at" SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_doctor_schedules_created_by ON doctor_schedules (created_by);

CREATE INDEX IF NOT EXISTS ix_doctor_schedules_doctor_id ON doctor_schedules (doctor_id);

CREATE INDEX IF NOT EXISTS ix_doctor_schedules_facility_id ON doctor_schedules (facility_id);

CREATE INDEX IF NOT EXISTS ix_doctor_schedules_starts_at ON doctor_schedules (starts_at);

CREATE INDEX IF NOT EXISTS ix_doctor_schedules_updated_by ON doctor_schedules (updated_by);

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.doctor_schedules'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='created_by' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'doctor_schedules', fk.conname); END LOOP; END $$;

ALTER TABLE public."doctor_schedules" ADD CONSTRAINT "fk_doctor_schedules_created_by_users" FOREIGN KEY ("created_by") REFERENCES public."users" ("id") ON DELETE SET NULL;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.doctor_schedules'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='doctor_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'doctor_schedules', fk.conname); END LOOP; END $$;

ALTER TABLE public."doctor_schedules" ADD CONSTRAINT "fk_doctor_schedules_doctor_id_doctors" FOREIGN KEY ("doctor_id") REFERENCES public."doctors" ("id") ON DELETE RESTRICT;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.doctor_schedules'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='facility_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'doctor_schedules', fk.conname); END LOOP; END $$;

ALTER TABLE public."doctor_schedules" ADD CONSTRAINT "fk_doctor_schedules_facility_id_facilities" FOREIGN KEY ("facility_id") REFERENCES public."facilities" ("id") ON DELETE RESTRICT;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.doctor_schedules'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='updated_by' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'doctor_schedules', fk.conname); END LOOP; END $$;

ALTER TABLE public."doctor_schedules" ADD CONSTRAINT "fk_doctor_schedules_updated_by_users" FOREIGN KEY ("updated_by") REFERENCES public."users" ("id") ON DELETE SET NULL;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.doctor_schedules'::regclass AND conname='ck_schedule_capacity_nonnegative') THEN ALTER TABLE doctor_schedules ADD CONSTRAINT ck_schedule_capacity_nonnegative CHECK (capacity >= 0); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.doctor_schedules'::regclass AND conname='ck_schedule_time_order') THEN ALTER TABLE doctor_schedules ADD CONSTRAINT ck_schedule_time_order CHECK (ends_at > starts_at); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.doctor_schedules'::regclass AND conname='uq_schedule_external_identity') THEN ALTER TABLE doctor_schedules ADD CONSTRAINT uq_schedule_external_identity UNIQUE (source_system, external_schedule_id); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.doctor_schedules'::regclass AND conname='excl_doctor_schedule_time') THEN ALTER TABLE doctor_schedules ADD CONSTRAINT excl_doctor_schedule_time EXCLUDE USING gist (doctor_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&) WHERE (status <> 'cancelled'); END IF; END $$;

ALTER TABLE public."doctor_services" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."doctor_services" ALTER COLUMN "doctor_id" SET NOT NULL;

ALTER TABLE public."doctor_services" ALTER COLUMN "service_id" SET NOT NULL;

UPDATE public."doctor_services" SET "active"=true WHERE "active" IS NULL;

ALTER TABLE public."doctor_services" ALTER COLUMN "active" SET DEFAULT true;

ALTER TABLE public."doctor_services" ALTER COLUMN "active" SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_doctor_services_doctor_id ON doctor_services (doctor_id);

CREATE INDEX IF NOT EXISTS ix_doctor_services_service_id ON doctor_services (service_id);

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.doctor_services'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='doctor_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'doctor_services', fk.conname); END LOOP; END $$;

ALTER TABLE public."doctor_services" ADD CONSTRAINT "fk_doctor_services_doctor_id_doctors" FOREIGN KEY ("doctor_id") REFERENCES public."doctors" ("id") ON DELETE CASCADE;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.doctor_services'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='service_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'doctor_services', fk.conname); END LOOP; END $$;

ALTER TABLE public."doctor_services" ADD CONSTRAINT "fk_doctor_services_service_id_services" FOREIGN KEY ("service_id") REFERENCES public."services" ("id") ON DELETE RESTRICT;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.doctor_services'::regclass AND conname='uq_doctor_service') THEN ALTER TABLE doctor_services ADD CONSTRAINT uq_doctor_service UNIQUE (doctor_id, service_id); END IF; END $$;

ALTER TABLE public."doctor_specialties" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."doctor_specialties" ALTER COLUMN "doctor_id" SET NOT NULL;

ALTER TABLE public."doctor_specialties" ALTER COLUMN "specialty_id" SET NOT NULL;

UPDATE public."doctor_specialties" SET "is_primary"=false WHERE "is_primary" IS NULL;

ALTER TABLE public."doctor_specialties" ALTER COLUMN "is_primary" SET DEFAULT false;

ALTER TABLE public."doctor_specialties" ALTER COLUMN "is_primary" SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_doctor_specialties_doctor_id ON doctor_specialties (doctor_id);

CREATE INDEX IF NOT EXISTS ix_doctor_specialties_specialty_id ON doctor_specialties (specialty_id);

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.doctor_specialties'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='doctor_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'doctor_specialties', fk.conname); END LOOP; END $$;

ALTER TABLE public."doctor_specialties" ADD CONSTRAINT "fk_doctor_specialties_doctor_id_doctors" FOREIGN KEY ("doctor_id") REFERENCES public."doctors" ("id") ON DELETE CASCADE;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.doctor_specialties'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='specialty_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'doctor_specialties', fk.conname); END LOOP; END $$;

ALTER TABLE public."doctor_specialties" ADD CONSTRAINT "fk_doctor_specialties_specialty_id_specialties" FOREIGN KEY ("specialty_id") REFERENCES public."specialties" ("id") ON DELETE RESTRICT;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.doctor_specialties'::regclass AND conname='uq_doctor_specialty') THEN ALTER TABLE doctor_specialties ADD CONSTRAINT uq_doctor_specialty UNIQUE (doctor_id, specialty_id); END IF; END $$;

ALTER TABLE public."otp_challenges" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."otp_challenges" ALTER COLUMN "target" SET NOT NULL;

ALTER TABLE public."otp_challenges" ALTER COLUMN "purpose" SET NOT NULL;

ALTER TABLE public."otp_challenges" ALTER COLUMN "code_hash" SET NOT NULL;

ALTER TABLE public."otp_challenges" ALTER COLUMN "expires_at" SET NOT NULL;

ALTER TABLE public."otp_challenges" ALTER COLUMN "attempts" SET NOT NULL;

UPDATE public."otp_challenges" SET "created_at"=now() WHERE "created_at" IS NULL;

ALTER TABLE public."otp_challenges" ALTER COLUMN "created_at" SET DEFAULT now();

ALTER TABLE public."otp_challenges" ALTER COLUMN "created_at" SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_otp_challenges_target ON otp_challenges (target);

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.otp_challenges'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='user_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'otp_challenges', fk.conname); END LOOP; END $$;

ALTER TABLE public."otp_challenges" ADD CONSTRAINT "fk_otp_challenges_user_id_users" FOREIGN KEY ("user_id") REFERENCES public."users" ("id") ON DELETE CASCADE;

ALTER TABLE public."refresh_sessions" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."refresh_sessions" ALTER COLUMN "user_id" SET NOT NULL;

ALTER TABLE public."refresh_sessions" ALTER COLUMN "token_hash" SET NOT NULL;

ALTER TABLE public."refresh_sessions" ALTER COLUMN "expires_at" SET NOT NULL;

UPDATE public."refresh_sessions" SET "created_at"=now() WHERE "created_at" IS NULL;

ALTER TABLE public."refresh_sessions" ALTER COLUMN "created_at" SET DEFAULT now();

ALTER TABLE public."refresh_sessions" ALTER COLUMN "created_at" SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_sessions_token_hash ON refresh_sessions (token_hash);

CREATE INDEX IF NOT EXISTS ix_refresh_sessions_user_id ON refresh_sessions (user_id);

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.refresh_sessions'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='user_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'refresh_sessions', fk.conname); END LOOP; END $$;

ALTER TABLE public."refresh_sessions" ADD CONSTRAINT "fk_refresh_sessions_user_id_users" FOREIGN KEY ("user_id") REFERENCES public."users" ("id") ON DELETE CASCADE;

ALTER TABLE public."booking_holds" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."booking_holds" ALTER COLUMN "user_id" SET NOT NULL;

ALTER TABLE public."booking_holds" ALTER COLUMN "schedule_id" SET NOT NULL;

ALTER TABLE public."booking_holds" ALTER COLUMN "service_id" SET NOT NULL;

ALTER TABLE public."booking_holds" ALTER COLUMN "specialty_id" SET NOT NULL;

ALTER TABLE public."booking_holds" ALTER COLUMN "status" SET NOT NULL;

ALTER TABLE public."booking_holds" ALTER COLUMN "expires_at" SET NOT NULL;

UPDATE public."booking_holds" SET "created_at"=now() WHERE "created_at" IS NULL;

ALTER TABLE public."booking_holds" ALTER COLUMN "created_at" SET DEFAULT now();

ALTER TABLE public."booking_holds" ALTER COLUMN "created_at" SET NOT NULL;

UPDATE public."booking_holds" SET "updated_at"=now() WHERE "updated_at" IS NULL;

ALTER TABLE public."booking_holds" ALTER COLUMN "updated_at" SET DEFAULT now();

ALTER TABLE public."booking_holds" ALTER COLUMN "updated_at" SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_booking_holds_expires_at ON booking_holds (expires_at);

CREATE INDEX IF NOT EXISTS ix_booking_holds_schedule_id ON booking_holds (schedule_id);

CREATE INDEX IF NOT EXISTS ix_booking_holds_schedule_status ON booking_holds (schedule_id, status);

CREATE INDEX IF NOT EXISTS ix_booking_holds_status ON booking_holds (status);

CREATE INDEX IF NOT EXISTS ix_booking_holds_user_id ON booking_holds (user_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_booking_holds_active_user_schedule ON booking_holds (user_id, schedule_id) WHERE status = 'active';

ALTER TABLE public."booking_holds" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public."booking_holds" FROM PUBLIC, anon, authenticated;

ALTER TABLE public."bookings" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."bookings" ALTER COLUMN "user_id" SET NOT NULL;

ALTER TABLE public."bookings" ALTER COLUMN "doctor_id" SET NOT NULL;

ALTER TABLE public."bookings" ALTER COLUMN "facility_id" SET NOT NULL;

ALTER TABLE public."bookings" ALTER COLUMN "starts_at" SET NOT NULL;

ALTER TABLE public."bookings" ALTER COLUMN "ends_at" SET NOT NULL;

ALTER TABLE public."bookings" ALTER COLUMN "service_id" SET NOT NULL;

ALTER TABLE public."bookings" ALTER COLUMN "specialty_id" SET NOT NULL;

ALTER TABLE public."bookings" ALTER COLUMN "encounter_type" SET NOT NULL;

ALTER TABLE public."bookings" ALTER COLUMN "reason" SET NOT NULL;

UPDATE public."bookings" SET "status"='pending_approval' WHERE "status" IS NULL;

ALTER TABLE public."bookings" ALTER COLUMN "status" SET DEFAULT 'pending_approval';

ALTER TABLE public."bookings" ALTER COLUMN "status" SET NOT NULL;

UPDATE public."bookings" SET "created_at"=now() WHERE "created_at" IS NULL;

ALTER TABLE public."bookings" ALTER COLUMN "created_at" SET DEFAULT now();

ALTER TABLE public."bookings" ALTER COLUMN "created_at" SET NOT NULL;

UPDATE public."bookings" SET "updated_at"=now() WHERE "updated_at" IS NULL;

ALTER TABLE public."bookings" ALTER COLUMN "updated_at" SET DEFAULT now();

ALTER TABLE public."bookings" ALTER COLUMN "updated_at" SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_bookings_doctor_id ON bookings (doctor_id);

CREATE INDEX IF NOT EXISTS ix_bookings_facility_id ON bookings (facility_id);

CREATE UNIQUE INDEX IF NOT EXISTS ix_bookings_hold_id ON bookings (hold_id);

CREATE INDEX IF NOT EXISTS ix_bookings_reviewed_by ON bookings (reviewed_by);

CREATE INDEX IF NOT EXISTS ix_bookings_schedule_id ON bookings (schedule_id);

CREATE INDEX IF NOT EXISTS ix_bookings_schedule_status ON bookings (schedule_id, status);

CREATE INDEX IF NOT EXISTS ix_bookings_service_id ON bookings (service_id);

CREATE INDEX IF NOT EXISTS ix_bookings_specialty_id ON bookings (specialty_id);

CREATE INDEX IF NOT EXISTS ix_bookings_starts_at ON bookings (starts_at);

CREATE INDEX IF NOT EXISTS ix_bookings_status ON bookings (status);

CREATE INDEX IF NOT EXISTS ix_bookings_user_created_at ON bookings (user_id, created_at);

CREATE INDEX IF NOT EXISTS ix_bookings_user_id ON bookings (user_id);

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.bookings'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='doctor_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'bookings', fk.conname); END LOOP; END $$;

ALTER TABLE public."bookings" ADD CONSTRAINT "fk_bookings_doctor_id_doctors" FOREIGN KEY ("doctor_id") REFERENCES public."doctors" ("id") ON DELETE RESTRICT;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.bookings'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='facility_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'bookings', fk.conname); END LOOP; END $$;

ALTER TABLE public."bookings" ADD CONSTRAINT "fk_bookings_facility_id_facilities" FOREIGN KEY ("facility_id") REFERENCES public."facilities" ("id") ON DELETE RESTRICT;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.bookings'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='hold_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'bookings', fk.conname); END LOOP; END $$;

ALTER TABLE public."bookings" ADD CONSTRAINT "fk_bookings_hold_id_booking_holds" FOREIGN KEY ("hold_id") REFERENCES public."booking_holds" ("id") ON DELETE SET NULL;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.bookings'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='reviewed_by' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'bookings', fk.conname); END LOOP; END $$;

ALTER TABLE public."bookings" ADD CONSTRAINT "fk_bookings_reviewed_by_users" FOREIGN KEY ("reviewed_by") REFERENCES public."users" ("id") ON DELETE SET NULL;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.bookings'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='schedule_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'bookings', fk.conname); END LOOP; END $$;

ALTER TABLE public."bookings" ADD CONSTRAINT "fk_bookings_schedule_id_doctor_schedules" FOREIGN KEY ("schedule_id") REFERENCES public."doctor_schedules" ("id") ON DELETE RESTRICT;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.bookings'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='service_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'bookings', fk.conname); END LOOP; END $$;

ALTER TABLE public."bookings" ADD CONSTRAINT "fk_bookings_service_id_services" FOREIGN KEY ("service_id") REFERENCES public."services" ("id") ON DELETE RESTRICT;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.bookings'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='specialty_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'bookings', fk.conname); END LOOP; END $$;

ALTER TABLE public."bookings" ADD CONSTRAINT "fk_bookings_specialty_id_specialties" FOREIGN KEY ("specialty_id") REFERENCES public."specialties" ("id") ON DELETE RESTRICT;

DO $$ DECLARE fk record; BEGIN FOR fk IN SELECT k.conname FROM pg_constraint k JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=k.conkey[1] WHERE k.conrelid='public.bookings'::regclass AND k.contype='f' AND cardinality(k.conkey)=1 AND a.attname='user_id' LOOP EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', 'bookings', fk.conname); END LOOP; END $$;

ALTER TABLE public."bookings" ADD CONSTRAINT "fk_bookings_user_id_users" FOREIGN KEY ("user_id") REFERENCES public."users" ("id") ON DELETE RESTRICT;

ALTER TABLE public."notifications" ALTER COLUMN "id" SET NOT NULL;

ALTER TABLE public."notifications" ALTER COLUMN "user_id" SET NOT NULL;

ALTER TABLE public."notifications" ALTER COLUMN "kind" SET NOT NULL;

ALTER TABLE public."notifications" ALTER COLUMN "status" SET NOT NULL;

ALTER TABLE public."notifications" ALTER COLUMN "title" SET NOT NULL;

ALTER TABLE public."notifications" ALTER COLUMN "message" SET NOT NULL;

ALTER TABLE public."notifications" ALTER COLUMN "dedupe_key" SET NOT NULL;

ALTER TABLE public."notifications" ALTER COLUMN "available_at" SET NOT NULL;

UPDATE public."notifications" SET "created_at"=now() WHERE "created_at" IS NULL;

ALTER TABLE public."notifications" ALTER COLUMN "created_at" SET DEFAULT now();

ALTER TABLE public."notifications" ALTER COLUMN "created_at" SET NOT NULL;

UPDATE public."notifications" SET "updated_at"=now() WHERE "updated_at" IS NULL;

ALTER TABLE public."notifications" ALTER COLUMN "updated_at" SET DEFAULT now();

ALTER TABLE public."notifications" ALTER COLUMN "updated_at" SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_notifications_available_at ON notifications (available_at);

CREATE INDEX IF NOT EXISTS ix_notifications_booking_id ON notifications (booking_id);

CREATE INDEX IF NOT EXISTS ix_notifications_status ON notifications (status);

CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id);

CREATE INDEX IF NOT EXISTS ix_notifications_user_status_available ON notifications (user_id, status, available_at);

CREATE UNIQUE INDEX IF NOT EXISTS uq_notifications_user_dedupe_key ON notifications (user_id, dedupe_key);

ALTER TABLE public."notifications" ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public."notifications" FROM PUBLIC, anon, authenticated;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.doctors'::regclass AND conname='ck_doctors_review_status') THEN ALTER TABLE public.doctors ADD CONSTRAINT ck_doctors_review_status CHECK (review_status IN ('needs_review','approved','rejected')); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.doctor_schedules'::regclass AND conname='ck_schedule_status') THEN ALTER TABLE public.doctor_schedules ADD CONSTRAINT ck_schedule_status CHECK (status IN ('available','inactive','blocked','cancelled')); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.bookings'::regclass AND conname='ck_bookings_status') THEN ALTER TABLE public.bookings ADD CONSTRAINT ck_bookings_status CHECK (status IN ('pending_approval','confirmed','rejected','cancelled')); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.booking_holds'::regclass AND conname='ck_booking_holds_status') THEN ALTER TABLE public.booking_holds ADD CONSTRAINT ck_booking_holds_status CHECK (status IN ('active','released','expired','consumed')); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.notifications'::regclass AND conname='ck_notifications_status') THEN ALTER TABLE public.notifications ADD CONSTRAINT ck_notifications_status CHECK (status IN ('pending','delivered','discarded')); END IF; END $$;

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.users'::regclass AND conname='ck_users_role') THEN ALTER TABLE public.users ADD CONSTRAINT ck_users_role CHECK (role IN ('patient','staff')); END IF; END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_bookings_user_id_idempotency_key ON public.bookings (user_id,idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS backend_migration_backup.applied_migrations (name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());

INSERT INTO backend_migration_backup.applied_migrations(name) VALUES ('supabase_backend_alignment_v1') ON CONFLICT (name) DO NOTHING;

REVOKE ALL ON ALL TABLES IN SCHEMA backend_migration_backup FROM PUBLIC, anon, authenticated;

NOTIFY pgrst, 'reload schema';

COMMIT;
