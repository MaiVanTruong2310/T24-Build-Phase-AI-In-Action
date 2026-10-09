-- Unify application identity on Supabase Auth.
--
-- BEFORE
--   public.users duplicated the auth identity (`email`, `password_hash`,
--   `verified_at`) next to auth.users, and nothing enforced the link between
--   the two tables: `auth_user_id` had no foreign key, so profiles could be
--   created, orphaned or diverged from the real identity silently.
--
-- AFTER
--   auth.users is the only source of truth for credentials and the confirmed
--   email. public.users keeps the application profile and mirrors `email`
--   one-way through a trigger on auth.users.
--
-- Columns deliberately KEPT (not redundant):
--   phone      - contact phone of the profile. auth.users.phone is empty for
--                every account (email-only provider), so this is the only copy.
--   full_name  - display name owned by the profile and user-editable through
--                PATCH /api/v1/users/me. Only seeded from signup metadata.
--   status     - application state ('active', 'guest', 'pending_verification'),
--                not a mirror of auth.users.email_confirmed_at.
--
-- Companion rollback: 20261010000000_unify_user_identity_rollback.sql

begin;

-- 1. Keep a recoverable copy of every column this migration drops ------------
create table if not exists public._backup_users_auth_overlap (
  user_id uuid primary key,
  email varchar(320),
  phone varchar(32),
  password_hash varchar(512),
  verified_at timestamptz,
  status varchar(32),
  auth_user_id uuid,
  backed_up_at timestamptz not null default now()
);

-- The insert is guarded so that re-running this migration after the columns
-- were dropped stays a no-op instead of failing on an undefined column.
do $mig$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'users' and column_name = 'password_hash'
  ) then
    insert into public._backup_users_auth_overlap (user_id, email, phone, password_hash, verified_at, status, auth_user_id)
    select id, email, phone, password_hash, verified_at, status, auth_user_id
      from public.users
    on conflict (user_id) do nothing;
  end if;
end
$mig$;

alter table public._backup_users_auth_overlap enable row level security;
revoke all on public._backup_users_auth_overlap from anon, authenticated;
grant all on public._backup_users_auth_overlap to service_role;

-- 2. Link profiles that already have a matching Supabase identity ------------
-- pgcrypto is not required; lower() is enough because Supabase stores the
-- canonical lower-case email.
update public.users u
   set auth_user_id = a.id
  from auth.users a
 where u.auth_user_id is null
   and u.email is not null
   and lower(a.email) = lower(u.email);

-- 3. Enforce the link that was only documented before ------------------------
alter table public.users drop constraint if exists users_auth_user_id_fkey;
alter table public.users
  add constraint users_auth_user_id_fkey
  foreign key (auth_user_id) references auth.users(id) on delete cascade;

-- 4. Mirror the login email one-way: auth.users -> public.users --------------
-- SECURITY DEFINER is required because the trigger fires as supabase_auth_admin
-- and public.users is owned by postgres.
create or replace function public.sync_user_email_from_auth()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $body$
begin
  update public.users
     set email = new.email,
         updated_at = now()
   where auth_user_id = new.id
     and email is distinct from new.email;
  return new;
end
$body$;

drop trigger if exists trg_sync_user_email_from_auth on auth.users;
create trigger trg_sync_user_email_from_auth
  after insert or update of email on auth.users
  for each row execute function public.sync_user_email_from_auth();

-- Backfill rows that were already linked before the trigger existed.
update public.users u
   set email = a.email
  from auth.users a
 where a.id = u.auth_user_id
   and u.email is distinct from a.email;

-- 5. Drop the duplicated columns --------------------------------------------
alter table public.users drop column if exists password_hash;
alter table public.users drop column if exists verified_at;

comment on column public.users.auth_user_id is
  'Supabase Auth identity (auth.users.id), FK ON DELETE CASCADE. NULL only for guest profiles that never sign in.';
comment on column public.users.email is
  'Mirror of auth.users.email maintained by trg_sync_user_email_from_auth. Do not write directly.';
comment on column public.users.phone is
  'Contact phone of the profile. Not a login credential and not stored in auth.users.';
comment on column public.users.full_name is
  'Display name owned by the application profile, seeded once from signup metadata.';
comment on column public.users.status is
  'Application state: active | guest | pending_verification.';

commit;
