from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from src.api.endpoints.workbench import cases, dashboard
from src.repositories.booking import BookingRepository
from src.repositories.doctor import DoctorRepositoryMixin
from src.repositories.service import MedicalServiceRepositoryMixin
from src.repositories.user import UserRepository


def statement_sql(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


def rows_result(rows=()):
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(rows)
    return result


@pytest.mark.asyncio
async def test_staff_booking_page_orders_updated_before_pagination():
    session = MagicMock()
    session.scalar = AsyncMock(return_value=2)
    session.execute = AsyncMock(side_effect=[MagicMock(all=MagicMock(return_value=[])), rows_result()])

    await BookingRepository(session).list_for_staff(None, None, 0, 20)

    sql = statement_sql(session.execute.await_args_list[-1].args[0])
    assert "ORDER BY bookings.updated_at DESC, bookings.id DESC" in sql


@pytest.mark.asyncio
async def test_staff_patient_page_orders_updated_before_pagination():
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[MagicMock(scalar_one=MagicMock(return_value=1)), rows_result()])

    await UserRepository(session).search_patients(
        query=None, status=None, gender=None, created_from=None, created_to=None, offset=0, limit=20
    )

    sql = statement_sql(session.execute.await_args_list[-1].args[0])
    assert "ORDER BY users.updated_at DESC, users.id" in sql


@pytest.mark.asyncio
async def test_staff_doctor_and_service_lists_use_update_order():
    session = MagicMock()
    session.execute = AsyncMock(return_value=rows_result())
    doctor_repo = DoctorRepositoryMixin()
    doctor_repo.session = session
    service_repo = MedicalServiceRepositoryMixin()
    service_repo.session = session

    await doctor_repo.list_doctors(
        public_only=False,
        specialty_id=None,
        facility_id=None,
        service_id=None,
        name=None,
        booking_enabled=None,
        offset=0,
        limit=20,
    )
    doctor_sql = statement_sql(session.execute.await_args_list[-1].args[0])
    await service_repo.list_services(public_only=False, offset=0, limit=20)
    service_sql = statement_sql(session.execute.await_args_list[-1].args[0])
    await doctor_repo.list_doctors(
        public_only=True,
        specialty_id=None,
        facility_id=None,
        service_id=None,
        name=None,
        booking_enabled=None,
        offset=0,
        limit=20,
    )
    public_doctor_sql = statement_sql(session.execute.await_args_list[-1].args[0])
    await service_repo.list_services(public_only=True, offset=0, limit=20)
    public_service_sql = statement_sql(session.execute.await_args_list[-1].args[0])

    assert "ORDER BY doctors.updated_at DESC, doctors.id" in doctor_sql
    assert "ORDER BY services.updated_at DESC, services.id" in service_sql
    assert "ORDER BY doctors.full_name, doctors.id" in public_doctor_sql
    assert "ORDER BY services.name, services.id" in public_service_sql


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("emergency_only", "conversations", "expected_order"),
    [
        (
            False,
            False,
            "ORDER BY coordination_cases.created_at DESC, coordination_cases.id DESC",
        ),
        (
            True,
            False,
            "ORDER BY coordination_cases.priority ASC, CASE WHEN (coordination_cases.assigned_to IS NULL) THEN",
        ),
        (
            False,
            True,
            "ORDER BY coordination_cases.priority ASC, coordination_cases.updated_at DESC, coordination_cases.id DESC",
        ),
    ],
)
async def test_staff_case_lists_use_mode_specific_order(emergency_only, conversations, expected_order):
    class DB:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            result = MagicMock()
            result.scalar_one.return_value = 0
            result.scalars.return_value.all.return_value = []
            return result

    db = DB()
    identity = (SimpleNamespace(id=None), SimpleNamespace(facility_ids=[]))
    await cases(
        status=None,
        priority=None,
        emergency_only=emergency_only,
        mine=False,
        conversations=conversations,
        q="",
        offset=0,
        limit=50,
        identity=identity,
        db=db,
    )

    assert expected_order in statement_sql(db.statements[-1])


@pytest.mark.asyncio
async def test_staff_dashboard_followups_keep_due_time_first():
    class DB:
        def __init__(self):
            self.statements = []

        def begin(self):
            class Transaction:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, *_):
                    return False

            return Transaction()

        async def execute(self, statement):
            self.statements.append(statement)
            result = MagicMock()
            result.all.return_value = []
            result.scalar_one.return_value = 0
            result.scalars.return_value.all.return_value = []
            return result

    db = DB()
    identity = (SimpleNamespace(id=None), SimpleNamespace(facility_ids=[]))
    await dashboard(identity, db)

    sql = statement_sql(db.statements[2])
    assert (
        "ORDER BY coordination_cases.follow_up_at, coordination_cases.priority, coordination_cases.updated_at DESC"
        in sql
    )
