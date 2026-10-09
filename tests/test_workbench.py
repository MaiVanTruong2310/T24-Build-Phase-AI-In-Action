"""Policy tests run offline; integration tests use an explicitly supplied DB."""

import asyncio
import os
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.db.base import Base
from src.models.booking import Booking
from src.models.booking_hold import BookingHold
from src.models.doctor import Doctor, DoctorFacility, DoctorSpecialty
from src.models.facility import Facility
from src.models.notification import Notification
from src.models.schedule import DoctorSchedule
from src.models.service import Service
from src.models.specialty import Specialty
from src.models.user import User
from src.models.workbench import (
    CoordinationCase as Case,
)
from src.models.workbench import (
    CoordinationDeposit as Deposit,
)
from src.models.workbench import CoordinationPolicy as Policy
from src.models.workbench import (
    CoordinatorMember as Member,
)
from src.schemas.workbench import CaseAction, DepositInput, PlanInput, VerifyInput
from src.services import workbench as svc
from src.services.coordinator_chat import after_turn, before_turn, validate_guidance


def test_stale_version_and_unassigned_actor_are_rejected():
    case = SimpleNamespace(version=3, assigned_to=uuid4())
    with pytest.raises(HTTPException) as err:
        svc.require_version(case, 2)
    assert err.value.status_code == 409
    with pytest.raises(HTTPException):
        svc.assert_owner(case, SimpleNamespace(id=uuid4()))


def test_guest_identity_is_not_derived_from_session_id():
    assert svc.owner_key(None, "a" * 64) != svc.owner_key(None, "b" * 64)
    assert "a" * 64 not in svc.owner_key(None, "a" * 64)


@pytest.mark.parametrize(
    "body", ["Bạn bị bệnh tiểu đường.", "Bác chắc chắn mắc ung thư.", "Uống paracetamol 500 mg mỗi lần."]
)
def test_explicit_diagnosis_and_dosage_blocked(body):
    with pytest.raises(HTTPException):
        validate_guidance(body)


def test_navigation_guidance_allowed():
    validate_guidance("Bạn nên khám chuyên khoa Nội tổng quát. Bác sĩ tại buổi khám sẽ đánh giá nguyên nhân.")


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def isolated_db():
    url = os.getenv("WORKBENCH_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set WORKBENCH_TEST_DATABASE_URL to run isolated PostgreSQL integration tests.")
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    schema = "workbench_test_" + uuid4().hex
    engine = create_async_engine(url, pool_size=3, max_overflow=0, connect_args={"connect_timeout": 10})
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA {schema}"))
            conn = await conn.execution_options(schema_translate_map={None: schema})
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(
            engine.execution_options(schema_translate_map={None: schema}), expire_on_commit=False
        )
        yield factory
    finally:
        async with engine.begin() as conn:
            # Only this random test schema is dropped, never public/application data.
            assert schema.startswith("workbench_test_") and len(schema) == 47
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        await engine.dispose()


