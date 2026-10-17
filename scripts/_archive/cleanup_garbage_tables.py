"""Clean up redundant backup schemas and unused indexes on Supabase."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg
from src.config import get_settings


def main():
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    print("Connecting to Supabase PostgreSQL...")
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            # 1. Inspect existing tables in backend_migration_backup and source_archive
            cur.execute("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema IN ('backend_migration_backup', 'source_archive')
                ORDER BY table_schema, table_name;
            """)
            backup_tables = cur.fetchall()
            print(f"Found {len(backup_tables)} tables in backup/archive schemas:")
            for schema, tbl in backup_tables:
                print(f"  - {schema}.{tbl}")

            # 2. Drop schemas CASCADE
            print("\nDropping schemas 'backend_migration_backup' and 'source_archive'...")
            cur.execute("DROP SCHEMA IF EXISTS backend_migration_backup CASCADE;")
            cur.execute("DROP SCHEMA IF EXISTS source_archive CASCADE;")
            print("Successfully dropped backup & archive schemas!")

            # 3. Clean duplicate redundant indexes on public schema
            print("\nCleaning up duplicate indexes in public schema...")
            duplicate_indexes = [
                "ix_doctors_code",
                "ix_facilities_code",
                "ix_services_code",
                "ix_specialties_code",
                "ix_users_phone",
            ]
            for idx in duplicate_indexes:
                cur.execute(f"DROP INDEX IF EXISTS public.{idx};")
                print(f"  - Dropped duplicate index: {idx}")

            # 4. Clean duplicate constraint if exists
            cur.execute("ALTER TABLE public.doctor_specialties DROP CONSTRAINT IF EXISTS uq_doctor_specialty;")
            print("  - Dropped duplicate constraint: doctor_specialties.uq_doctor_specialty")

            # 5. Verify remaining schemas
            cur.execute("""
                SELECT table_schema, count(*) 
                FROM information_schema.tables 
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                GROUP BY table_schema;
            """)
            print("\nRemaining schemas and table counts:")
            for schema, count in cur.fetchall():
                print(f"  - {schema}: {count} tables")

    print("\nCleanup completed successfully!")


if __name__ == "__main__":
    main()
