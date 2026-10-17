-- Additive migration: existing patient IDs and booking records remain intact.
CREATE TABLE public.patient_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_user_id uuid NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE RESTRICT,
  linked_user_id uuid UNIQUE REFERENCES public.users(id) ON DELETE RESTRICT,
  full_name varchar(120), date_of_birth date, gender varchar(24),
  contact_phone varchar(20), citizen_id varchar(12), health_insurance_code varchar(32),
  address varchar(500), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.patient_relationships (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
  patient_profile_id uuid NOT NULL REFERENCES public.patient_profiles(id) ON DELETE RESTRICT,
  relationship varchar(24) NOT NULL CHECK (relationship IN ('self','parent','child','spouse','sibling','grandparent','other')),
  status varchar(16) NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  can_book boolean NOT NULL DEFAULT true,
  can_view_medical boolean NOT NULL DEFAULT false,
  consent_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_patient_relationship UNIQUE (user_id, patient_profile_id)
);
CREATE INDEX ix_patient_relationships_user_id ON public.patient_relationships(user_id);
CREATE INDEX ix_patient_relationships_patient_profile_id ON public.patient_relationships(patient_profile_id);
ALTER TABLE public.patient_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.patient_relationships ENABLE ROW LEVEL SECURITY;
-- All access goes through the authenticated backend, never anonymous PostgREST.
REVOKE ALL ON public.patient_profiles, public.patient_relationships FROM anon, authenticated;
GRANT ALL ON public.patient_profiles, public.patient_relationships TO service_role;

INSERT INTO public.patient_profiles(patient_user_id,linked_user_id,full_name,date_of_birth,gender,contact_phone,citizen_id,health_insurance_code,address)
SELECT id, CASE WHEN status NOT IN ('guest','dependent') THEN id END, left(full_name,120), date_of_birth, gender,
       CASE WHEN length(phone)<=20 THEN phone END, citizen_id, health_insurance_code, left(patient_details->>'address',500)
FROM public.users WHERE role='patient';
INSERT INTO public.patient_relationships(user_id,patient_profile_id,relationship,can_view_medical)
SELECT linked_user_id,id,'self',true FROM public.patient_profiles WHERE linked_user_id IS NOT NULL;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['bookings','booking_holds','consultation_requests','package_requests','coordination_cases'] LOOP
    EXECUTE format('ALTER TABLE public.%I ADD COLUMN patient_profile_id uuid REFERENCES public.patient_profiles(id) ON DELETE RESTRICT',t);
    EXECUTE format('ALTER TABLE public.%I ADD COLUMN requested_by_user_id uuid REFERENCES public.users(id) ON DELETE RESTRICT',t);
    EXECUTE format('CREATE INDEX %I ON public.%I(requested_by_user_id)', 'ix_'||t||'_requested_by_user_id',t);
    EXECUTE format('CREATE INDEX %I ON public.%I(patient_profile_id)', 'ix_'||t||'_patient_profile_id',t);
  END LOOP;
END $$;
UPDATE public.bookings b SET patient_profile_id=p.id,requested_by_user_id=p.linked_user_id FROM public.patient_profiles p WHERE p.patient_user_id=b.user_id;
UPDATE public.booking_holds b SET patient_profile_id=p.id,requested_by_user_id=p.linked_user_id FROM public.patient_profiles p WHERE p.patient_user_id=b.user_id;
UPDATE public.consultation_requests b SET patient_profile_id=p.id,requested_by_user_id=p.linked_user_id FROM public.patient_profiles p WHERE p.patient_user_id=b.patient_id;
UPDATE public.package_requests b SET patient_profile_id=p.id,requested_by_user_id=p.linked_user_id FROM public.patient_profiles p WHERE p.patient_user_id=b.patient_id;
UPDATE public.coordination_cases b SET patient_profile_id=p.id,requested_by_user_id=p.linked_user_id FROM public.patient_profiles p WHERE p.patient_user_id=b.patient_id;
ALTER TABLE public.chat_conversations ADD COLUMN patient_profile_id uuid REFERENCES public.patient_profiles(id) ON DELETE RESTRICT;
CREATE INDEX ix_chat_conversations_patient_profile_id ON public.chat_conversations(patient_profile_id);
UPDATE public.chat_conversations c SET patient_profile_id=p.id FROM public.patient_profiles p WHERE p.linked_user_id=c.user_id;
