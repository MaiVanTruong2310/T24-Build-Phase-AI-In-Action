import asyncio
from src.db.session import get_db_session
from src.models.user import User
from sqlalchemy import select

async def main():
    async for s in get_db_session():
        res = await s.execute(select(User.id, User.email, User.full_name, User.date_of_birth, User.gender).limit(10))
        for r in res.all():
            print(r)
        break

import sys

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
