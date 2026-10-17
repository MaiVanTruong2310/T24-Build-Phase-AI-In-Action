# Supabase backend schema alignment

Applied to project `uxtpazhbzpoohlhncwbh` on 2026-10-02.

`supabase_backend_alignment.sql` is a one-off bootstrap for the existing crawled schema, not an Alembic revision. Do not run the historical Alembic chain or stamp its heads against this database without reconciling those revisions first.

## Changes

- Add missing backend columns and `booking_holds`, `catalog_audit_events`, `notifications`.
- Align booking statuses, foreign keys, uniqueness, schedule overlap protection and required columns.
- Keep the five retired doctor columns absent; the doctor ORM and API no longer use them.
- Preserve legacy booking columns. Generate a default `booking_code` so backend inserts work without supplying the legacy field.
- Keep original crawl schedules without a verified facility in `source_archive.doctor_schedules`; these are not available appointment slots. No facility or service assignments are inferred.
- Keep original table data in `backend_migration_backup.*_20261002`. Backups preserve rows, not the complete original DDL.
- New operational tables have RLS enabled and deny browser-role access. The FastAPI backend uses its PostgreSQL connection.

## Execution and safeguards

The SQL runs in one transaction with lock/statement timeouts. It refuses to convert legacy bookings with existing rows before a mapping is prepared. Before applying, verify the target is the intended Supabase project and review the SQL. Use a PostgreSQL client that stops on errors.

The migration was executed first in a transaction that was rolled back, then applied. Temporary booking/hold/notification test records were also rolled back and were not retained.

## Verification

- All 15 ORM tables can be queried.
- 100 real doctor profiles with their specialty/facility assignments load and serialize successfully.
- Backend staff booking query succeeds.
- Hold expiry, booking status changes and notification insertion succeed with temporary fixtures.
- Existing row counts remain unchanged, except 1,984 source schedules are preserved in the archive and removed from live booking schedules.
- Anonymous/authenticated client roles cannot read/write the three new operational tables.

## Deployment

Deploy the accompanying doctor ORM/API changes before using doctor catalog endpoints. Keep `DATABASE_AUTO_CREATE=false`; `create_all()` does not reconcile existing columns. Both Railway database URLs must point at the intended Supabase database.
