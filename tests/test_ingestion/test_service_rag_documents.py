from src.medical_assistant.ingestion.crawlers.services.build_rag_documents import service_to_documents


def test_service_to_documents_builds_summary_content_and_price_chunks() -> None:
    record = {
        "service_key": "goi-a",
        "service_id": "prod_1",
        "name": "Gói A",
        "description": "Mô tả gói khám và lợi ích dành cho khách hàng.",
        "source_url": "https://online.vinmec.com/vn/dich-vu/goi-a",
        "content": {"benefits": [{"data": {"items": [{"text": "Phát hiện sớm"}, {"text": "Tư vấn chuyên sâu"}]}}]},
        "branches": [
            {
                "name": "Vinmec A",
                "location": "Hà Nội",
                "variants": [{"amount": 1000000, "currency": "vnd"}],
            }
        ],
    }

    documents = service_to_documents(record, chunk_size=128, chunk_overlap=16)

    assert {document["metadata"]["section"] for document in documents} == {
        "summary",
        "benefits",
        "branches_and_prices",
    }
    assert all(document["metadata"]["service_key"] == "goi-a" for document in documents)