async def seed(factory):
    async with factory() as db, db.begin():
        actor = User(email=uuid4().hex + "@example.test", full_name="Test coordinator", status="active", role="staff")
        other = User(email=uuid4().hex + "@example.test", full_name="Other coordinator", status="active", role="staff")
        patient = User(full_name="Test patient", status="active", role="patient")
        doctor = Doctor(code=uuid4().hex, full_name="Test doctor")
        facility = Facility(code=uuid4().hex, name="Test facility")
        service = Service(code=uuid4().hex, name="Test service", booking_mode="doctor_visit")
        specialty = Specialty(code=uuid4().hex, name="Test specialty")
        db.add_all([actor, other, patient, doctor, facility, service, specialty])
        await db.flush()
        member = Member(
            user_id=actor.id,
            is_admin=True,
            on_duty=True,
            enabled=True,
            facility_ids=[],
            clinical_qualification="Test physician",
        )
        other_member = Member(
            user_id=other.id, on_duty=True, enabled=True, facility_ids=[], clinical_qualification="Test physician"
        )
        db.add_all(
            [
                member,
                other_member,
                DoctorSpecialty(doctor_id=doctor.id, specialty_id=specialty.id),
                DoctorFacility(doctor_id=doctor.id, facility_id=facility.id),
            ]
        )
        if not await db.get(Policy, 1):
            db.add(
                Policy(
                    id=1,
                    hold_minutes=30,
                    response_minutes=30,
                    emergency_response_minutes=2,
                    payment_instructions="Test account instructions",
                    refund_policy="Test cancellation terms",
                )
            )
        schedules = [
            DoctorSchedule(
                doctor_id=doctor.id,
                facility_id=facility.id,
                starts_at=svc.now() + timedelta(days=1, hours=i),
                ends_at=svc.now() + timedelta(days=1, hours=i, minutes=30),
                capacity=1,
                status="available",
            )
            for i in (0, 1)
        ]
        db.add_all(schedules)
        await db.flush()
        case = Case(
            source="chat",
            source_id=uuid4().hex,
            owner_key="user:" + str(patient.id),
            session_id=uuid4().hex,
            patient_id=patient.id,
            patient={"name": "Test patient", "phone": "0900000000"},
            assigned_to=actor.id,
            status="contacting",
            ai_snapshot={"max_booking_days": 3},
            plan={},
        )
        db.add(case)
        await db.flush()
        return SimpleNamespace(
            actor=actor,
            other=other,
            member=member,
            other_member=other_member,
            patient=patient,
            case_id=case.id,
            specialty=specialty,
            service=service,
            schedules=schedules,
        )


@pytest.mark.asyncio(loop_scope="module")
async def test_deposit_booking_reschedule_cancel_refund(isolated_db):
    s = await seed(isolated_db)
    async with isolated_db() as db, db.begin():
        case = await svc.locked_case(db, s.case_id, s.member)
        with pytest.raises(HTTPException):
            await svc.confirm(db, case, s.actor, s.member, case.version)
        await svc.set_plan(
            db,
            case,
            s.actor,
            s.member,
            PlanInput(
                version=case.version,
                specialty_id=s.specialty.id,
                service_id=s.service.id,
                schedule_id=s.schedules[0].id,
                reason="Verified navigation",
                patient_agreed=True,
            ),
        )
        await svc.request_deposit(db, case, s.actor, s.member, DepositInput(version=case.version, amount=100000))
        await svc.verify_deposit(
            db,
            case,
            s.actor,
            VerifyInput(
                version=case.version, reference="test-payment-" + uuid4().hex, evidence="Verified test payment record"
            ),
        )
        await svc.confirm(db, case, s.actor, s.member, case.version)
        booking_id = case.booking_id
        assert case.status == "confirmed"
    async with isolated_db() as db, db.begin():
        case = await svc.locked_case(db, s.case_id, s.member)
        await svc.set_plan(
            db,
            case,
            s.actor,
            s.member,
            PlanInput(
                version=case.version,
                specialty_id=s.specialty.id,
                service_id=s.service.id,
                schedule_id=s.schedules[1].id,
                reason="Patient requested new time",
                patient_agreed=True,
            ),
        )
        await svc.request_deposit(db, case, s.actor, s.member, DepositInput(version=case.version, amount=100000))
        assert case.status == "deposit_verified"
        await svc.confirm(db, case, s.actor, s.member, case.version)
        assert case.booking_id == booking_id
        await svc.action(
            db, case, s.actor, s.member, CaseAction(version=case.version, action="cancel", note="Patient cancellation")
        )
        await svc.action(
            db,
            case,
            s.actor,
            s.member,
            CaseAction(
                version=case.version,
                action="refund_confirm",
                note="Actual refund verified",
                reference="test-refund-" + uuid4().hex,
            ),
        )
    async with isolated_db() as db:
        booking = await db.get(Booking, booking_id)
        deposits = (await db.execute(select(Deposit).where(Deposit.case_id == s.case_id))).scalars().all()
        assert booking.status == "cancelled" and deposits[0].status == "refunded"
        assert len(deposits) == 1
        assert (
            len((await db.execute(select(Notification).where(Notification.user_id == s.patient.id))).scalars().all())
            == 6
        )


