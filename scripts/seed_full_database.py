"""Seed full development database with specialties, facilities, services, doctors, schedules, and test accounts."""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from uuid import UUID

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.security import hash_password
from src.db.session import get_session_factory, initialize_database
from src.models.doctor import Doctor, DoctorFacility, DoctorService, DoctorSpecialty
from src.models.facility import Facility
from src.models.schedule import DoctorSchedule
from src.models.service import Service
from src.models.specialty import Specialty
from src.models.user import User

SPECIALTIES = [
    {
        "id": UUID("10000000-0000-4000-8000-000000000001"),
        "code": "CARDIOLOGY",
        "name": "Trung tâm Tim mạch",
        "description": "Khám, chẩn đoán và can thiệp điều trị bệnh lý tim mạch, mạch vành, rối loạn nhịp tim.",
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000002"),
        "code": "PEDIATRICS",
        "name": "Nhi khoa",
        "description": "Chăm sóc sức khỏe toàn diện, tiêm chủng và điều trị bệnh lý ở trẻ sơ sinh và trẻ nhỏ.",
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000003"),
        "code": "OBSTETRICS_GYNECOLOGY",
        "name": "Sản phụ khoa",
        "description": "Chăm sóc thai kỳ, quản lý thai nghén nguy cơ cao và điều trị bệnh lý phụ khoa.",
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000004"),
        "code": "INTERNAL_MEDICINE",
        "name": "Nội khoa tổng quát",
        "description": "Khám sàng lọc sức khỏe tổng quát, quản lý các bệnh lý chuyển hóa và mạn tính.",
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000005"),
        "code": "SURGERY",
        "name": "Ngoại khoa",
        "description": "Phẫu thuật nội soi, can thiệp ngoại tiêu hóa, lồng ngực và ngoại chấn thương.",
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000006"),
        "code": "DERMATOLOGY",
        "name": "Da liễu - Thẩm mỹ da",
        "description": "Điều trị các bệnh lý da, tóc, móng và chăm sóc phục hồi da chuyên sâu.",
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000007"),
        "code": "ORTHOPEDICS",
        "name": "Chấn thương chỉnh hình - Y học thể thao",
        "description": "Phục hồi chức năng, điều trị tổn thương xương khớp và chấn thương vận động.",
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000008"),
        "code": "NEUROLOGY",
        "name": "Thần kinh",
        "description": "Khám và điều trị đau đầu, đột quỵ, động kinh và các rối loạn thần kinh ngoại biên.",
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000009"),
        "code": "ONCOLOGY",
        "name": "Trung tâm Ung bướu",
        "description": "Tầm soát ung thư sớm, hội chẩn đa chuyên khoa và phác đồ hóa xạ trị chuẩn quốc tế.",
    },
    {
        "id": UUID("10000000-0000-4000-8000-000000000010"),
        "code": "ENT",
        "name": "Tai - Mũi - Họng",
        "description": "Khám nội soi và phẫu thuật điều trị các bệnh lý tai mũi họng người lớn và trẻ em.",
    },
]

FACILITIES = [
    {
        "id": UUID("40000000-0000-4000-8000-000000000001"),
        "code": "VMEC-TIMESCITY",
        "name": "Bệnh viện ĐKQT Vinmec Times City",
        "description": "Bệnh viện đa khoa quốc tế đạt chuẩn JCI tại Hà Nội.",
        "address": "458 Minh Khai, Phường Vĩnh Tuy, Quận Hai Bà Trưng, Hà Nội",
        "phone": "02439743556",
        "status": "active",
    },
    {
        "id": UUID("40000000-0000-4000-8000-000000000002"),
        "code": "VMEC-CENTRALPARK",
        "name": "Bệnh viện ĐKQT Vinmec Central Park",
        "description": "Bệnh viện đa khoa quốc tế đạt chuẩn JCI tại TP. Hồ Chí Minh.",
        "address": "208 Nguyễn Hữu Cảnh, Phường 22, Quận Bình Thạnh, TP. Hồ Chí Minh",
        "phone": "02836221166",
        "status": "active",
    },
]

