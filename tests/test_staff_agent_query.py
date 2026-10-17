"""Security checks for bounded staff-agent query plans and RO execution."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from src.repositories.staff_agent_query import build_staff_query
from src.schemas.staff_agent_query import StaffQueryPlan
from src.services import staff_agent_query as query_service_module
from src.services.staff_agent_query import StaffAgentQueryService


def _plan(**overrides):
    value = {
        "subject": "catalog",
        "select": ["doctor_name", "facility_name"],
        "filters": [{"field": "facility_name", "operator": "contains", "value": "ABC"}],
        "limit": 10,
    }
    value.update(overrides)
    return StaffQueryPlan.model_validate(value)


def test_query_plan_rejects_extra_keys_and_non_strict_scalars():
    with pytest.raises(ValidationError):
        StaffQueryPlan.model_validate({**_plan().model_dump(), "table": "users"})
    with pytest.raises(ValidationError):
        StaffQueryPlan.model_validate({**_plan().model_dump(), "limit": "10"})


def test_query_compiler_binds_values_and_injects_facility_scope():
    staff_id, allowed_facility, other_facility = uuid4(), uuid4(), uuid4()
    hostile_value = "ABC%' OR 1=1 --"
    plan = _plan(
        filters=[{"field": "facility_name", "operator": "contains", "value": hostile_value}],
    )
    statement = build_staff_query(plan, [allowed_facility], staff_id=staff_id)
    compiled = statement.compile(dialect=postgresql.dialect())

    assert "FROM v_staff_agent_catalog" in str(compiled)
    assert hostile_value not in str(compiled)
    assert f"%{hostile_value.replace('%', chr(92) + '%')}%" in compiled.params.values()
    facility_values = next(value for value in compiled.params.values() if isinstance(value, list))
    assert allowed_facility in facility_values
    assert str(other_facility) not in [str(value) for value in compiled.params.values()]


def test_query_compiler_requires_bounded_future_availability_window():
    plan = _plan(
        subject="availability",
        select=["doctor_name", "starts_at", "remaining_capacity"],
        filters=[{"field": "doctor_name", "operator": "contains", "value": "An"}],
    )
    with pytest.raises(ValueError, match="bounded starts_at window"):
        build_staff_query(plan, [], staff_id=uuid4())

    too_wide = StaffQueryPlan.model_validate(
        {
            **plan.model_dump(),
            "filters": [
                {"field": "doctor_name", "operator": "contains", "value": "An"},
                {
                    "field": "starts_at",
                    "operator": "between",
                    "value": [
                        (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                        (datetime.now(UTC) + timedelta(days=40)).isoformat(),
                    ],
                },
            ],
        }
    )
    with pytest.raises(ValueError, match="at most 31 days"):
        build_staff_query(too_wide, [], staff_id=uuid4())


def test_case_query_resolves_me_to_authenticated_staff_id():
    staff_id = uuid4()
    plan = _plan(
        subject="case_operations",
        select=["case_id", "case_status", "assigned_to", "facility_id"],
        filters=[{"field": "assigned_to", "operator": "equals", "value": "me"}],
    )
    compiled = build_staff_query(plan, [], staff_id=staff_id).compile(dialect=postgresql.dialect())
    assert str(staff_id) in [str(value) for value in compiled.params.values()]
    assert "v_staff_agent_case_operations" in str(compiled)


class _FakeResult:
    def __init__(self, row=None):
        self.row = row

    def mappings(self):
        return self

    def one_or_none(self):
        return self.row


class _FakeSession:
    bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    def __init__(self, privileges):
        self.privileges = privileges
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def begin(self):
        return self

    async def execute(self, statement):
        self.calls.append(str(statement))
        if "WITH RECURSIVE memberships" in str(statement):
            return _FakeResult(self.privileges)
        return _FakeResult()


@pytest.mark.asyncio
async def test_query_sets_read_only_before_attestation_and_query(monkeypatch):
    staff_id = uuid4()
    privileges = {
        "principal_is_unprivileged": True,
        "database_is_read_only": True,
        "schemas_are_read_only": True,
        "tables_are_read_only": True,
        "sequences_are_read_only": True,
        "only_safe_views_readable": True,
        "no_sequence_access": True,
        "safe_views_are_readable": True,
    }
    session = _FakeSession(privileges)
    calls = []

    class Factory:
        def __call__(self):
            return session

    async def execute(_session, _plan, _facility_ids, _staff_id):
        calls.append("query")
        return [{"doctor_name": "Bác sĩ A"}]

    monkeypatch.setattr(query_service_module, "execute_staff_query", execute)
    result = await StaffAgentQueryService(Factory()).query(staff_id, [], _plan())

    assert result["items"] == [{"doctor_name": "Bác sĩ A"}]
    assert session.calls[0] == "SET TRANSACTION READ ONLY"
    assert "statement_timeout" in session.calls[1]
    assert "WITH RECURSIVE memberships" in session.calls[2]
    assert calls == ["query"]


@pytest.mark.asyncio
async def test_query_rejects_write_capable_database_principal(monkeypatch):
    privileges = {
        "principal_is_unprivileged": True,
        "database_is_read_only": True,
        "schemas_are_read_only": True,
        "tables_are_read_only": False,
        "sequences_are_read_only": True,
        "only_safe_views_readable": True,
        "no_sequence_access": True,
        "safe_views_are_readable": True,
    }
    session = _FakeSession(privileges)
    queried = False

    class Factory:
        def __call__(self):
            return session

    async def execute(*_args):
        nonlocal queried
        queried = True
        return []

    monkeypatch.setattr(query_service_module, "execute_staff_query", execute)
    result = await StaffAgentQueryService(Factory()).query(uuid4(), [], _plan())

    assert result["available"] is False
    assert queried is False
    assert len(session.calls) == 3


@pytest.mark.asyncio
async def test_missing_readonly_configuration_does_not_fall_back_to_default_database(monkeypatch):
    monkeypatch.setattr(query_service_module, "get_staff_agent_readonly_session_factory", lambda: None)
    monkeypatch.setattr(
        query_service_module,
        "get_settings",
        lambda: SimpleNamespace(staff_agent_readonly_database_url="", database_url=""),
    )
    result = await StaffAgentQueryService().query(uuid4(), [], _plan())
    assert result["available"] is False


def test_readonly_login_must_be_distinct_and_point_to_the_application_database():
    app = "postgresql://app_user:secret@db.example:5432/clinic"
    good = "postgresql://staff_agent_readonly:secret@db.example:5432/clinic"
    same_user = "postgresql://app_user:secret@db.example:5432/clinic"
    different_database = "postgresql://staff_agent_readonly:secret@db.example:5432/other"

    assert query_service_module._separate_readonly_login(good, app)
    assert not query_service_module._separate_readonly_login(same_user, app)
    assert not query_service_module._separate_readonly_login(different_database, app)
