"""get_specialty_display_name: khớp NGUYÊN TỪ, không khớp chuỗi con ("Nhi" từng ra "Truyền nhiễm")."""

import pytest

from src.medical_assistant.domain.language_service import get_specialty_display_name


@pytest.mark.parametrize(
    ("raw", "vi", "en"),
    [
        ("Nhi", "Nhi khoa", "Pediatrics"),
        ("khoa nhi", "Nhi khoa", "Pediatrics"),
        ("trẻ em", "Nhi khoa", "Pediatrics"),
        ("Truyền nhiễm", "Truyền nhiễm", "Infectious Diseases"),
        ("tim mach", "Trung tâm Tim mạch", "Cardiology Center"),
        ("sức khỏe tinh thần", "Trung tâm chăm sóc sức khỏe tinh thần", "Mental Health Care Center"),
        ("ENT", "Tai - Mũi - Họng", "Otorhinolaryngology (ENT)"),
        ("mắt", "Mắt (Nhãn khoa)", "Ophthalmology"),
    ],
)
def test_specialty_display_name_matches_whole_words(raw, vi, en):
    assert get_specialty_display_name(raw, "vi") == vi
    assert get_specialty_display_name(raw, "en") == en