SERVICES = [
    {
        "id": UUID("50000000-0000-4000-8000-000000000001"),
        "code": "CONSULT-GEN",
        "name": "Khám Nội tổng quát",
        "description": "Khám sàng lọc sức khỏe ban đầu, đo chỉ số sinh tồn và tư vấn bệnh học.",
        "duration_minutes": 30,
        "price": 300000.0,
        "original_price": 400000.0,
        "category": "consultation",
        "booking_mode": "doctor_visit",
        "status": "active",
    },
    {
        "id": UUID("50000000-0000-4000-8000-000000000002"),
        "code": "CONSULT-SPEC",
        "name": "Khám Chuyên khoa",
        "description": "Khám chuyên sâu theo chuyên khoa với bác sĩ chuyên khoa I, II.",
        "duration_minutes": 30,
        "price": 500000.0,
        "original_price": 600000.0,
        "category": "consultation",
        "booking_mode": "doctor_visit",
        "status": "active",
    },
    {
        "id": UUID("50000000-0000-4000-8000-000000000003"),
        "code": "CONSULT-VIP",
        "name": "Khám Chuyên gia VIP",
        "description": "Khám ưu tiên cùng Giáo sư, Phó Giáo sư, Chuyên gia đầu ngành.",
        "duration_minutes": 45,
        "price": 1000000.0,
        "original_price": 1200000.0,
        "category": "consultation",
        "booking_mode": "doctor_visit",
        "status": "active",
    },
]

