import pytest

from src.medical_assistant.ingestion.crawl_utils.chunking import TokenChunker
from src.medical_assistant.ingestion.crawlers.doctors.build_rag_documents import profile_to_documents
from src.medical_assistant.ingestion.crawlers.specialties.build_rag_documents import specialty_to_documents


def test_token_chunker_honors_limit_and_overlap() -> None:
    chunker = TokenChunker(chunk_size=80, overlap=12)
    body = " ".join(f"token-{index}" for index in range(160))
    chunks = chunker.split(body)

    assert len(chunks) > 1
    assert all(chunk.token_count <= 80 for chunk in chunks)
    assert [chunk.index for chunk in chunks] == list(range(1, len(chunks) + 1))
    assert all(chunk.count == len(chunks) for chunk in chunks)

    encoding = chunker.encoding
    encoded_chunks = [encoding.encode(chunk.text) for chunk in chunks]
    for previous, current in zip(encoded_chunks, encoded_chunks[1:]):
        assert previous[-12:] == current[:12]


def test_doctor_chunks_stay_within_one_section() -> None:
    profile = {
        "profile_id": "1",
        "language": "vi",
        "name": "Bác sĩ A",
        "overview": " ".join(["Tổng quan dài."] * 200),
        "education": ["Đào tạo chuyên sâu."],
        "source_url": "https://example.test/doctor",
    }
    documents = profile_to_documents(profile, chunk_size=100, chunk_overlap=15)

    overview = [item for item in documents if item["metadata"]["section"] == "overview"]
    assert len(overview) > 1
    assert all("## Đào tạo" not in item["text"] for item in overview)
    assert all(item["metadata"]["parent_id"] == "vinmec-1-vi-overview" for item in overview)
    assert all(item["metadata"]["token_count"] <= 100 for item in documents)


def test_specialty_chunks_preserve_block_parent() -> None:
    record = {
        "specialty_key": "tim-mach",
        "language": "vi",
        "name": "Tim mạch",
        "overview": [
            {"title": "Điều trị", "content": [" ".join(["Nội dung."] * 200)]}
        ],
        "services": [],
        "technologies": [],
        "source_url": "https://example.test/specialty",
    }
    documents = specialty_to_documents(record, chunk_size=100, chunk_overlap=15)

    assert len(documents) > 1
    assert len({item["metadata"]["parent_id"] for item in documents}) == 1
    assert all(item["metadata"]["token_count"] <= 100 for item in documents)


@pytest.mark.parametrize("size,overlap", [(63, 10), (100, -1), (100, 100)])
def test_token_chunker_rejects_invalid_configuration(size: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        TokenChunker(chunk_size=size, overlap=overlap)
