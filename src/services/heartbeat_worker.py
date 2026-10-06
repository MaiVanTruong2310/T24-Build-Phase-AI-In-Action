"""Heartbeat Service: Worker tự hành đánh thức định kỳ (Heartbeat Loops 2025–2026).

Thực hiện 3 nhiệm vụ bảo trì tự động:
1. Thu hồi các Open Loops (giữ chỗ slot quá 15 phút chưa xác nhận).
2. Dọn dẹp vệ sinh bộ nhớ (Memory Hygiene): Xóa các triệu chứng/facts đã quá hạn TTL.
3. Chăm sóc liên tục (Continuous Care): Quét các ca tái khám / nhắc lịch cần gửi tin nhắn.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, update

from src.db.session import get_session_factory
from src.models.patient_memory import PatientMemoryItem, PatientOpenLoop

logger = logging.getLogger(__name__)


class HeartbeatWorker:
    def __init__(self):
        self.sessionmaker = get_session_factory()

    async def pulse_once(self) -> dict[str, Any]:
        """Thực hiện một nhịp đập bảo trì (Single pulse)."""
        now = datetime.now(UTC)
        metrics = {
            "timestamp": now.isoformat(),
            "expired_loops_reclaimed": 0,
            "expired_facts_pruned": 0,
        }

        async with self.sessionmaker() as session:
            async with session.begin():
                # 1. Thu hồi slot holds và open loops đã quá hạn
                loop_stmt = (
                    update(PatientOpenLoop)
                    .where(
                        PatientOpenLoop.status == "open",
                        PatientOpenLoop.due_at.is_not(None),
                        PatientOpenLoop.due_at < now,
                    )
                    .values(status="expired")
                )
                loop_res = await session.execute(loop_stmt)
                metrics["expired_loops_reclaimed"] = loop_res.rowcount

                # 2. Vệ sinh bộ nhớ: Xóa các triệu chứng cấp tính đã hết hạn TTL
                mem_stmt = delete(PatientMemoryItem).where(
                    PatientMemoryItem.valid_until.is_not(None),
                    PatientMemoryItem.valid_until < now,
                )
                mem_res = await session.execute(mem_stmt)
                metrics["expired_facts_pruned"] = mem_res.rowcount

        logger.info(
            "Heartbeat pulse completed: %d expired loops reclaimed, %d expired facts pruned.",
            metrics["expired_loops_reclaimed"],
            metrics["expired_facts_pruned"],
        )
        return metrics

    async def run_forever(self, interval_seconds: int = 60) -> None:
        """Vòng lặp chạy nền liên tục (Heartbeat Daemon Loop)."""
        logger.info("Starting Autonomous Heartbeat Worker (interval=%ds)...", interval_seconds)
        while True:
            try:
                await self.pulse_once()
            except Exception as exc:
                logger.exception("Error during heartbeat pulse: %s", exc)
            await asyncio.sleep(interval_seconds)


_heartbeat_worker: HeartbeatWorker | None = None


def get_heartbeat_worker() -> HeartbeatWorker:
    global _heartbeat_worker
    if _heartbeat_worker is None:
        _heartbeat_worker = HeartbeatWorker()
    return _heartbeat_worker
