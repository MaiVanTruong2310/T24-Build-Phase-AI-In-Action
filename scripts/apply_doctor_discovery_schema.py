"""Apply migration 0013 atomically to the existing unversioned Supabase database."""

import importlib.util
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import get_settings  # noqa: E402


class Collector:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, sql: str) -> None:
        self.statements.append(sql)


def main() -> None:
    path = ROOT / "alembic" / "versions" / "0013_doctor_discovery.py"
    spec = importlib.util.spec_from_file_location("doctor_discovery_migration", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load doctor discovery migration")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    collector = Collector()
    migration.op = collector
    migration.upgrade()
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name, column_name, data_type, udt_name FROM information_schema.columns
                WHERE table_schema = 'public' AND (
                    (table_name = 'doctors' AND column_name IN
                     ('honors','academic_ranks','degrees','languages','position','experience_years','education','work_history','awards'))
                    OR (table_name = 'doctor_facilities' AND column_name IN ('position','is_primary'))
                )
            """)
            found = cursor.fetchall()
            existing = {(row[0], row[1]) for row in found}
            if len(existing) == 11:
                print("Doctor discovery schema already exists")
                return
            if existing != {("doctors", "languages")}:
                raise RuntimeError(f"Partial doctor discovery schema detected: {sorted(found)}")
            for statement in collector.statements:
                cursor.execute(statement)
            cursor.execute("""
                SELECT count(*) FROM information_schema.columns
                WHERE table_schema = 'public' AND (
                    (table_name = 'doctors' AND column_name IN
                     ('honors','academic_ranks','degrees','languages','position','experience_years','education','work_history','awards'))
                    OR (table_name = 'doctor_facilities' AND column_name IN ('position','is_primary'))
                )
            """)
            if cursor.fetchone()[0] != 11:
                raise RuntimeError("Schema verification failed")
        connection.commit()
    print(f"Applied {len(collector.statements)} statements; 11 columns verified")


if __name__ == "__main__":
    main()
