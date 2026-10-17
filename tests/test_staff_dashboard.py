from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from src.api.endpoints import staff_dashboard as staff_dashboard_api
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


@pytest.mark.asyncio
async def test_dashboard_scoped_queries_apply_facility_and_doctor_filters():
    class Result:
        def scalar_one(self):
            return 0

    class Session:
        statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return Result()

    facility_id, doctor_id = uuid4(), uuid4()
    session = Session()
    start = datetime.fromisoformat("2026-10-09T00:00:00+07:00")
    end = datetime.fromisoformat("2026-10-10T00:00:00+07:00")
    await dashboard_summary(session, start, end, facility_id, doctor_id)

    sql = [
        str(statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
        for statement in session.statements
    ]
    for index in (0, 1, 4, 5, 6, 7, 8, 9):
        assert str(facility_id) in sql[index]
        assert str(doctor_id) in sql[index]
    assert str(facility_id) not in sql[2]
    assert str(doctor_id) not in sql[2]


@pytest.mark.asyncio
async def test_dashboard_route_forwards_facility_and_doctor_filters(monkeypatch):
    facility_id, doctor_id = uuid4(), uuid4()
    start = datetime.fromisoformat("2026-10-09T00:00:00+07:00")
    end = datetime.fromisoformat("2026-10-10T00:00:00+07:00")
    captured = {}
    user_id = uuid4()

    async def fake_dashboard_summary(db, from_, to, facility, doctor):
        captured.update(facility_id=facility, doctor_id=doctor)
        return {"patients_total": 3}

    class Session:
        async def commit(self):
            pass

    async def get_cache(namespace, params):
        captured["cache_namespace"] = namespace
        captured["cache_params"] = params
        return False, None, "0"

    async def set_cache(_namespace, _params, _value, _generation):
        return None

    monkeypatch.setattr(staff_dashboard_api, "dashboard_summary", fake_dashboard_summary)
    monkeypatch.setattr(staff_dashboard_api, "get_redis_api_cache", get_cache)
    monkeypatch.setattr(staff_dashboard_api, "set_redis_api_cache", set_cache)
    await staff_dashboard_api.summary(start, end, facility_id, doctor_id, SimpleNamespace(id=user_id), Session())

    assert captured["facility_id"] == facility_id
    assert captured["doctor_id"] == doctor_id
    assert captured["cache_namespace"] == "staff-dashboard"
    assert captured["cache_params"] == (str(user_id), start.isoformat(), end.isoformat(), facility_id, doctor_id)


@pytest.mark.asyncio
async def test_dashboard_cache_hit_skips_aggregate_queries(monkeypatch):
    user_id = uuid4()
    start = datetime.fromisoformat("2026-10-09T00:00:00+07:00")
    end = datetime.fromisoformat("2026-10-10T00:00:00+07:00")
    expected = {"range": {"from": start.isoformat(), "to": end.isoformat()}, "metrics": {"patients_total": 4}}

    async def get_cache(_namespace, _params):
        return True, expected, "0"

    async def unexpected_query(*_args):
        raise AssertionError("cache hit should skip dashboard aggregation")

    class Session:
        async def commit(self):
            pass

    monkeypatch.setattr(staff_dashboard_api, "get_redis_api_cache", get_cache)
    monkeypatch.setattr(staff_dashboard_api, "dashboard_summary", unexpected_query)
    response = await staff_dashboard_api.summary(start, end, None, None, SimpleNamespace(id=user_id), Session())

    assert response.data == expected
