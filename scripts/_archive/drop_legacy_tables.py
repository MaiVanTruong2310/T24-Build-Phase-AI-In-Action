"""Audit legacy and unified chat tables without modifying the database.

Legacy history is retained for compatibility and rollback. This command is
intentionally read-only; cleanup requires a separately approved task.
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text

from src.db.session import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def audit_legacy_tables():
    engine = get_engine()
    tables = (
        "chat_conversations",
        "chat_turns",
        "coordination_messages",
        "conversations",
        "messages",
        "patient_chat_context",
        "conversation_participants",
    )
    async with engine.connect() as conn:
        for table in tables:
            exists = await conn.scalar(
                text("SELECT to_regclass(:qualified_table)"), {"qualified_table": f"public.{table}"}
            )
            count = await conn.scalar(text(f"SELECT COUNT(*) FROM public.{table}")) if exists else None
            logger.info("table=%s exists=%s rows=%s", table, bool(exists), count)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(audit_legacy_tables())