@pytest.mark.asyncio(loop_scope="module")
async def test_concurrent_claim_and_scope(isolated_db):
    s = await seed(isolated_db)
    async with isolated_db() as db, db.begin():
        case = await db.get(Case, s.case_id)
        case.assigned_to = None
        version = case.version

    async def claim(actor, member):
        try:
            async with isolated_db() as db, db.begin():
                case = await svc.locked_case(db, s.case_id, member)
                await svc.action(db, case, actor, member, CaseAction(version=version, action="claim"))
            return True
        except HTTPException as exc:
            assert exc.status_code == 409
            return False

    assert sum(await asyncio.gather(claim(s.actor, s.member), claim(s.other, s.other_member))) == 1
    async with isolated_db() as db, db.begin():
        case = await db.get(Case, s.case_id)
        case.facility_id = s.schedules[0].facility_id
    async with isolated_db() as db, db.begin():
        with pytest.raises(HTTPException) as err:
            await svc.locked_case(db, s.case_id, SimpleNamespace(facility_ids=[str(uuid4())]))
        assert err.value.status_code == 404


@pytest.mark.asyncio(loop_scope="module")
async def test_message_client_id_replays_same_payload_and_rejects_reuse(isolated_db):
    s = await seed(isolated_db)
    client_id = uuid4()

    async def submit_message():
        async with isolated_db() as db, db.begin():
            case = await db.get(Case, s.case_id)
            message = await svc.add_message(db, case, client_id, "coordinator", "Hướng dẫn", s.actor)
            return message.id, message._created_by_request

    first, replay = await asyncio.gather(submit_message(), submit_message())
    assert first[0] == replay[0]
    assert sum([first[1], replay[1]]) == 1

    async with isolated_db() as db, db.begin():
        case = await db.get(Case, s.case_id)
        replay = await svc.add_message(db, case, client_id, "coordinator", "Hướng dẫn", s.actor)
        assert replay.id == first[0]
        assert replay._created_by_request is False

    async with isolated_db() as db, db.begin():
        case = await db.get(Case, s.case_id)
        with pytest.raises(HTTPException) as err:
            await svc.add_message(db, case, client_id, "coordinator", "Nội dung khác", s.actor)
        assert err.value.status_code == 409

    async with isolated_db() as db:
        with pytest.raises(HTTPException):
            async with db.begin():
                case = await db.get(Case, s.case_id)
                original_status = case.status
                case.status = "completed"
                await svc.add_message(db, case, client_id, "coordinator", "Nội dung khác", s.actor)
    async with isolated_db() as db, db.begin():
        case = await db.get(Case, s.case_id)
        assert case.status == original_status


@pytest.mark.asyncio(loop_scope="module")
async def test_human_chat_guest_isolation_and_emergency(isolated_db):
    s = await seed(isolated_db)
    from src.medical_assistant.domain.schemas import ChatRequest

    request = ChatRequest(message="Tôi cần tư vấn khám tổng quát", session_id="test-" + uuid4().hex)
    token = "a" * 64
    async with isolated_db() as db:
        cid, control, emergency, _ = await before_turn(db, request, None, token)
    async with isolated_db() as db, db.begin():
        case = await db.get(Case, cid)
        case.assigned_to = s.actor.id
        await svc.action(db, case, s.actor, s.member, CaseAction(version=case.version, action="takeover"))
        await svc.add_message(db, case, uuid4(), "coordinator", "Bạn nên khám Nội tổng quát.", s.actor)
    async with isolated_db() as db:
        result = await after_turn(db, cid, request, {"response": "AI draft"}, {"is_emergency": False})
        assert result["workflow_status"] == "HUMAN_TAKEOVER"
    urgent = ChatRequest(message="Tôi đau ngực dữ dội, khó thở, vã mồ hôi lạnh", session_id=request.session_id)
    async with isolated_db() as db:
        cid2, control, emergency, _ = await before_turn(db, urgent, None, token)
        assert cid == cid2 and emergency.is_emergency
    async with isolated_db() as db, db.begin():
        case = await db.get(Case, cid)
        assert case.priority == 0
        assert case.owner_key != svc.owner_key(None, "b" * 64)
        with pytest.raises(HTTPException):
            await svc.set_plan(
                db,
                case,
                s.actor,
                s.member,
                PlanInput(
                    version=case.version,
                    specialty_id=s.specialty.id,
                    service_id=s.service.id,
                    schedule_id=s.schedules[0].id,
                    reason="No routine booking",
                    patient_agreed=True,
                ),
            )


