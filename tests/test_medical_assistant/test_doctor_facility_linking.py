from src.medical_assistant.domain.doctor_schedule_service import DoctorScheduleService
from src.medical_assistant.domain.facility_linking import (
    canonical_facilities,
    facility_key,
    match_facility,
    workplace_department,
)

TIMES_CITY_ID = "026b309d-33ad-58ab-af37-9cf90c0c2c4e"
DOCTOR_ONE_ID = "db8fc02e-8527-5b62-ac5c-3974af254e50"
DOCTOR_TWO_ID = "11111111-1111-4111-8111-111111111111"


def test_workplace_maps_to_canonical_facility_and_extracts_department():
    facilities = canonical_facilities(
        [
            {
                "id": TIMES_CITY_ID,
                "code": "BENH_VIEN_DA_KHOA_QUOC_TE_VINMEC_TIMES_CITY",
                "name": "Bệnh viện Đa khoa Quốc tế Vinmec Times City",
            },
            {
                "id": "22222222-2222-4222-8222-222222222222",
                "code": "VINMEC_TIMES_CITY_INTERNATIONAL_HOSPITAL",
                "name": "Vinmec Times City International Hospital",
            },
        ]
    )
    workplace = "Khoa Nội Tiêu hóa - Gan mật - Bệnh viện Đa khoa Quốc tế Vinmec Times City"

    assert facility_key(workplace) == ("times_city", "hospital")
    assert match_facility(workplace, facilities)["id"] == TIMES_CITY_ID
    assert workplace_department(workplace) == "Khoa Nội Tiêu hóa - Gan mật"


def test_specialty_clinic_inside_hospital_is_not_misclassified_as_general_clinic():
    workplace = "Phòng khám chuyên sâu Mạch vành - Bệnh viện Đa khoa Quốc tế Vinmec Times City"
    assert facility_key(workplace) == ("times_city", "hospital")


class FacilityAwareClient:
    def __init__(self):
        self.calls = []

    def select(self, table, params=None):
        params = params or {}
        self.calls.append((table, params))
        if table == "facilities":
            return [{"id": TIMES_CITY_ID, "code": "TIMES_CITY", "name": "Bệnh viện Vinmec Times City"}]
        if table == "specialties":
            return [{"id": "33333333-3333-4333-8333-333333333333", "code": "TIEU_HOA", "name": "Tiêu hóa"}]
        if table == "doctor_specialties":
            return [{"doctor_id": DOCTOR_ONE_ID}, {"doctor_id": DOCTOR_TWO_ID}]
        if table == "doctor_facilities":
            return [{"doctor_id": DOCTOR_ONE_ID, "department": "Khoa Nội Tiêu hóa - Gan mật"}]
        if table == "doctors":
            assert params["id"] == f"in.({DOCTOR_ONE_ID})"
            return [
                {
                    "id": DOCTOR_ONE_ID,
                    "full_name": "Nguyễn Xuân Mười",
                    "title": "Thạc sĩ, Bác sĩ",
                    "years_of_experience": 21,
                    "languages": ["vi"],
                    "source_url": "https://www.vinmec.com/vie/chuyen-gia-y-te/nguyen-xuan-muoi-51490-vi",
                }
            ]
        if table == "doctor_schedules":
            assert params["facility_id"] == f"eq.{TIMES_CITY_ID}"
            return []
        return []


def test_database_search_intersects_specialty_with_facility_relationships():
    service = DoctorScheduleService(client=FacilityAwareClient())
    doctors = service.get_available_doctors_and_slots(
        specialty_name="Tiêu hóa",
        facility_id=TIMES_CITY_ID,
        limit_doctors=3,
    )

    assert [doctor["full_name"] for doctor in doctors] == ["Nguyễn Xuân Mười"]
    assert doctors[0]["workplace"] == "Bệnh viện Vinmec Times City"
    assert doctors[0]["department"] == "Khoa Nội Tiêu hóa - Gan mật"


def test_specialized_times_city_centers_map_to_times_city_hospital():
    assert facility_key("Trung tâm Y Học Cổ Truyền Vinmec - Sao Phương Đông") == ("times_city", "hospital")
    assert facility_key("Trung tâm Chăm sóc Sức khỏe Tinh Thần") == ("times_city", "hospital")
    assert facility_key("Viện nghiên cứu Tế bào gốc và Công nghệ gen Vinmec") == ("times_city", "hospital")
    assert facility_key("Khối Sản xuất Tế bào, Trung tâm Công nghệ Cao Vinmec") == ("times_city", "hospital")
    assert facility_key("Ngân hàng mô Vinmec") == ("times_city", "hospital")
    assert facility_key("Trung tâm Nha khoa Quốc tế Vinmec View Dental Premium") == ("times_city", "hospital")


def test_extract_workplaces_from_record_fallback():
    from src.medical_assistant.domain.facility_linking import extract_workplaces_from_record

    # 1. Primary Nơi làm việc present
    rec1 = {"sections": {"Nơi làm việc": ["Bệnh viện Đa khoa Quốc tế Vinmec Đà Nẵng"]}}
    assert extract_workplaces_from_record(rec1) == ["Bệnh viện Đa khoa Quốc tế Vinmec Đà Nẵng"]

    # 2. Missing Nơi làm việc, fallback to Chức vụ
    rec2 = {"sections": {"Chức vụ": ["Điều dưỡng Trưởng - Phòng khám Vinmec Sài Gòn"]}}
    wps = extract_workplaces_from_record(rec2)
    assert any("Vinmec Sài Gòn" in wp for wp in wps)

    # 3. Missing Nơi làm việc, fallback to Kinh nghiệm làm việc
    rec3 = {
        "sections": {
            "Kinh nghiệm làm việc": [
                "2010 - 2015: Bệnh viện Chợ Rẫy",
                "2015 - đến nay: Bác sĩ khoa Khám bệnh - Bệnh viện Đa khoa Quốc tế Vinmec Central Park",
            ]
        }
    }
    wps = extract_workplaces_from_record(rec3)
    assert any("Central Park" in wp for wp in wps)
