from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.api.endpoints.coordination import VN_TZ
from src.db.dependencies import get_db_session
from src.main import app


@pytest.mark.asyncio
@pytest.mark.parametrize('value', ['1266-02-31', '2026-02-31', 'not-a-date', ''])
async def test_invalid_session_date_never_queries_database(client, monkeypatch, value):
    db = SimpleNamespace(execute=AsyncMock())
    async def database():
        yield db
    monkeypatch.setitem(app.dependency_overrides, get_db_session, database)
    response = await client.get('/api/v1/coordination/sessions', params={'doctor_id': str(uuid4()), 'date': value})
    assert response.status_code == 400
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_past_session_date_never_queries_database(client, monkeypatch):
    db = SimpleNamespace(execute=AsyncMock())
    async def database():
        yield db
    monkeypatch.setitem(app.dependency_overrides, get_db_session, database)
    yesterday = datetime.now(VN_TZ).date() - timedelta(days=1)
    response = await client.get('/api/v1/coordination/sessions', params={'doctor_id': str(uuid4()), 'date': yesterday.isoformat()})
    assert response.status_code == 409
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('days', [91, 100000])
async def test_far_future_session_date_never_queries_database(client, monkeypatch, days):
    db = SimpleNamespace(execute=AsyncMock())
    async def database():
        yield db
    monkeypatch.setitem(app.dependency_overrides, get_db_session, database)
    value = datetime.now(VN_TZ).date() + timedelta(days=days)
    response = await client.get('/api/v1/coordination/sessions', params={'doctor_id': str(uuid4()), 'date': value.isoformat()})
    assert response.status_code == 409
    db.execute.assert_not_awaited()
