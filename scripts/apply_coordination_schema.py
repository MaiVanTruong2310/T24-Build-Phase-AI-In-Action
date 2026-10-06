"""Apply the additive coordination schema to an existing unversioned database.

The project also carries the Alembic migration. This helper is for the existing
Supabase database, which has no alembic_version table. It applies the same DDL
atomically and leaves all existing tables and rows untouched.
"""

import importlib.util
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import get_settings  # noqa: E402

TABLES = (
    "weekly_shifts", "consultation_sessions", "consultation_slots",
    "consultation_requests", "consultation_request_events",
)


class Collector:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, sql: str) -> None:
        self.statements.append(sql)


def main() -> None:
    migration_path = ROOT / "alembic" / "versions" / "0012_consultation_coordination.py"
    spec = importlib.util.spec_from_file_location("coordination_migration", migration_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load coordination migration")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    collector = Collector()
    migration.op = collector
    migration.upgrade()

    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            names = [f"public.{name}" for name in TABLES]
            cursor.execute("SELECT to_regclass(name) FROM unnest(%s::text[]) AS name", (names,))
            existing = [row[0] is not None for row in cursor.fetchall()]
            if all(existing):
                print("Coordination schema already exists")
                return
            if any(existing):
                raise RuntimeError("Partial coordination schema detected; inspect before applying")
            for statement in collector.statements:
                cursor.execute(statement)
            cursor.execute("SELECT to_regclass(name) FROM unnest(%s::text[]) AS name", (names,))
            if not all(row[0] is not None for row in cursor.fetchall()):
                raise RuntimeError("Schema verification failed")
        connection.commit()
    print(f"Applied {len(collector.statements)} statements; {len(TABLES)} tables verified")


if __name__ == "__main__":
    main()