@pytest.mark.asyncio(loop_scope="module")
async def test_capacity_and_late_deposit(isolated_db):
    s = await seed(isolated_db)
    async with isolated_db() as db, db.begin():
        first = await db.get(Case, s.case_id)
        second = Case(
            source="chat",
            source_id=uuid4().hex,
            patient_id=s.patient.id,
            patient={},
            assigned_to=s.other.id,
            status="contacting",
            ai_snapshot={},
            plan={},
        )
        db.add(second)
        await db.flush()
        for case, actor, member in [(first, s.actor, s.member), (second, s.other, s.other_member)]:
            await svc.set_plan(
                db,
                case,
                actor,
                member,
                PlanInput(
                    version=case.version,
                    specialty_id=s.specialty.id,
                    service_id=s.service.id,
                    schedule_id=s.schedules[0].id,
                    reason="Verified patient agreement",
                    patient_agreed=True,
                ),
            )
        cases = [(first.id, first.version, s.actor, s.member), (second.id, second.version, s.other, s.other_member)]

    async def reserve(cid, version, actor, member):
        try:
            async with isolated_db() as db, db.begin():
                case = await svc.locked_case(db, cid, member)
                await svc.request_deposit(db, case, actor, member, DepositInput(version=version, amount=100000))
            return cid
        except HTTPException as exc:
            assert exc.status_code == 409
            return None

    results = await asyncio.gather(*(reserve(*args) for args in cases))
    assert len([x for x in results if x]) == 1
    winner = next(x for x in results if x)
    actor, member = next((a, m) for cid, _, a, m in cases if cid == winner)
    async with isolated_db() as db, db.begin():
        deposit = (await db.execute(select(Deposit).where(Deposit.case_id == winner))).scalar_one()
        deposit.expires_at = svc.now() - timedelta(minutes=1)
        case = await db.get(Case, winner)
        hold = await db.get(BookingHold, __import__("uuid").UUID(case.plan["hold_id"]))
        hold.expires_at = deposit.expires_at
        await db.flush()
        await svc.expire_deposits(db)
        assert case.status == "deposit_expired"
        await svc.verify_deposit(
            db,
            case,
            actor,
            VerifyInput(version=case.version, reference="late-" + uuid4().hex, evidence="Late transaction verified"),
        )
        assert case.status == "deposit_late"
        with pytest.raises(HTTPException):
            await svc.confirm(db, case, actor, member, case.version)