DOCTORS = [
    {
        "id": UUID("20000000-0000-4000-8000-000000000001"),
        "code": "DOC-CARD-001",
        "full_name": "Nguyễn Minh Anh",
        "license_number": "CCHN-CARD-001",
        "email": "minh.anh.cardiology@medicare.local",
        "phone": "0901000001",
        "bio": "Khám và điều trị bệnh lý tim mạch, tăng huyết áp và rối loạn nhịp.",
        "gender": "female",
        "title": "Bác sĩ chuyên khoa II",
        "date_of_birth": date(1982, 4, 12),
        "specialty_id": UUID("10000000-0000-4000-8000-000000000001"),
    },
    {
        "id": UUID("20000000-0000-4000-8000-000000000002"),
        "code": "DOC-PEDI-001",
        "full_name": "Trần Hoàng Nam",
        "license_number": "CCHN-PEDI-001",
        "email": "hoang.nam.pediatrics@medicare.local",
        "phone": "0901000002",
        "bio": "Theo dõi tăng trưởng và điều trị các bệnh lý thường gặp ở trẻ em.",
        "gender": "male",
        "title": "Bác sĩ chuyên khoa I",
        "date_of_birth": date(1985, 8, 23),
        "specialty_id": UUID("10000000-0000-4000-8000-000000000002"),
    },
    {
        "id": UUID("20000000-0000-4000-8000-000000000003"),
        "code": "DOC-OBGY-001",
        "full_name": "Lê Thu Hà",
        "license_number": "CCHN-OBGY-001",
        "email": "thu.ha.obgyn@medicare.local",
        "phone": "0901000003",
        "bio": "Khám sản khoa, phụ khoa và tư vấn chăm sóc sức khỏe sinh sản.",
        "gender": "female",
        "title": "Bác sĩ chuyên khoa II",
        "date_of_birth": date(1980, 11, 5),
        "specialty_id": UUID("10000000-0000-4000-8000-000000000003"),
    },
    {
        "id": UUID("20000000-0000-4000-8000-000000000004"),
        "code": "DOC-IM-001",
        "full_name": "Phạm Quốc Huy",
        "license_number": "CCHN-IM-001",
        "email": "quoc.huy.internal@medicare.local",
        "phone": "0901000004",
        "bio": "Khám sức khỏe tổng quát và quản lý bệnh lý nội khoa mạn tính.",
        "gender": "male",
        "title": "Bác sĩ chuyên khoa I",
        "date_of_birth": date(1983, 2, 17),
        "specialty_id": UUID("10000000-0000-4000-8000-000000000004"),
    },
    {
        "id": UUID("20000000-0000-4000-8000-000000000005"),
        "code": "DOC-SURG-001",
        "full_name": "Võ Thành Đạt",
        "license_number": "CCHN-SURG-001",
        "email": "thanh.dat.surgery@medicare.local",
        "phone": "0901000005",
        "bio": "Tư vấn và điều trị các bệnh lý cần can thiệp ngoại khoa.",
        "gender": "male",
        "title": "Bác sĩ chuyên khoa II",
        "date_of_birth": date(1979, 6, 30),
        "specialty_id": UUID("10000000-0000-4000-8000-000000000005"),
    },
    {
        "id": UUID("20000000-0000-4000-8000-000000000006"),
        "code": "DOC-DERM-001",
        "full_name": "Nguyễn Thùy Dương",
        "license_number": "CCHN-DERM-001",
        "email": "thuy.duong.dermatology@medicare.local",
        "phone": "0901000006",
        "bio": "Điều trị bệnh lý da, tóc, móng và chăm sóc da chuyên sâu.",
        "gender": "female",
        "title": "Bác sĩ chuyên khoa I",
        "date_of_birth": date(1987, 1, 21),
        "specialty_id": UUID("10000000-0000-4000-8000-000000000006"),
    },
    {
        "id": UUID("20000000-0000-4000-8000-000000000007"),
        "code": "DOC-ORTH-001",
        "full_name": "Đỗ Anh Tuấn",
        "license_number": "CCHN-ORTH-001",
        "email": "anh.tuan.orthopedics@medicare.local",
        "phone": "0901000007",
        "bio": "Điều trị bệnh lý xương khớp, cơ và chấn thương vận động.",
        "gender": "male",
        "title": "Bác sĩ chuyên khoa II",
        "date_of_birth": date(1981, 9, 14),
        "specialty_id": UUID("10000000-0000-4000-8000-000000000007"),
    },
    {
        "id": UUID("20000000-0000-4000-8000-000000000008"),
        "code": "DOC-NEUR-001",
        "full_name": "Bùi Minh Khoa",
        "license_number": "CCHN-NEUR-001",
        "email": "minh.khoa.neurology@medicare.local",
        "phone": "0901000008",
        "bio": "Khám và điều trị bệnh lý thần kinh, não bộ và cột sống.",
        "gender": "male",
        "title": "Bác sĩ chuyên khoa I",
        "date_of_birth": date(1984, 3, 9),
        "specialty_id": UUID("10000000-0000-4000-8000-000000000008"),
    },
    {
        "id": UUID("20000000-0000-4000-8000-000000000009"),
        "code": "DOC-ONCO-001",
        "full_name": "Hoàng Ngọc Lan",
        "license_number": "CCHN-ONCO-001",
        "email": "ngoc.lan.oncology@medicare.local",
        "phone": "0901000009",
        "bio": "Tầm soát, chẩn đoán và điều trị bệnh lý ung bướu.",
        "gender": "female",
        "title": "Bác sĩ chuyên khoa II",
        "date_of_birth": date(1978, 12, 1),
        "specialty_id": UUID("10000000-0000-4000-8000-000000000009"),
    },
    {
        "id": UUID("20000000-0000-4000-8000-000000000010"),
        "code": "DOC-ENT-001",
        "full_name": "Nguyễn Đức Long",
        "license_number": "CCHN-ENT-001",
        "email": "duc.long.ent@medicare.local",
        "phone": "0901000010",
        "bio": "Khám và điều trị bệnh lý tai, mũi, họng và vùng đầu cổ.",
        "gender": "male",
        "title": "Bác sĩ chuyên khoa I",
        "date_of_birth": date(1986, 7, 18),
        "specialty_id": UUID("10000000-0000-4000-8000-000000000010"),
    },
]

USERS = [
    {
        "id": UUID("00000000-0000-4000-8000-000000000001"),
        "email": "staff@vinmec.com",
        "phone": "0912345678",
        "password": "Password123@",
        "full_name": "Nhân viên Điều phối",
        "role": "staff",
        "status": "active",
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000002"),
        "email": "patient@vinmec.com",
        "phone": "0987654321",
        "password": "Password123@",
        "full_name": "Trần Văn An",
        "role": "patient",
        "status": "active",
    },
]


