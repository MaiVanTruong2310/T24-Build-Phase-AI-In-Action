BEGIN;
-- Align source profile columns with P124-Dev's existing User model.
-- Existing profile data and application roles are retained.
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS date_of_birth date,
    ADD COLUMN IF NOT EXISTS gender varchar(16),
    ADD COLUMN IF NOT EXISTS citizen_id varchar(12),
    ADD COLUMN IF NOT EXISTS health_insurance_code varchar(32),
    ADD COLUMN IF NOT EXISTS password_hash varchar(512),
    ADD COLUMN IF NOT EXISTS status varchar(32) DEFAULT 'pending_verification',
    ADD COLUMN IF NOT EXISTS verified_at timestamptz,
    ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();

ALTER TABLE public.users
    ALTER COLUMN full_name TYPE varchar(200),
    ALTER COLUMN email TYPE varchar(320),
    ALTER COLUMN phone TYPE varchar(32),
    ALTER COLUMN role TYPE varchar(32);

CREATE INDEX IF NOT EXISTS ix_users_citizen_id ON public.users (citizen_id);
CREATE INDEX IF NOT EXISTS ix_users_health_insurance_code ON public.users (health_insurance_code);
NOTIFY pgrst, 'reload schema';

-- Supabase Auth owns credentials; public.users retains application profile IDs.
ALTER TABLE public.users
    ALTER COLUMN phone DROP NOT NULL,
    ALTER COLUMN full_name DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS auth_user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_auth_user_id ON public.users(auth_user_id);
ALTER TABLE public.users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE public.users ADD CONSTRAINT users_role_check
    CHECK (role IN ('PATIENT', 'RECEPTIONIST', 'DOCTOR', 'ADMIN', 'patient', 'staff'));
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.users FROM anon, authenticated;
NOTIFY pgrst, 'reload schema';

COMMIT;
