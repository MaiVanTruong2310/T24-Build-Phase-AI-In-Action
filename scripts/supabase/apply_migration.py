"""Apply a SQL migration file to the Supabase Postgres instance.

Supabase CLI/MCP is not always available in the build environment, so this thin
runner executes a migration file over a direct psycopg connection.

The connection goes through the Supabase *transaction* pooler (port 6543) by
default, because the session pooler (5432) rejects new clients once its client
limit is reached. Prepared statements are disabled for pgbouncer compatibility.

Usage:
    python scripts/supabase/apply_migration.py scripts/supabase/migrations/<file>.sql
    python scripts/supabase/apply_migration.py <file>.sql --dry-run

``--dry-run`` rewrites the trailing ``commit;`` into ``rollback;`` so the whole
migration is executed and then discarded.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
POOLER_PORT = "6543"


def database_url(source: str) -> str:
    """Return the psycopg URL for the configured Supabase connection."""
    load_dotenv(REPO_ROOT / ".env")
    value = os.getenv(source)
    if not value:
        raise SystemExit(f"{source} is not configured (checked {REPO_ROOT / '.env'} and the environment)")
    return re.sub(r"postgresql(\+\w+)?://", "postgresql://", value, count=1).replace(":5432", f":{POOLER_PORT}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sql_file", type=Path, help="Migration file to execute")
    parser.add_argument("--dry-run", action="store_true", help="Execute then roll back instead of committing")
    parser.add_argument("--url-env", default="AUTH_DATABASE_URL", help="Environment variable holding the URL")
    args = parser.parse_args()

    if not args.sql_file.is_file():
        raise SystemExit(f"not a file: {args.sql_file}")

    sql = args.sql_file.read_text(encoding="utf-8")
    if args.dry_run:
        sql, replaced = re.subn(r"\bcommit\s*;\s*$", "rollback;\n", sql, flags=re.IGNORECASE)
        if not replaced:
            raise SystemExit("--dry-run requires the migration to end with 'commit;'")

    url = database_url(args.url_env)
    print(f"file   : {args.sql_file}")
    print(f"target : {url.split('@')[-1]}")
    print(f"mode   : {'DRY RUN (rollback)' if args.dry_run else 'APPLY'}")

    with psycopg.connect(url, autocommit=True, prepare_threshold=None) as connection:
        connection.execute(sql)
        version = connection.execute("select version()").fetchone()
        users = connection.execute(
            """
            select count(*) from information_schema.columns
            where table_schema='public' and table_name='users'
            """
        ).fetchone()
    print(f"server : {version[0].split(',')[0]}")
    print(f"public.users columns now: {users[0]}")
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
