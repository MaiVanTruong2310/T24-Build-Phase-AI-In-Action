"""Copy legacy Supabase takeover rows into EC2 coordination tables, idempotently."""

import argparse
import asyncio
import hashlib
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from src.config import get_settings
from src.db.session import get_auth_session_factory, get_session_factory
from src.models.chat_takeover import ChatTakeoverAuditEvent, ChatTakeoverCase, ChatTakeoverMessage
from src.models.user import User
from src.models.workbench import CoordinationCase, CoordinationEvent, CoordinationMessage

logger = logging.getLogger("takeover_backfill")


def map_case_status(status: str) -> tuple[str, str, bool]:
    if status == "resolved":
        return "completed", "ai", False
    if status == "taken_over":
        return "contacting", "human", False
    return "new", "human", status == "released"


async def copy_case(source, target, legacy_case) -> tuple[CoordinationCase, bool]:
    owner_key = f"user:{legacy_case.patient_user_id}"
    source_id = hashlib.sha256(f"{owner_key}:{legacy_case.session_id}".encode()).hexdigest()
    case = (
        await target.execute(
            select(CoordinationCase)
            .where(
                (CoordinationCase.legacy_takeover_case_id == legacy_case.id)
                | ((CoordinationCase.owner_key == owner_key) & (CoordinationCase.session_id == legacy_case.session_id))
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    created = case is None
    patient = await target.get(User, legacy_case.patient_user_id)
    staff = await target.get(User, legacy_case.assigned_staff_id) if legacy_case.assigned_staff_id else None
    status, control, released = map_case_status(legacy_case.status)
    summary = legacy_case.summary or {}
    if case is None:
        case = CoordinationCase(
            id=legacy_case.id,
            source="chat",
            source_id=source_id,
            owner_key=owner_key,
            session_id=legacy_case.session_id,
            patient_id=patient.id if patient else None,
            requested_by_user_id=patient.id if patient else None,
            patient={
                "name": summary.get("patient_name"),
                "gender": summary.get("patient_gender"),
            },
            ai_snapshot={},
            checkpoint={},
            plan={},
            status=status,
            priority=priority_number(legacy_case.priority),
            control=control,
            version=1,
            created_at=legacy_case.created_at,
        )
        target.add(case)
        await target.flush()
    if case.legacy_takeover_case_id not in (None, legacy_case.id):
        raise RuntimeError("A coordination case already has a different legacy takeover alias")
    case.legacy_takeover_case_id = legacy_case.id
    case.patient_id = patient.id if patient else None
    case.requested_by_user_id = patient.id if patient else None
    case.assigned_to = staff.id if staff and legacy_case.status == "taken_over" else None
    case.status, case.control = status, control
    case.priority = priority_number(legacy_case.priority)
    case.ai_snapshot = {
        **(case.ai_snapshot or {}),
        "workflow_status": legacy_case.workflow_status,
        "takeover_summary": summary,
    }
    case.checkpoint = {
        **(case.checkpoint or {}),
        "takeover_released": released,
        "takeover_claimed_at": legacy_case.claimed_at.isoformat() if legacy_case.claimed_at else None,
        "takeover_resolved_at": legacy_case.resolved_at.isoformat() if legacy_case.resolved_at else None,
    }
    case.updated_at = legacy_case.updated_at or datetime.now(UTC)

    messages = (
        (
            await source.execute(
                select(ChatTakeoverMessage)
                .where(ChatTakeoverMessage.case_id == legacy_case.id)
                .order_by(ChatTakeoverMessage.created_at, ChatTakeoverMessage.id)
            )
        )
        .scalars()
        .all()
    )
    for old_message in messages:
        client_id = old_message.client_message_id or f"legacy:{old_message.id}"
        existing = (
            await target.execute(
                select(CoordinationMessage).where(
                    CoordinationMessage.case_id == case.id,
                    CoordinationMessage.client_id == client_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        actor = await target.get(User, old_message.author_user_id) if old_message.author_user_id else None
        sender = {"staff": "coordinator", "assistant": "ai"}.get(old_message.author_type, old_message.author_type)
        target.add(
            CoordinationMessage(
                id=old_message.id,
                case_id=case.id,
                client_id=client_id,
                sender=sender,
                actor_id=actor.id if actor else None,
                body=old_message.content,
                created_at=old_message.created_at,
            )
        )

    events = (
        (
            await source.execute(
                select(ChatTakeoverAuditEvent)
                .where(ChatTakeoverAuditEvent.case_id == legacy_case.id)
                .order_by(ChatTakeoverAuditEvent.created_at, ChatTakeoverAuditEvent.id)
            )
        )
        .scalars()
        .all()
    )
    for old_event in events:
        exists = await target.get(CoordinationEvent, old_event.id)
        if exists is not None:
            continue
        actor = await target.get(User, old_event.actor_user_id) if old_event.actor_user_id else None
        target.add(
            CoordinationEvent(
                id=old_event.id,
                case_id=case.id,
                actor_id=actor.id if actor else None,
                action=f"takeover_{old_event.event_type}"[:40],
                details=old_event.event_metadata or {},
                created_at=old_event.created_at,
            )
        )
    return case, created


def priority_number(priority: str) -> int:
    return {"critical": 0, "high": 1, "normal": 2}.get(priority, 2)


async def backfill(apply_changes: bool) -> dict[str, int]:
    if not get_settings().auth_database_url:
        raise RuntimeError("AUTH_DATABASE_URL is required to read legacy takeover data")
    source_factory = get_auth_session_factory()
    target_factory = get_session_factory()
    totals = {"cases": 0, "created": 0, "messages": 0, "events": 0, "missing_patient_profiles": 0}
    async with source_factory() as source:
        legacy_cases = (
            (await source.execute(select(ChatTakeoverCase).order_by(ChatTakeoverCase.created_at, ChatTakeoverCase.id)))
            .scalars()
            .all()
        )
        for legacy_case in legacy_cases:
            async with target_factory() as target:
                try:
                    case, created = await copy_case(source, target, legacy_case)
                    await target.flush()
                    totals["cases"] += 1
                    totals["created"] += int(created)
                    totals["missing_patient_profiles"] += int(case.patient_id is None)
                    totals["messages"] += len(
                        (
                            await source.execute(
                                select(ChatTakeoverMessage.id).where(ChatTakeoverMessage.case_id == legacy_case.id)
                            )
                        ).all()
                    )
                    totals["events"] += len(
                        (
                            await source.execute(
                                select(ChatTakeoverAuditEvent.id).where(
                                    ChatTakeoverAuditEvent.case_id == legacy_case.id
                                )
                            )
                        ).all()
                    )
                    if not apply_changes:
                        await target.rollback()
                    else:
                        await target.commit()
                except Exception:
                    await target.rollback()
                    raise
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit the copy; default is rollback/dry-run")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    totals = asyncio.run(backfill(args.apply))
    mode = "applied" if args.apply else "dry-run"
    logger.info("takeover backfill %s: %s", mode, totals)


if __name__ == "__main__":
    main()
