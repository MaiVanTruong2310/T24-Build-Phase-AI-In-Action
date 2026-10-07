from types import SimpleNamespace

import pytest

from src.api.dependencies import get_current_user
from src.api.endpoints.catalog import get_catalog_service
from src.core.cache import get_catalog_cache
from src.main import app


class CountingCatalogService:
    """Minimal catalog double used to verify endpoint cache behavior."""

    def __init__(self):
        self.list_calls = 0

    async def list_services(self, **kwargs):
        assert kwargs["public_only"] is True
        self.list_calls += 1
        return []


@pytest.mark.asyncio
async def test_public_catalog_list_uses_ttl_cache(client):
    service = CountingCatalogService()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="patient", status="active")
    app.dependency_overrides[get_catalog_service] = lambda: service
    get_catalog_cache().clear()
    try:
        first = await client.get("/api/v1/services")
        second = await client.get("/api/v1/services")
    finally:
        app.dependency_overrides.clear()
        get_catalog_cache().clear()

    assert first.status_code == 200
    assert first.headers["x-cache"] == "MISS"
    assert second.status_code == 200
    assert second.headers["x-cache"] == "HIT"
    assert service.list_calls == 1
