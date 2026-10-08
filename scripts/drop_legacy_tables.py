"""
Script to safely drop redundant legacy chat tables after successful migration:
- chat_turns
- chat_conversations
- coordination_messages

Core booking tables (bookings, booking_holds, weekly_shifts, package_requests) and coordination_cases are untouched.
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


async def drop_legacy_tables():
    backup_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backup_legacy_data.json"))
    if not os.path.exists(backup_file):
        raise RuntimeError(f"Backup file not found at {backup_file}! Aborting drop for safety.")

    size_mb = os.path.getsize(backup_file) / (1024 * 1024)
    logger.info(f"Verified backup exists at {backup_file} ({size_mb:.2f} MB)")

    engine = get_engine()
    logger.info("Connecting to database...")

    async with engine.begin() as conn:
        logger.info("Dropping table chat_turns...")
        await conn.execute(text("DROP TABLE IF EXISTS public.chat_turns CASCADE;"))

        logger.info("Dropping table chat_conversations...")
        await conn.execute(text("DROP TABLE IF EXISTS public.chat_conversations CASCADE;"))

        logger.info("Dropping table coordination_messages...")
        await conn.execute(text("DROP TABLE IF EXISTS public.coordination_messages CASCADE;"))

        logger.info("Checking remaining tables...")
        remaining = (await conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name IN ('chat_turns', 'chat_conversations', 'coordination_messages');
        """))).scalars().all()

        if remaining:
            raise RuntimeError(f"Tables still exist: {remaining}")
        logger.info("SUCCESS: All redundant tables (chat_turns, chat_conversations, coordination_messages) have been dropped.")

        # Verify unified tables
        unified_stats = (await conn.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM public.conversations) AS conversations_count,
                (SELECT COUNT(*) FROM public.messages) AS messages_count,
                (SELECT COUNT(*) FROM public.patient_chat_context) AS patient_chat_context_count,
                (SELECT COUNT(*) FROM public.conversation_participants) AS participants_count;
        """))).mappings().one()
        logger.info(f"Verified Unified Tables Healthy: {dict(unified_stats)}")


if __name__ == "__main__":
    asyncio.run(drop_legacy_tables())
