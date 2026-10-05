"""Coordinator regressions: mocked database, no external services."""
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from src.api.endpoints import workbench as routes
from src.db.dependencies import get_db_session
from src.services import workbench as svc
from src.schemas.workbench import CaseAction, VerifyInput


@pytest.mark.asyncio
async def test_queue_repeated_poll_is_read_only(monkeypatch):
    sync = AsyncMock()
    expire = AsyncMock()
    monkeypatch.setattr(svc, 'sync_sources', sync)
    monkeypatch.setattr(svc, 'expire_deposits', expire)
    count = NS(scalar_one=lambda: 0)
    rows = NS(scalars=lambda: NS(all=lambda: []))
    db = NS(execute=AsyncMock(side_effect=[count, rows] * 3))
    app = FastAPI()
    app.include_router(routes.router)
    identity = (NS(id=uuid4()), NS(facility_ids=[]))
    async def access():
        return identity
    async def database():
        yield db
    app.dependency_overrides[routes.access] = access
    app.dependency_overrides[get_db_session] = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        for query in ('', '?q=test&mine=true', '?conversations=true&priority=0'):
            response = await client.get('/staff/workbench/cases' + query)
            assert response.status_code == 200
            assert response.json()['data'] == {'items': [], 'total': 0}
    sync.assert_not_awaited()
    expire.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('status', ['cancelled', 'completed', 'confirmed', 'planned', 'deposit_late'])
async def test_verify_never_reopens_closed_or_ineligible_case(status):
    actor = NS(id=uuid4())
    case = NS(version=2, assigned_to=actor.id, status=status)
    db = NS(execute=AsyncMock())
    with pytest.raises(HTTPException) as error:
        await svc.verify_deposit(db, case, actor, VerifyInput(version=2, reference='bank-ref', evidence='bank-record'))
    assert error.value.status_code == 409
    assert case.status == status
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_emergency_is_rejected():
    actor = NS(id=uuid4())
    case = NS(version=1, assigned_to=actor.id, status='waiting_deposit', priority=0, ai_snapshot={})
    db = NS(execute=AsyncMock())
    with pytest.raises(HTTPException) as error:
        await svc.verify_deposit(db, case, actor, VerifyInput(version=1, reference='bank-ref', evidence='bank-record'))
    assert error.value.status_code == 409
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handover_requires_recipient_on_duty():
    actor = NS(id=uuid4())
    recipient = uuid4()
    case = NS(version=1, assigned_to=actor.id, status='contacting', facility_id=None)
    target = NS(enabled=True, on_duty=False, facility_ids=[])
    db = NS(get=AsyncMock(side_effect=[target, NS(status='active', role='staff')]))
    with pytest.raises(HTTPException) as error:
        await svc.action(db, case, actor, NS(on_duty=True), CaseAction(version=1, action='handover', assigned_to=recipient, note='Shift summary'))
    assert error.value.status_code == 409
    assert case.assigned_to == actor.id
    assert case.version == 1


@pytest.mark.asyncio
async def test_handover_accepts_active_scoped_recipient(monkeypatch):
    actor = NS(id=uuid4())
    recipient = uuid4()
    facility = uuid4()
    case = NS(version=1, assigned_to=actor.id, status='contacting', facility_id=facility)
    target = NS(enabled=True, on_duty=True, facility_ids=[str(facility)])
    db = NS(get=AsyncMock(side_effect=[target, NS(status='active', role='staff')]))
    monkeypatch.setattr(svc, 'event', lambda *args, **kwargs: None)
    await svc.action(db, case, actor, NS(on_duty=True), CaseAction(version=1, action='handover', assigned_to=recipient, note='Shift summary'))
    assert case.assigned_to == recipient
    assert case.version == 2


@pytest.mark.asyncio
async def test_source_sync_skips_when_another_worker_holds_lock():
    db = NS(execute=AsyncMock(return_value=NS(scalar_one=lambda: False)))
    await svc.sync_sources(db)
    assert db.execute.await_count == 1
