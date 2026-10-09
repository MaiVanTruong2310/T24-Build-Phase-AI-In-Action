"""Staff dashboard aggregate API."""

from datetime import datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_staff
from src.api.response import success_response
from src.db.dependencies import get_db_session
from src.models.user import User
from src.services.staff_dashboard import dashboard_summary

router = APIRouter(prefix="/staff/dashboard", tags=["staff-dashboard"])
BUSINESS_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def resolve_range(start: datetime | None, end: datetime | None) -> tuple[datetime, datetime]:
    if (start is None) != (end is None):
        raise HTTPException(400, "Cần truyền đồng thời from và to.")
    if start is None:
        today = datetime.now(BUSINESS_TZ).date()
        start = datetime.combine(today, time.min, BUSINESS_TZ)
        end = datetime.combine(today + timedelta(days=1), time.min, BUSINESS_TZ)
    assert end is not None
    if start.utcoffset() is None or end.utcoffset() is None or start >= end:
        raise HTTPException(400, "Khoảng thời gian cần có timezone và from phải trước to.")
    return start, end


@router.get("/summary")
async def summary(
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = None,
    facility_id: UUID | None = None,
    doctor_id: UUID | None = None,
    _: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db_session),
):
    from_, to = resolve_range(from_, to)

    metrics = await dashboard_summary(db, from_, to, facility_id, doctor_id)
    await db.commit()
    return success_response(
        {
            "range": {"from": from_.isoformat(), "to": to.isoformat()},
            "timezone": "Asia/Ho_Chi_Minh",
            "metrics": metrics,
        }
    )
