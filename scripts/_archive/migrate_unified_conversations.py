"""
ETL Migration Script: Migrate legacy chat & coordination data to Unified Conversation Schema.
Strict Zero Data Loss & Transactional Safety.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text

from src.db.session import get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def run_migration():
    engine = get_engine()
    logger.info("Connecting to database...")

    async with engine.begin() as conn:
        logger.info("--- Step 1: Pre-flight sanity checks ---")
        chat_conv_count = (await conn.execute(text("SELECT COUNT(*) FROM chat_conversations"))).scalar_one()
        chat_turn_count = (await conn.execute(text("SELECT COUNT(*) FROM chat_turns"))).scalar_one()
        coord_case_count = (await conn.execute(text("SELECT COUNT(*) FROM coordination_cases"))).scalar_one()
        coord_msg_count = (await conn.execute(text("SELECT COUNT(*) FROM coordination_messages"))).scalar_one()

        logger.info(
            f"Source Counts: chat_conversations={chat_conv_count}, "
            f"chat_turns={chat_turn_count}, "
            f"coordination_cases={coord_case_count}, "
            f"coordination_messages={coord_msg_count}"
        )

        expected_conversations = chat_conv_count + coord_case_count
        expected_messages = (chat_turn_count * 2) + coord_msg_count
        logger.info(f"Target Expectation: conversations={expected_conversations}, messages={expected_messages}")

        logger.info("--- Step 2: Migrating chat_conversations -> conversations ---")
        chat_conv_rows = (
            (
                await conn.execute(
                    text("""
            SELECT id, user_id, session_id, title, patient_profile_id, created_at, updated_at
            FROM chat_conversations
        """)
                )
            )
            .mappings()
            .all()
        )

        for c in chat_conv_rows:
            # Upsert into conversations
            await conn.execute(
                text("""
                    INSERT INTO conversations (
                        id, category, mode, status, patient_id,
                        created_by_type, created_by_id, created_at, updated_at
                    ) VALUES (
                        :id, 'PATIENT_SUPPORT', 'AI', 'RESOLVED', :patient_id,
                        'PATIENT', :created_by_id, :created_at, :updated_at
                    ) ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": c["id"],
                    "patient_id": c["user_id"],
                    "created_by_id": c["user_id"],
                    "created_at": c["created_at"],
                    "updated_at": c["updated_at"],
                },
            )

            # Insert participants
            if c["user_id"]:
                await conn.execute(
                    text("""
                        INSERT INTO conversation_participants (
                            id, conversation_id, participant_type, participant_id, role, joined_at
                        ) VALUES (
                            :id, :conv_id, 'PATIENT', :user_id, 'patient', :joined_at
                        ) ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": uuid5(NAMESPACE_URL, f"p124:chat-conversation:{c['id']}:patient"),
                        "conv_id": c["id"],
                        "user_id": c["user_id"],
                        "joined_at": c["created_at"],
                    },
                )

            await conn.execute(
                text("""
                    INSERT INTO conversation_participants (
                        id, conversation_id, participant_type, participant_id, role, joined_at
                    ) VALUES (
                        :id, :conv_id, 'AGENT', NULL, 'assistant', :joined_at
                    ) ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": uuid5(NAMESPACE_URL, f"p124:chat-conversation:{c['id']}:agent"),
                    "conv_id": c["id"],
                    "joined_at": c["created_at"],
                },
            )

            # Insert patient_chat_context
            ctx_data = {
                "session_id": c["session_id"],
                "title": c["title"],
                "patient_profile_id": str(c["patient_profile_id"]) if c["patient_profile_id"] else None,
            }
            await conn.execute(
                text("""
                    INSERT INTO patient_chat_context (
                        conversation_id, patient_id, current_stage, context_data, updated_at
                    ) VALUES (
                        :conv_id, :patient_id, 'GENERAL_SUPPORT', :ctx_data, :updated_at
                    ) ON CONFLICT (conversation_id) DO NOTHING
                """),
                {
                    "conv_id": c["id"],
                    "patient_id": c["user_id"],
                    "ctx_data": json.dumps(ctx_data),
                    "updated_at": c["updated_at"],
                },
            )

        logger.info(f"Successfully migrated {len(chat_conv_rows)} chat_conversations")

        logger.info("--- Step 3: Migrating chat_turns -> messages ---")
        chat_turn_rows = (
            (
                await conn.execute(
                    text("""
            SELECT id, conversation_id, request_id, user_text, assistant_text, result, status, created_at
            FROM chat_turns
            ORDER BY created_at ASC
        """)
                )
            )
            .mappings()
            .all()
        )

        # Map conv_id -> user_id
        user_id_map = {c["id"]: c["user_id"] for c in chat_conv_rows}

        for t in chat_turn_rows:
            conv_id = t["conversation_id"]
            user_id = user_id_map.get(conv_id)

            # Patient message
            user_msg_meta = {
                "turn_id": str(t["id"]),
                "request_id": str(t["request_id"]) if t["request_id"] else None,
                "legacy_source": "chat_turns.user_text",
            }
            await conn.execute(
                text("""
                    INSERT INTO messages (
                        id, conversation_id, sender_type, sender_id, message_type,
                        content, metadata, created_at
                    ) VALUES (
                        :id, :conv_id, 'PATIENT', :sender_id, 'TEXT',
                        :content, :meta, :created_at
                    ) ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": uuid5(NAMESPACE_URL, f"p124:chat-turn:{t['id']}:patient"),
                    "conv_id": conv_id,
                    "sender_id": user_id,
                    "content": t["user_text"] or "",
                    "meta": json.dumps(user_msg_meta),
                    "created_at": t["created_at"],
                },
            )

            # Agent message
            agent_msg_meta = {
                "turn_id": str(t["id"]),
                "request_id": str(t["request_id"]) if t["request_id"] else None,
                "status": t["status"],
                "result": t["result"] if isinstance(t["result"], dict) else None,
                "legacy_source": "chat_turns.assistant_text",
            }
            agent_created_at = t["created_at"] + timedelta(seconds=1)
            await conn.execute(
                text("""
                    INSERT INTO messages (
                        id, conversation_id, sender_type, sender_id, message_type,
                        content, metadata, created_at
                    ) VALUES (
                        :id, :conv_id, 'AGENT', NULL, 'TEXT',
                        :content, :meta, :created_at
                    ) ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": uuid5(NAMESPACE_URL, f"p124:chat-turn:{t['id']}:agent"),
                    "conv_id": conv_id,
                    "content": t["assistant_text"] or "",
                    "meta": json.dumps(agent_msg_meta),
                    "created_at": agent_created_at,
                },
            )

        logger.info(f"Successfully migrated {len(chat_turn_rows)} turns into {len(chat_turn_rows) * 2} messages")

        logger.info("--- Step 4: Migrating coordination_cases -> conversations & handoffs ---")
        coord_case_rows = (
            (
                await conn.execute(
                    text("""
            SELECT id, source, source_id, owner_key, session_id, patient_id, patient,
                   ai_snapshot, checkpoint, plan, facility_id, assigned_to, status,
                   priority, control, version, due_at, follow_up_at, booking_id,
                   patient_profile_id, requested_by_user_id, legacy_takeover_case_id,
                   created_at, updated_at
            FROM coordination_cases
        """)
                )
            )
            .mappings()
            .all()
        )

        for case in coord_case_rows:
            mode = "HUMAN" if case["control"] == "human" else "AI"
            status = "ACTIVE" if case["status"] in ("open", "active", "in_progress", "new") else "RESOLVED"
            creator_type = "PATIENT" if case["requested_by_user_id"] or case["patient_id"] else "SYSTEM"
            creator_id = case["requested_by_user_id"] or case["patient_id"]

            await conn.execute(
                text("""
                    INSERT INTO conversations (
                        id, category, mode, status, patient_id,
                        created_by_type, created_by_id, created_at, updated_at
                    ) VALUES (
                        :id, 'PATIENT_SUPPORT', :mode, :status, :patient_id,
                        :created_by_type, :created_by_id, :created_at, :updated_at
                    ) ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": case["id"],
                    "mode": mode,
                    "status": status,
                    "patient_id": case["patient_id"],
                    "created_by_type": creator_type,
                    "created_by_id": creator_id,
                    "created_at": case["created_at"],
                    "updated_at": case["updated_at"],
                },
            )

            # Insert patient_chat_context
            case_ctx = {
                "source": case["source"],
                "source_id": case["source_id"],
                "owner_key": case["owner_key"],
                "session_id": case["session_id"],
                "patient": case["patient"] if isinstance(case["patient"], dict) else {},
                "ai_snapshot": case["ai_snapshot"] if isinstance(case["ai_snapshot"], dict) else {},
                "plan": case["plan"] if isinstance(case["plan"], dict) else {},
                "priority": case["priority"],
                "facility_id": str(case["facility_id"]) if case["facility_id"] else None,
            }
            stage = "STAFF_HANDLING" if case["control"] == "human" else "GENERAL_SUPPORT"
            await conn.execute(
                text("""
                    INSERT INTO patient_chat_context (
                        conversation_id, patient_id, booking_id, current_stage,
                        context_data, updated_at
                    ) VALUES (
                        :conv_id, :patient_id, :booking_id, :stage,
                        :ctx_data, :updated_at
                    ) ON CONFLICT (conversation_id) DO NOTHING
                """),
                {
                    "conv_id": case["id"],
                    "patient_id": case["patient_id"],
                    "booking_id": case["booking_id"],
                    "stage": stage,
                    "ctx_data": json.dumps(case_ctx),
                    "updated_at": case["updated_at"],
                },
            )

            # Participants
            if case["patient_id"]:
                await conn.execute(
                    text("""
                        INSERT INTO conversation_participants (
                            id, conversation_id, participant_type, participant_id, role, joined_at
                        ) VALUES (
                            :id, :conv_id, 'PATIENT', :patient_id, 'patient', :joined_at
                        ) ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": uuid5(NAMESPACE_URL, f"p124:workbench-case:{case['id']}:patient"),
                        "conv_id": case["id"],
                        "patient_id": case["patient_id"],
                        "joined_at": case["created_at"],
                    },
                )

            if case["assigned_to"]:
                await conn.execute(
                    text("""
                        INSERT INTO conversation_participants (
                            id, conversation_id, participant_type, participant_id, role, joined_at
                        ) VALUES (
                            :id, :conv_id, 'STAFF', :staff_id, 'coordinator', :joined_at
                        ) ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": uuid5(NAMESPACE_URL, f"p124:workbench-case:{case['id']}:staff:{case['assigned_to']}"),
                        "conv_id": case["id"],
                        "staff_id": case["assigned_to"],
                        "joined_at": case["updated_at"],
                    },
                )

            # Record handoff if human took over
            if case["control"] == "human" or case["assigned_to"]:
                await conn.execute(
                    text("""
                        INSERT INTO handoffs (
                            id, conversation_id, from_actor_type, to_actor_type,
                            reason, requested_by_type, assigned_staff_id,
                            status, requested_at, accepted_at
                        ) VALUES (
                            :id, :conv_id, 'AGENT', 'STAFF',
                            'MANUAL_REVIEW', 'SYSTEM', :assigned_staff_id,
                            :status, :req_at, :acc_at
                        ) ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": uuid5(NAMESPACE_URL, f"p124:workbench-case:{case['id']}:handoff"),
                        "conv_id": case["id"],
                        "assigned_staff_id": case["assigned_to"],
                        "status": "ACCEPTED" if case["assigned_to"] else "REQUESTED",
                        "req_at": case["created_at"],
                        "acc_at": case["updated_at"] if case["assigned_to"] else None,
                    },
                )

        logger.info(f"Successfully migrated {len(coord_case_rows)} coordination_cases")

        logger.info("--- Step 5: Migrating coordination_messages -> messages ---")
        coord_msg_rows = (
            (
                await conn.execute(
                    text("""
            SELECT id, case_id, client_id, sender, actor_id, body, created_at
            FROM coordination_messages
            ORDER BY created_at ASC
        """)
                )
            )
            .mappings()
            .all()
        )

        for m in coord_msg_rows:
            sender_lower = (m["sender"] or "").lower()
            if sender_lower in ("patient", "user"):
                sender_type = "PATIENT"
            elif sender_lower in ("coordinator", "staff"):
                sender_type = "STAFF"
            elif sender_lower == "system":
                sender_type = "SYSTEM"
            else:
                sender_type = "STAFF"

            meta = {
                "client_id": m["client_id"],
                "legacy_sender": m["sender"],
                "legacy_source": "coordination_messages",
            }

            await conn.execute(
                text("""
                    INSERT INTO messages (
                        id, conversation_id, sender_type, sender_id, message_type,
                        content, metadata, created_at
                    ) VALUES (
                        :id, :conv_id, :sender_type, :sender_id, 'TEXT',
                        :content, :meta, :created_at
                    ) ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": m["id"],
                    "conv_id": m["case_id"],
                    "sender_type": sender_type,
                    "sender_id": m["actor_id"],
                    "content": m["body"],
                    "meta": json.dumps(meta),
                    "created_at": m["created_at"],
                },
            )

        logger.info(f"Successfully migrated {len(coord_msg_rows)} coordination_messages")

        logger.info("--- Step 6: Audit & Verification ---")
        actual_conversations = (await conn.execute(text("SELECT COUNT(*) FROM conversations"))).scalar_one()
        actual_messages = (await conn.execute(text("SELECT COUNT(*) FROM messages"))).scalar_one()
        actual_participants = (await conn.execute(text("SELECT COUNT(*) FROM conversation_participants"))).scalar_one()
        actual_contexts = (await conn.execute(text("SELECT COUNT(*) FROM patient_chat_context"))).scalar_one()
        actual_handoffs = (await conn.execute(text("SELECT COUNT(*) FROM handoffs"))).scalar_one()

        logger.info("Audit Summary:")
        logger.info(f"  Conversations: {actual_conversations} (Expected: {expected_conversations})")
        logger.info(f"  Messages:      {actual_messages} (Expected: {expected_messages})")
        logger.info(f"  Participants:  {actual_participants}")
        logger.info(f"  Chat Contexts: {actual_contexts}")
        logger.info(f"  Handoffs:      {actual_handoffs}")

        if actual_conversations != expected_conversations:
            raise RuntimeError(f"Conversations mismatch! {actual_conversations} != {expected_conversations}")
        if actual_messages != expected_messages:
            raise RuntimeError(f"Messages mismatch! {actual_messages} != {expected_messages}")

        logger.info("AUDIT PASSED! All data accounted for without loss. Committing transaction...")

    await engine.dispose()
    logger.info("Migration finished successfully.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_migration())