@pytest.mark.asyncio(loop_scope="module")
async def test_workbench_api_and_guest_receipts(isolated_db):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from src.api.dependencies import get_current_user
    from src.api.endpoints.workbench import patient_router, router
    from src.db.dependencies import get_db_session

    s = await seed(isolated_db)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.include_router(patient_router, prefix="/api/v1")

    async def db_dependency():
        async with isolated_db() as db:
            yield db

    current = [s.actor]

    async def user_dependency():
        return current[0]

    app.dependency_overrides[get_db_session] = db_dependency
    app.dependency_overrides[get_current_user] = user_dependency

    @app.middleware("http")
    async def capability(request, call_next):
        request.state.coordination_guest = request.cookies.get("coordination_guest", "a" * 64)
        return await call_next(request)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/v1/staff/workbench/me")).status_code == 200
        response = await client.get("/api/v1/staff/workbench/cases?conversations=true")
        assert response.status_code == 200 and response.json()["data"]["total"] > 0
        current[0] = s.patient
        assert (await client.get("/api/v1/staff/workbench/me")).status_code == 403
        current[0] = s.actor
        async with isolated_db() as db, db.begin():
            case = Case(
                source="chat",
                source_id=uuid4().hex,
                owner_key=svc.owner_key(None, "a" * 64),
                session_id=uuid4().hex,
                patient={"name": "Guest test"},
                status="new",
                ai_snapshot={},
                plan={},
            )
            db.add(case)
            await db.flush()
            sid = case.session_id
        receipt = await client.get("/api/v1/coordination/live/" + sid)
        assert receipt.json()["data"]["case"]["id"] == str(case.id)
        client.cookies.set("coordination_guest", "b" * 64)
        hidden = await client.get("/api/v1/coordination/live/" + sid)
        assert hidden.json()["data"]["case"] is None
        assert (
            await client.post("/api/v1/coordination/live/" + sid + "/messages", json={"body": "Hello"})
        ).status_code == 404


@pytest.mark.asyncio(loop_scope="module")
async def test_all_sources_import_once_and_source_cancel(isolated_db):
    from src.models.package_request import PackageRequest

    s = await seed(isolated_db)
    async with isolated_db() as db, db.begin():
        request = PackageRequest(
            patient_id=s.patient.id,
            service_id=s.service.id,
            facility_id=s.schedules[0].facility_id,
            preferred_date=svc.now().date(),
            patient_name="Test package patient",
        )
        db.add(request)
        await db.flush()
        await svc.sync_sources(db)
        await svc.sync_sources(db)
        rows = (
            (await db.execute(select(Case).where(Case.source == "package", Case.source_id == str(request.id))))
            .scalars()
            .all()
        )
        assert len(rows) == 1 and rows[0].owner_key == "user:" + str(s.patient.id)
        request.status = "cancelled"
        await db.flush()
        await svc.sync_sources(db)
        assert rows[0].status == "cancelled"


@pytest.mark.asyncio(loop_scope="module")
async def test_shift_handover_and_browser_grants(isolated_db):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from src.api.dependencies import get_current_user
    from src.api.endpoints.workbench import router
    from src.db.dependencies import get_db_session

    s = await seed(isolated_db)
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def db_dependency():
        async with isolated_db() as db:
            yield db

    async def user_dependency():
        return s.actor

    app.dependency_overrides[get_db_session] = db_dependency
    app.dependency_overrides[get_current_user] = user_dependency
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/api/v1/staff/workbench/duty/end")).status_code == 409
        response = await client.post(
            "/api/v1/staff/workbench/duty/handover",
            json={"assigned_to": str(s.other.id), "note": "Verified shift summary"},
        )
        assert response.status_code == 200 and response.json()["data"]["cases_transferred"] == 1
    async with isolated_db() as db:
        assert (await db.get(Case, s.case_id)).assigned_to == s.other.id
        assert (await db.get(Member, s.actor.id)).on_duty is False
        schema = str(db.bind.sync_engine.get_execution_options()["schema_translate_map"][None])
        from src.models.workbench import WORKBENCH_TABLES

        for table in WORKBENCH_TABLES:
            grants = (
                await db.execute(
                    text(
                        "SELECT has_table_privilege('anon',:table,'SELECT'), has_table_privilege('authenticated',:table,'SELECT')"
                    ),
                    {"table": schema + "." + table.name},
                )
            ).one()
            assert tuple(grants) == (False, False)


def test_guest_graph_threads_are_capability_bound():
    from src.services.chat_history import graph_thread

    assert graph_thread("same-session", None, "a" * 64) != graph_thread("same-session", None, "b" * 64)
