-- Seed doctors and their specialty assignments for VMEC-01.
--
-- Prerequisite: run the Alembic migrations through the current head first.
-- This script intentionally creates only doctor <-> specialty relations.
-- Facility/service assignments require real IDs from the target environment.

BEGIN;

-- Fail early if the supplied specialty catalog is not present or has changed.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM (
            VALUES
                ('10000000-0000-4000-8000-000000000001'::uuid, 'CARDIOLOGY'),
                ('10000000-0000-4000-8000-000000000002'::uuid, 'PEDIATRICS'),
                ('10000000-0000-4000-8000-000000000003'::uuid, 'OBSTETRICS_GYNECOLOGY'),
                ('10000000-0000-4000-8000-000000000004'::uuid, 'INTERNAL_MEDICINE'),
                ('10000000-0000-4000-8000-000000000005'::uuid, 'SURGERY'),
                ('10000000-0000-4000-8000-000000000006'::uuid, 'DERMATOLOGY'),
                ('10000000-0000-4000-8000-000000000007'::uuid, 'ORTHOPEDICS'),
                ('10000000-0000-4000-8000-000000000008'::uuid, 'NEUROLOGY'),
                ('10000000-0000-4000-8000-000000000009'::uuid, 'ONCOLOGY'),
                ('10000000-0000-4000-8000-000000000010'::uuid, 'ENT')
        ) AS expected(id, code)
        LEFT JOIN specialties s ON s.id = expected.id AND s.code = expected.code
        WHERE s.id IS NULL
    ) THEN
        RAISE EXCEPTION 'Expected specialty catalog is missing or does not match the supplied UUID/code pairs';
    END IF;
END
$$;

WITH seed_doctors (
    id,
    code,
    full_name,
    license_number,
    email,
    phone,
    bio,
    avatar_url,
    gender,
    title,
    date_of_birth,
    status,
    review_status,
    booking_enabled
) AS (
    VALUES
        (
            '20000000-0000-4000-8000-000000000001'::uuid,
            'DOC-CARD-001',
            'Nguyễn Minh Anh',
            'CCHN-CARD-001',
            'minh.anh.cardiology@medicare.local',
            '0901000001',
            'Khám và điều trị bệnh lý tim mạch, tăng huyết áp và rối loạn nhịp.',
            NULL,
            'female',
            'Bác sĩ chuyên khoa II',
            '1982-04-12'::date,
            'active',
            'approved',
            TRUE
        ),
        (
            '20000000-0000-4000-8000-000000000002'::uuid,
            'DOC-PEDI-001',
            'Trần Hoàng Nam',
            'CCHN-PEDI-001',
            'hoang.nam.pediatrics@medicare.local',
            '0901000002',
            'Theo dõi tăng trưởng và điều trị các bệnh lý thường gặp ở trẻ em.',
            NULL,
            'male',
            'Bác sĩ chuyên khoa I',
            '1985-08-23'::date,
            'active',
            'approved',
            TRUE
        ),
        (
            '20000000-0000-4000-8000-000000000003'::uuid,
            'DOC-OBGY-001',
            'Lê Thu Hà',
            'CCHN-OBGY-001',
            'thu.ha.obgyn@medicare.local',
            '0901000003',
            'Khám sản khoa, phụ khoa và tư vấn chăm sóc sức khỏe sinh sản.',
            NULL,
            'female',
            'Bác sĩ chuyên khoa II',
            '1980-11-05'::date,
            'active',
            'approved',
            TRUE
        ),
        (
            '20000000-0000-4000-8000-000000000004'::uuid,
            'DOC-IM-001',
            'Phạm Quốc Huy',
            'CCHN-IM-001',
            'quoc.huy.internal@medicare.local',
            '0901000004',
            'Khám sức khỏe tổng quát và quản lý bệnh lý nội khoa mạn tính.',
            NULL,
            'male',
            'Bác sĩ chuyên khoa I',
            '1983-02-17'::date,
            'active',
            'approved',
            TRUE
        ),
        (
            '20000000-0000-4000-8000-000000000005'::uuid,
            'DOC-SURG-001',
            'Võ Thành Đạt',
            'CCHN-SURG-001',
            'thanh.dat.surgery@medicare.local',
            '0901000005',
            'Tư vấn và điều trị các bệnh lý cần can thiệp ngoại khoa.',
            NULL,
            'male',
            'Bác sĩ chuyên khoa II',
            '1979-06-30'::date,
            'active',
            'approved',
            TRUE
        ),
        (
            '20000000-0000-4000-8000-000000000006'::uuid,
            'DOC-DERM-001',
            'Nguyễn Thùy Dương',
            'CCHN-DERM-001',
            'thuy.duong.dermatology@medicare.local',
            '0901000006',
            'Điều trị bệnh lý da, tóc, móng và chăm sóc da chuyên sâu.',
            NULL,
            'female',
            'Bác sĩ chuyên khoa I',
            '1987-01-21'::date,
            'active',
            'approved',
            TRUE
        ),
        (
            '20000000-0000-4000-8000-000000000007'::uuid,
            'DOC-ORTH-001',
            'Đỗ Anh Tuấn',
            'CCHN-ORTH-001',
            'anh.tuan.orthopedics@medicare.local',
            '0901000007',
            'Điều trị bệnh lý xương khớp, cơ và chấn thương vận động.',
            NULL,
            'male',
            'Bác sĩ chuyên khoa II',
            '1981-09-14'::date,
            'active',
            'approved',
            TRUE
        ),
        (
            '20000000-0000-4000-8000-000000000008'::uuid,
            'DOC-NEUR-001',
            'Bùi Minh Khoa',
            'CCHN-NEUR-001',
            'minh.khoa.neurology@medicare.local',
            '0901000008',
            'Khám và điều trị bệnh lý thần kinh, não bộ và cột sống.',
            NULL,
            'male',
            'Bác sĩ chuyên khoa I',
            '1984-03-09'::date,
            'active',
            'approved',
            TRUE
        ),
        (
            '20000000-0000-4000-8000-000000000009'::uuid,
            'DOC-ONCO-001',
            'Hoàng Ngọc Lan',
            'CCHN-ONCO-001',
            'ngoc.lan.oncology@medicare.local',
            '0901000009',
            'Tầm soát, chẩn đoán và điều trị bệnh lý ung bướu.',
            NULL,
            'female',
            'Bác sĩ chuyên khoa II',
            '1978-12-01'::date,
            'active',
            'approved',
            TRUE
        ),
        (
            '20000000-0000-4000-8000-000000000010'::uuid,
            'DOC-ENT-001',
            'Nguyễn Đức Long',
            'CCHN-ENT-001',
            'duc.long.ent@medicare.local',
            '0901000010',
            'Khám và điều trị bệnh lý tai, mũi, họng và vùng đầu cổ.',
            NULL,
            'male',
            'Bác sĩ chuyên khoa I',
            '1986-07-18'::date,
            'active',
            'approved',
            TRUE
        )
)
INSERT INTO doctors (
    id,
    code,
    full_name,
    license_number,
    email,
    phone,
    bio,
    avatar_url,
    gender,
    title,
    date_of_birth,
    status,
    review_status,
    booking_enabled
)
SELECT
    id,
    code,
    full_name,
    license_number,
    email,
    phone,
    bio,
    avatar_url,
    gender,
    title,
    date_of_birth,
    status,
    review_status,
    booking_enabled
