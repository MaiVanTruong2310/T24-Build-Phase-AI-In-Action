"""Apply only the reviewed workbench tables, without changing existing tables."""
import asyncio
from sqlalchemy import text
from src.db.session import get_engine
from src.models.workbench import WORKBENCH_TABLES


async def main():
    engine = get_engine()
    async with engine.begin() as conn:
        for table in WORKBENCH_TABLES:
            await conn.run_sync(lambda sync_conn, t=table: t.create(sync_conn, checkfirst=True))
            await conn.execute(text(f'ALTER TABLE {table.name} ENABLE ROW LEVEL SECURITY'))
            await conn.execute(text(f'REVOKE ALL ON {table.name} FROM anon, authenticated'))
        count = (await conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname=current_schema() AND tablename=ANY(:tables)"), {'tables': [t.name for t in WORKBENCH_TABLES]})).scalar_one()
        if count != len(WORKBENCH_TABLES):
            raise RuntimeError('Workbench schema verification failed.')
    await engine.dispose()
    print('Workbench schema verified. Browser roles have no direct table grants.')


if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
