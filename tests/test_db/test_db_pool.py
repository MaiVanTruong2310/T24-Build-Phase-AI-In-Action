import pytest

from src.config import Settings
from src.db import session as database


def test_shared_database_url_prefers_required_ssl():
    base = "postgresql://user:secret@pooler.example:5432/postgres"
    assert database._shared_database_url(base, base + "?sslmode=require") == base + "?sslmode=require"
    assert database._shared_database_url(base + "?sslmode=require", base) == base + "?sslmode=require"
    assert database._shared_database_url(base, base) == base
    assert database._shared_database_url(base, base.replace("user", "other")) is None
    assert database._shared_database_url(base, base + "?connect_timeout=5") is None


@pytest.mark.asyncio
async def test_matching_database_urls_share_one_bounded_pool(monkeypatch):
    base = "postgresql://user:secret@pooler.example:5432/postgres"
    settings = Settings(
        _env_file=None,
        database_url=base,
        auth_database_url=base + "?sslmode=require",
        database_pool_size=3,
        database_max_overflow=1,
    )
    monkeypatch.setattr(database, "get_settings", lambda: settings)
    database.get_engine.cache_clear()
    database.get_auth_engine.cache_clear()
    try:
        engine = database.get_engine()
        assert database.get_auth_engine() is engine
        assert engine.url.query["sslmode"] == "require"
        assert engine.pool.size() == 3
        assert engine.pool._max_overflow == 1
    finally:
        await database.get_engine().dispose()
        database.get_auth_engine.cache_clear()
        database.get_engine.cache_clear()
