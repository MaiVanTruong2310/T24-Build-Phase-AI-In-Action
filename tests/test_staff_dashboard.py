from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from src.api.endpoints.staff_dashboard import resolve_range
from src.main import app
from src.services.staff_dashboard import dashboard_summary


def test_dashboard_range_requires_timezone_and_both_bounds():
    start = datetime.fromisoformat("2026-10-09T00:00:00+07:00")
    end = datetime.fromisoformat("2026-10-10T00:00:00+07:00")
    assert resolve_range(start, end) == (start, end)

    with pytest.raises(HTTPException, match="đồng thời"):
        resolve_range(start, None)
    with pytest.raises(HTTPException, match="timezone"):
        resolve_range(datetime(2026, 10, 9), datetime(2026, 10, 10))
    with pytest.raises(HTTPException, match="from phải trước to"):
        resolve_range(end, start)


def test_staff_dashboard_summary_route_is_mounted():
    assert "/api/v1/staff/dashboard/summary" in app.openapi()["paths"]


@pytest.mark.asyncio
async def test_dashboard_builds_aggregate_only_queries_for_metrics():
    class Result:
        def scalar_one(self):
            return 2

    class Session:
        statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return Result()

    session = Session()
    start = datetime.fromisoformat("2026-10-09T00:00:00+07:00")
    end = datetime.fromisoformat("2026-10-10T00:00:00+07:00")
    metrics = await dashboard_summary(session, start, end, uuid4(), uuid4())

    assert len(metrics) == len(session.statements) == 10
    assert all(value == 2 for value in metrics.values())
    sql = [str(statement.compile(dialect=postgresql.dialect())) for statement in session.statements]
    assert all("count(" in statement.lower() for statement in sql)
