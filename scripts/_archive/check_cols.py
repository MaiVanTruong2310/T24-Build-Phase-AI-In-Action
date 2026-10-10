import asyncio, sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from sqlalchemy import text
from src.db.session import get_session_factory

async def check():
    factory = get_session_factory()
    async with factory() as session:
        res = await session.execute(text("SELECT column_name, is_nullable, data_type FROM information_schema.columns WHERE table_name = 'consultation_requests'"))
        for col, null, dtype in res.all():
            print(f"  {col}: nullable={null}, type={dtype}")

asyncio.run(check())
