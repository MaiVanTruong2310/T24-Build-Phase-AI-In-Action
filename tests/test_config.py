from src.config import parse_cors_origins


def test_parse_cors_origins_normalizes_and_deduplicates_origins():
    assert parse_cors_origins(
        " http://localhost:5173/,https://example.com,https://example.com/,,"
    ) == ["http://localhost:5173", "https://example.com"]