FROM seed_doctors
ON CONFLICT (id) DO UPDATE SET
    code = EXCLUDED.code,
    full_name = EXCLUDED.full_name,
    license_number = EXCLUDED.license_number,
    email = EXCLUDED.email,
    phone = EXCLUDED.phone,
    bio = EXCLUDED.bio,
    avatar_url = EXCLUDED.avatar_url,
    gender = EXCLUDED.gender,
    title = EXCLUDED.title,
    date_of_birth = EXCLUDED.date_of_birth,
    status = EXCLUDED.status,
    review_status = EXCLUDED.review_status,
    booking_enabled = EXCLUDED.booking_enabled,
    updated_at = NOW();

WITH specialty_assignments (id, doctor_id, specialty_id, is_primary) AS (
    VALUES
        ('30000000-0000-4000-8000-000000000001'::uuid, '20000000-0000-4000-8000-000000000001'::uuid, '10000000-0000-4000-8000-000000000001'::uuid, TRUE),
        ('30000000-0000-4000-8000-000000000002'::uuid, '20000000-0000-4000-8000-000000000002'::uuid, '10000000-0000-4000-8000-000000000002'::uuid, TRUE),
        ('30000000-0000-4000-8000-000000000003'::uuid, '20000000-0000-4000-8000-000000000003'::uuid, '10000000-0000-4000-8000-000000000003'::uuid, TRUE),
        ('30000000-0000-4000-8000-000000000004'::uuid, '20000000-0000-4000-8000-000000000004'::uuid, '10000000-0000-4000-8000-000000000004'::uuid, TRUE),
        ('30000000-0000-4000-8000-000000000005'::uuid, '20000000-0000-4000-8000-000000000005'::uuid, '10000000-0000-4000-8000-000000000005'::uuid, TRUE),
        ('30000000-0000-4000-8000-000000000006'::uuid, '20000000-0000-4000-8000-000000000006'::uuid, '10000000-0000-4000-8000-000000000006'::uuid, TRUE),
        ('30000000-0000-4000-8000-000000000007'::uuid, '20000000-0000-4000-8000-000000000007'::uuid, '10000000-0000-4000-8000-000000000007'::uuid, TRUE),
        ('30000000-0000-4000-8000-000000000008'::uuid, '20000000-0000-4000-8000-000000000008'::uuid, '10000000-0000-4000-8000-000000000008'::uuid, TRUE),
        ('30000000-0000-4000-8000-000000000009'::uuid, '20000000-0000-4000-8000-000000000009'::uuid, '10000000-0000-4000-8000-000000000009'::uuid, TRUE),
        ('30000000-0000-4000-8000-000000000010'::uuid, '20000000-0000-4000-8000-000000000010'::uuid, '10000000-0000-4000-8000-000000000010'::uuid, TRUE)
)
INSERT INTO doctor_specialties (id, doctor_id, specialty_id, is_primary)
SELECT id, doctor_id, specialty_id, is_primary
FROM specialty_assignments
ON CONFLICT (doctor_id, specialty_id) DO UPDATE SET
    is_primary = EXCLUDED.is_primary;

COMMIT;

-- Verification query:
-- SELECT d.code, d.full_name, s.code AS specialty_code, s.name AS specialty_name
-- FROM doctors d
-- JOIN doctor_specialties ds ON ds.doctor_id = d.id
-- JOIN specialties s ON s.id = ds.specialty_id
-- WHERE d.code LIKE 'DOC-%-001'
-- ORDER BY d.code;
