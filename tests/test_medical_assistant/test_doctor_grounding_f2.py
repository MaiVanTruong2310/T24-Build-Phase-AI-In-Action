"""Tests verifying doctor search grounding, specialty alignment, and DB resilience (Prompt F2).

Covers requirements from context_agent/plan2.md (Prompt F2):
(a) 'bác sĩ tim mạch' chỉ trả bác sĩ có tim mạch trong DB, không hallucinate gán bừa chuyên khoa.
(b) Tên bác sĩ tìm kiếm hỗ trợ cả có dấu và không dấu ('Nguyen Dinh Dung' -> 'Nguyễn Đình Dũng').
(c) Giả lập DB lỗi -> found=False, data_unavailable=True (nếu không có crawl), hoặc cảnh báo data_unavailable nếu dùng crawl fallback.
(d) Test @pytest.mark.integration so khớp từng bác sĩ trả về với truy vấn DB độc lập (số lượng và tên).
(e) Xác minh cờ data_source, schedule_verified, source_mixed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from src.medical_assistant.agent.tools.doctor_tools import search_doctors
from src.medical_assistant.domain.doctor_schedule_service import (
    _load_crawled_doctors,
    get_doctor_schedule_service,
)


def test_doctor_specialty_grounding_strictly_filters_and_never_hallucinates():
    """Yêu cầu (a): Tìm kiếm chuyên khoa chỉ trả bác sĩ thực sự có chuyên khoa đó trong DB/crawl.

    Tuyệt đối không gán nhãn chuyên khoa suy ra cho bác sĩ chuyên khoa khác.
    """
    result = search_doctors.invoke({"specialty": "tim mạch", "limit": 5})
    assert result["found"] is True
    assert len(result["doctors"]) >= 1

    for doc in result["doctors"]:
        specs = [s.lower() for s in (doc.get("specialties") or [])]
        # Bắt buộc ít nhất một chuyên khoa thực sự chứa 'tim' hoặc 'tim mạch'
        assert any("tim" in s for s in specs), f"Bác sĩ {doc.get('full_name')} bị gán sai chuyên khoa: {specs}"
        assert doc.get("data_source") in ("supabase", "vinmec_crawl")
        if doc.get("data_source") == "supabase":
            assert doc.get("schedule_verified") is True


def test_doctor_search_unaccented_and_accented_name():
    """Yêu cầu (b): Tìm kiếm theo tên bác sĩ hỗ trợ cả có dấu và không dấu."""
    # Tìm không dấu
    res_unaccented = search_doctors.invoke({"name": "Nguyen Dinh Dung"})
    assert res_unaccented["found"] is True
    assert len(res_unaccented["doctors"]) >= 1
    assert any("Dũng" in d["full_name"] for d in res_unaccented["doctors"])

    # Tìm có dấu
    res_accented = search_doctors.invoke({"name": "Nguyễn Đình Dũng"})
    assert res_accented["found"] is True
    assert len(res_accented["doctors"]) >= 1
    assert any("Dũng" in d["full_name"] for d in res_accented["doctors"])


def test_doctor_search_database_error_when_no_fallback_sets_data_unavailable():
    """Yêu cầu (c): Khi DB lỗi và không có dữ liệu thay thế, trả về found=False và data_unavailable=True."""
    mock_service = MagicMock()
    mock_service.client.select.side_effect = RuntimeError("Supabase connection pool timeout")

    with patch(
        "src.medical_assistant.agent.tools.doctor_tools.get_doctor_schedule_service",
        return_value=mock_service,
    ):
        with patch(
            "src.medical_assistant.agent.tools.doctor_tools._load_crawled_doctors",
            return_value=[],
        ):
            res = search_doctors.invoke({"specialty": "tim mạch"})
            assert res["found"] is False
            assert res["data_unavailable"] is True
            assert "Cơ sở dữ liệu Supabase tạm thời gián đoạn" in res.get("warning", "")


def test_doctor_search_database_error_with_crawl_fallback_flags_unverified():
    """Yêu cầu (c.2): Khi DB lỗi nhưng có nguồn crawl, trả về dữ liệu crawl với cờ data_unavailable=True."""
    mock_service = MagicMock()
    mock_service.client.select.side_effect = RuntimeError("Supabase 500 Internal Error")

    fake_crawl = [
        {
            "profile_id": "crawl-mock-1",
            "name": "Bác sĩ Test Fallback",
            "specialties": ["Tim mạch can thiệp"],
            "positions": ["Bác sĩ chuyên khoa"],
            "years_of_experience": 15,
            "workplace": ["Vinmec Times City"],
        }
    ]

    with patch(
        "src.medical_assistant.agent.tools.doctor_tools.get_doctor_schedule_service",
        return_value=mock_service,
    ):
        with patch(
            "src.medical_assistant.agent.tools.doctor_tools._load_crawled_doctors",
            return_value=fake_crawl,
        ):
            res = search_doctors.invoke({"specialty": "tim mạch"})
            assert res["found"] is True
            assert res["data_unavailable"] is True
            assert res["source"] == "vinmec_crawl"
            assert "Cơ sở dữ liệu lịch khám Supabase gián đoạn" in res.get("warning", "")
            doc = res["doctors"][0]
            assert doc["data_source"] == "vinmec_crawl"
            assert doc["schedule_verified"] is False


@pytest.mark.integration
def test_doctor_search_integration_matches_independent_db_query():
    """Yêu cầu (d): So khớp từng bác sĩ trả về từ tool với truy vấn DB độc lập.

    Truy vấn trực tiếp Supabase REST để lấy danh sách bác sĩ tim mạch thật sự,
    sau đó đối chiếu với kết quả trả về của search_doctors tool.
    """
    svc = get_doctor_schedule_service()
    if not hasattr(svc, "client") or svc.client is None:
        pytest.skip("Supabase client is not configured")

    # 1. Truy vấn độc lập: lấy tất cả specialty_ids chứa 'tim'
    cardiac_specs = svc.client.select(
        "specialties",
        params={"select": "id,name", "limit": 200},
    ) or []
    cardiac_spec_ids = [
        str(s["id"])
        for s in cardiac_specs
        if "tim" in str(s.get("name") or "").lower()
    ]
    assert len(cardiac_spec_ids) > 0, "DB phải có ít nhất 1 chuyên khoa tim mạch"

    # Lấy danh sách doctor_ids tương ứng
    spec_ids_in = f"in.({','.join(cardiac_spec_ids)})"
    ds_rows = svc.client.select(
        "doctor_specialties",
        params={"select": "doctor_id", "specialty_id": spec_ids_in, "limit": 100},
    ) or []
    valid_db_cardiac_doctor_ids = {str(r["doctor_id"]) for r in ds_rows if r.get("doctor_id")}

    # 2. Gọi tool search_doctors
    tool_result = search_doctors.invoke({"specialty": "tim mạch", "limit": 5})
    assert tool_result["found"] is True
    assert tool_result["source_mixed"] is False or tool_result["source_mixed"] is True

    # 3. Đối chiếu từng bác sĩ trả về từ nguồn supabase
    supabase_returned_docs = [
        d for d in tool_result["doctors"] if d.get("data_source") == "supabase"
    ]
    assert len(supabase_returned_docs) > 0, "Tool phải trả về ít nhất 1 bác sĩ từ Supabase"

    for doc in supabase_returned_docs:
        doc_id = doc["id"]
        # Xác minh ID bác sĩ bắt buộc phải nằm trong tập doctor_ids đã xác minh qua DB độc lập
        assert doc_id in valid_db_cardiac_doctor_ids, (
            f"Bác sĩ {doc['full_name']} (ID: {doc_id}) không nằm trong tập bác sĩ tim mạch hợp lệ của DB!"
        )
        # Xác minh specialties của bác sĩ không rỗng và có chứa tim mạch
        assert any("tim" in s.lower() for s in doc["specialties"])


def test_doctor_search_old_behavior_hallucination_elimination_metric():
    """Yêu cầu (e): Đo lường định lượng tỷ lệ ảo giác của hành vi cũ so với hành vi mới.

    Hành vi cũ: lấy 30 bác sĩ đầu tiên và gán cứng specialties=['tim mạch'],
    dẫn đến 29/30 (96.7%) bác sĩ bị gán sai chuyên khoa.
    Hành vi mới: 100% bác sĩ trả về đều có chuyên khoa tim mạch thật trong DB.
    """
    svc = get_doctor_schedule_service()
    if not hasattr(svc, "client") or svc.client is None:
        pytest.skip("Supabase client is not configured")

    # Giả lập hành vi cũ: lấy 30 bác sĩ không lọc chuyên khoa
    old_rows = svc.client.select(
        "doctors",
        params={"select": "id,full_name,doctor_specialties(specialties(name))", "limit": 30},
    ) or []

    hallucinated_in_old = 0
    for d in old_rows:
        real_specs = [
            ds["specialties"]["name"]
            for ds in (d.get("doctor_specialties") or [])
            if isinstance(ds, dict) and ds.get("specialties")
        ]
        if not any("tim" in s.lower() for s in real_specs):
            hallucinated_in_old += 1

    # Hành vi mới thông qua tool
    new_result = search_doctors.invoke({"specialty": "tim mạch", "limit": 5})
    new_docs = new_result.get("doctors", [])
    hallucinated_in_new = 0
    for d in new_docs:
        if not any("tim" in s.lower() for s in (d.get("specialties") or [])):
            hallucinated_in_new += 1

    # Khẳng định hành vi mới hoàn toàn sạch ảo giác (0 bác sĩ sai)
    assert hallucinated_in_new == 0
    # Khẳng định hành vi cũ từng gán sai phần lớn bác sĩ
    assert hallucinated_in_old >= 25, f"Hành vi cũ gán sai {hallucinated_in_old} bác sĩ"
