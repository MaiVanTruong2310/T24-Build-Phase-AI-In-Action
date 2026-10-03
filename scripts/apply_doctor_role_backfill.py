"""Apply role classification migration to an unversioned Supabase database."""

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
    path = ROOT / "alembic" / "versions" / "0014_doctor_role_backfill.py"
    spec = importlib.util.spec_from_file_location("doctor_role_backfill", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load doctor role migration")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    collector = Collector()
    migration.op = collector
    migration.upgrade()
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='doctors' AND column_name='professional_role'")
            if cursor.fetchone():
                print("Doctor roles already exist")
                return
            for statement in collector.statements:
                cursor.execute(statement)
            cursor.execute("SELECT professional_role, count(*) FROM doctors GROUP BY professional_role ORDER BY professional_role")
            summary = cursor.fetchall()
        connection.commit()
    print(f"Applied role backfill: {ascii(summary)}")


if __name__ == "__main__":
    main()
