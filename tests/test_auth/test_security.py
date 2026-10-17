from src.config import get_settings
from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_round_trip():
    encoded = hash_password("correct horse battery staple")

    assert encoded != "correct horse battery staple"
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_access_token_round_trip(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes")
    get_settings.cache_clear()

    token, _ = create_access_token("user-123", "patient")
    payload = decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["role"] == "patient"
    assert payload["type"] == "access"

    get_settings.cache_clear()


def test_refresh_token_hash_is_deterministic_and_one_way():
    token = "refresh-token-value"

    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert hash_refresh_token(token) != token
