import asyncio, sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from sqlalchemy import text
from src.db.session import get_session_factory

async def check():
    factory = get_session_factory()
    async with factory() as session:
        res = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        print('Tables:', sorted([r[0] for r in res.all()]))

asyncio.run(check())
