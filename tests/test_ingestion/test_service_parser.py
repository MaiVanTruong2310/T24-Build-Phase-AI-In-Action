from src.medical_assistant.ingestion.crawlers.services.service_parser import (
    canonical_service_url,
    extract_service_links,
    parse_service,
    service_key_for_url,
)


def test_service_url_normalization_and_listing_extraction() -> None:
    html = """
    <a href="/vn/dich-vu/goi-a?tracking=1">A</a>
    <a href="https://online.vinmec.com/vn/dich-vu/goi-b/">B</a>
    <a href="/vn/dich-vu?sortBy=price">Filtered listing</a>
    <a href="/vn/lop-hoc/khoa-a">Course</a>
    """

    assert canonical_service_url("https://online.vinmec.com/vn/dich-vu/goi-a/?x=1") == (
        "https://online.vinmec.com/vn/dich-vu/goi-a"
    )
    assert service_key_for_url("https://online.vinmec.com/vn/dich-vu/goi-a") == "goi-a"
    assert service_key_for_url("https://online.vinmec.com/vn/dich-vu") is None
    assert extract_service_links(html) == [
        "https://online.vinmec.com/vn/dich-vu/goi-a",
        "https://online.vinmec.com/vn/dich-vu/goi-b",
    ]


def test_parse_service_preserves_product_prices_and_content() -> None:
    product = {
        "id": "prod_1",
        "title": "Gói khám A",
        "description": "Mô tả",
        "metadata": {"star": 4.9, "sold_count": 10, "valid_duration": 90},
        "categories": [{"id": "cat_1", "name": "Tổng quát", "handle": "tong-quat"}],
        "tags": [{"value": "Nữ", "metadata": {"group": "gender"}}],
        "variants": [
            {
                "id": "variant_1",
                "title": "Tiêu chuẩn",
                "options": [{"value": "Tiêu chuẩn", "option": {"title": "Loại gói"}}],
                "images": [{"url": "https://example.com/a.jpg", "rank": 0}],
            }
        ],
    }
    prices = {
        "data": {
            "prices": [
                {
                    "branch_id": "branch_1",
                    "branch_name": "Vinmec A",
                    "branch_location": "Hà Nội",
                    "variants": [
                        {
                            "variant_id": "variant_1",
                            "variant_title": "Tiêu chuẩn",
                            "amount": 1000000,
                            "currency_code": "vnd",
                        }
                    ],
                }
            ]
        }
    }
    details = [
        {
            "id": "detail_1",
            "branch_id": "branch_1",
            "metadata": {
                "tabs": {"intro": [{"slug": "richtext", "data": {"html": "<p>Nội dung <b>giới thiệu</b></p>"}}]}
            },
        }
    ]

    record = parse_service(
        product,
        prices,
        details,
        "https://online.vinmec.com/vn/dich-vu/goi-kham-a",
    )

    assert record["service_key"] == "goi-kham-a"
    assert record["tags"] == {"gender": ["Nữ"]}
    assert record["branches"][0]["variants"][0]["amount"] == 1000000
    assert record["branches"][0]["detail"]["id"] == "detail_1"
    assert record["content"]["intro"][0]["data"]["html_text"] == "Nội dung giới thiệu"
