import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from src.db.session import get_engine
from src.models.patient_memory import MEMORY_TABLES


async def main():
    engine = get_engine()
    async with engine.begin() as conn:
        for table in MEMORY_TABLES:
            await conn.run_sync(lambda sync_conn, t=table: t.create(sync_conn, checkfirst=True))
            await conn.execute(text(f"ALTER TABLE {table.name} ENABLE ROW LEVEL SECURITY"))
            await conn.execute(text(f"REVOKE ALL ON {table.name} FROM anon, authenticated"))
        count = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM pg_tables WHERE schemaname=current_schema() AND tablename=ANY(:tables)"
                ),
                {"tables": [t.name for t in MEMORY_TABLES]},
            )
        ).scalar_one()
        if count != len(MEMORY_TABLES):
            raise RuntimeError("Patient memory schema verification failed.")
    await engine.dispose()
    print("Patient memory schema applied and verified successfully.")


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