async def seed_data(session: AsyncSession) -> None:
    print("[1/6] Seeding specialties...")
    for item in SPECIALTIES:
        existing = await session.get(Specialty, item["id"])
        if not existing:
            session.add(Specialty(**item, status="active"))
        else:
            existing.name = item["name"]
            existing.description = item["description"]
            existing.code = item["code"]
    await session.flush()

    print("[2/6] Seeding facilities...")
    for item in FACILITIES:
        existing = await session.get(Facility, item["id"])
        if not existing:
            session.add(Facility(**item))
        else:
            existing.name = item["name"]
            existing.address = item["address"]
            existing.phone = item["phone"]
    await session.flush()

    print("[3/6] Seeding services...")
    for item in SERVICES:
        existing = await session.get(Service, item["id"])
        if not existing:
            session.add(Service(**item))
        else:
            existing.name = item["name"]
            existing.price = item["price"]
            existing.original_price = item["original_price"]
    await session.flush()

    print("[4/6] Seeding doctors & assignments...")
    facility_id = FACILITIES[0]["id"]
    service_id = SERVICES[1]["id"]  # Khám chuyên khoa

    for doc_data in DOCTORS:
        specialty_id = doc_data.pop("specialty_id")
        existing_doc = await session.get(Doctor, doc_data["id"])
        if not existing_doc:
            doctor = Doctor(**doc_data, status="active", review_status="approved", booking_enabled=True)
            session.add(doctor)
            await session.flush()

            # Assign specialty
            session.add(DoctorSpecialty(doctor_id=doctor.id, specialty_id=specialty_id, is_primary=True))
            # Assign facility
            session.add(DoctorFacility(doctor_id=doctor.id, facility_id=facility_id, department="Khu khám chuyên khoa", room="P.101"))
            # Assign service
            session.add(DoctorService(doctor_id=doctor.id, service_id=service_id, active=True))
        else:
            existing_doc.full_name = doc_data["full_name"]
            existing_doc.bio = doc_data["bio"]
    await session.flush()

    print("[5/6] Seeding test accounts (staff & patient)...")
    for u in USERS:
        pwd = u.pop("password")
        existing_user = await session.get(User, u["id"])
        if not existing_user:
            user = User(
                **u,
                password_hash=hash_password(pwd),
                verified_at=datetime.now(UTC),
            )
            session.add(user)
        else:
            existing_user.password_hash = hash_password(pwd)
            existing_user.role = u["role"]
            existing_user.status = u["status"]
            existing_user.verified_at = datetime.now(UTC)
    await session.flush()

    print("[6/6] Generating upcoming doctor appointment slots (7 days)...")
    now = datetime.now(UTC)
    start_date = now.date()

    # Create slots for first 5 doctors for the next 7 days
    slot_hours = [
        (time(8, 0), time(8, 30)),
        (time(8, 30), time(9, 0)),
        (time(9, 0), time(9, 30)),
        (time(9, 30), time(10, 0)),
        (time(10, 0), time(10, 30)),
        (time(14, 0), time(14, 30)),
        (time(14, 30), time(15, 0)),
        (time(15, 0), time(15, 30)),
        (time(15, 30), time(16, 0)),
    ]

    for doc_data in DOCTORS[:5]:
        doc_id = doc_data["id"]
        for day_offset in range(1, 8):
            target_date = start_date + timedelta(days=day_offset)
            for start_t, end_t in slot_hours:
                starts_at = datetime.combine(target_date, start_t, tzinfo=UTC)
                ends_at = datetime.combine(target_date, end_t, tzinfo=UTC)
                ext_id = f"SEED-{doc_data['code']}-{target_date.isoformat()}-{start_t.strftime('%H%M')}"

                # Check if exists
                stmt = select(DoctorSchedule).where(
                    DoctorSchedule.doctor_id == doc_id,
                    DoctorSchedule.external_schedule_id == ext_id,
                )
                res = await session.execute(stmt)
                if not res.scalar_one_or_none():
                    slot = DoctorSchedule(
                        doctor_id=doc_id,
                        facility_id=facility_id,
                        starts_at=starts_at,
                        ends_at=ends_at,
                        capacity=2,
                        status="available",
                        source_system="seed",
                        external_schedule_id=ext_id,
                    )
                    session.add(slot)

    await session.commit()
    print("All seed data completed successfully!")


async def main() -> None:
    settings = get_settings()
    print(f"Connecting to database: {settings.database_url}")
    await initialize_database()
    async with get_session_factory()() as session:
        await seed_data(session)


if __name__ == "__main__":
    asyncio.run(main())
