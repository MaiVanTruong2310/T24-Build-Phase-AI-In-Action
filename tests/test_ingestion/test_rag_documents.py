import json
from pathlib import Path

from src.medical_assistant.ingestion.crawlers.doctors.build_rag_documents import (
    profile_to_documents,
    read_jsonl,
    write_jsonl,
)


def sample_profile() -> dict:
    return {
        "profile_id": "50786",
        "language": "vi",
        "name": "Phùng Nam Lâm",
        "credentials": ["Tiến sĩ", "Bác sĩ"],
        "overview": "Bác sĩ có nhiều kinh nghiệm trong lĩnh vực cấp cứu.",
        "positions": ["Phó Tổng Giám đốc chuyên môn"],
        "specialties": ["Hồi sức - Cấp cứu"],
        "workplace": ["Hệ thống Y tế Vinmec"],
        "education": ["Đào tạo tại Việt Nam", "Đào tạo tại Hoa Kỳ"],
        "experience": ["Bệnh viện Bạch Mai", "Vinmec Times City"],
        "source_url": "https://www.vinmec.com/vie/chuyen-gia-y-te/phung-nam-lam-50786-vi",
    }


def test_profile_to_documents_preserves_metadata_and_markdown() -> None:
    documents = profile_to_documents(sample_profile())

    sections = {document["metadata"]["section"] for document in documents}
    assert {
        "overview",
        "positions",
        "specialties",
        "workplace",
        "education",
        "experience",
    } <= sections
    overview = next(document for document in documents if document["metadata"]["section"] == "overview")
    assert overview["chunk_id"] == "vinmec-50786-vi-overview-1"
    assert "# Tiến sĩ, Bác sĩ Phùng Nam Lâm" in overview["text"]
    assert "## Giới thiệu" in overview["text"]
    assert overview["metadata"]["specialties"] == ["Hồi sức - Cấp cứu"]


def test_jsonl_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "documents.jsonl"
    records = [{"chunk_id": "one", "text": "Xin chào", "metadata": {}}]

    assert write_jsonl(path, records) == 1
    assert list(read_jsonl(path)) == records
    assert json.loads(path.read_text(encoding="utf-8")) == records[0]
