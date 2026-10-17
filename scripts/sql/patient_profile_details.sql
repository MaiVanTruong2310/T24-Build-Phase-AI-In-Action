-- Apply to the AUTH_DATABASE_URL database before deploying the model change.
BEGIN;
SET LOCAL lock_timeout = '5s';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS patient_details jsonb;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.users FROM anon, authenticated;
NOTIFY pgrst, 'reload schema';
COMMIT;
