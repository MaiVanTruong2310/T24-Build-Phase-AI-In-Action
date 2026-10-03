from src.medical_assistant.ingestion.crawlers.diseases.build_rag_documents import disease_to_documents
from src.medical_assistant.ingestion.crawlers.diseases.build_specialty_facilities import (
    build_documents as build_facility_documents,
)
from src.medical_assistant.ingestion.crawlers.diseases.build_symptom_routes import route_to_documents


def test_disease_documents_are_marked_education_only() -> None:
    documents = disease_to_documents(
        {
            "disease_key": "benh-mau",
            "language": "vi",
            "name": "Bệnh mẫu",
            "source_url": "https://example.test/benh-mau",
            "sections": [{"key": "symptoms", "heading": "Triệu chứng", "content": ["Nội dung mẫu"]}],
        }
    )

    assert len(documents) == 1
    assert documents[0]["metadata"]["category"] == "disease_education"
    assert documents[0]["metadata"]["usage"] == "education_only"
    assert documents[0]["metadata"]["section"] == "symptoms"


def test_symptom_routes_prefer_medical_specialties() -> None:
    documents = route_to_documents(
        {
            "title": "Gói mẫu",
            "source_url": "https://example.test/goi-mau",
            "content": {"text": "Đau đầu kéo dài hoặc tái phát nhiều lần."},
            "structured_data": {
                "service": {"id": "service-1", "categories": ["Thần kinh - Đột quỵ"]},
                "medical_specialties": ["Nội thần kinh"],
            },
            "review": {"status": "draft"},
        }
    )

    assert documents
    assert documents[0]["metadata"]["category"] == "symptom_specialty"
    assert documents[0]["metadata"]["name"] == "Nội thần kinh"
    assert documents[0]["metadata"]["source_review_status"] == "draft"


def test_specialty_facilities_use_official_address_and_url() -> None:
    routes = iter(
        [
            {
                "title": "Gói đau đầu",
                "source_url": "https://online.vinmec.com/goi-dau-dau",
                "content": {"text": "Đau đầu kéo dài hoặc tái phát."},
                "structured_data": {
                    "service": {"id": "service-1", "description": "Đánh giá đau đầu"},
                    "medical_specialties": ["Nội thần kinh"],
                    "branches": [{"name": "Bệnh viện Đa khoa Quốc tế Vinmec Times City", "location": "Hà Nội"}],
                },
            }
        ]
    )
    hospitals = [
        {
            "name": "Bệnh viện Đa khoa Quốc tế Vinmec Times City",
            "address": "458 Minh Khai, Hà Nội",
            "hotline_display": "024 3974 3556",
            "detail_url": "https://www.vinmec.com/vie/co-so-y-te/times-city",
        }
    ]

    documents = list(build_facility_documents(routes, hospitals))

    assert documents
    assert documents[0]["metadata"]["category"] == "specialty_facility"
    assert documents[0]["metadata"]["source_url"].endswith("/times-city")
    assert "458 Minh Khai" in documents[0]["text"]
