-- Rollback for 20261010000000_unify_user_identity.sql
--
-- Restores the two dropped columns from public._backup_users_auth_overlap and
-- removes the trigger, the foreign key and the email mirror function.
-- It does NOT restore the trigger-created email values on rows that were
-- backfilled from auth.users; use the backup table if the original value
-- differed.

begin;

alter table public.users add column if not exists password_hash varchar(512);
alter table public.users add column if not exists verified_at timestamptz;

update public.users u
   set password_hash = b.password_hash,
       verified_at = b.verified_at
  from public._backup_users_auth_overlap b
 where b.user_id = u.id;

drop trigger if exists trg_sync_user_email_from_auth on auth.users;
drop function if exists public.sync_user_email_from_auth();

alter table public.users drop constraint if exists users_auth_user_id_fkey;

commit;
