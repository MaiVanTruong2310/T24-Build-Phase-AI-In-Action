from types import SimpleNamespace

import pytest

from src.api.dependencies import get_current_user
from src.api.endpoints import doctor as doctor_endpoints
from src.api.endpoints import service as service_endpoints
from src.api.endpoints import specialty as specialty_endpoints
from src.api.endpoints.catalog import get_catalog_service
from src.main import app


class CountingCatalogService:
    """Minimal catalog double used to verify endpoint cache behavior."""

    def __init__(self):
        self.list_calls = 0
        self.specialty_calls = []
        self.doctor_calls = []
        self.service_filters = []

    async def list_services(self, **kwargs):
        assert kwargs["public_only"] is True
        self.list_calls += 1
        self.service_filters.append(kwargs)
        return []

    async def list_specialties(self, **kwargs):
        self.specialty_calls.append(kwargs)
        return []

    async def list_doctors(self, **kwargs):
        self.doctor_calls.append(kwargs)
        return []


@pytest.mark.asyncio
async def test_public_catalog_list_uses_redis_cache(client, monkeypatch):
    service = CountingCatalogService()
    entries = {}

    async def get_cache(family, params):
        return (True, entries[(family, params)], "0") if (family, params) in entries else (False, None, "0")

    async def set_cache(family, params, value, generation):
        entries[(family, params)] = value

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="patient", status="active")
    app.dependency_overrides[get_catalog_service] = lambda: service
    monkeypatch.setattr(service_endpoints, "get_redis_api_cache", get_cache)
    monkeypatch.setattr(service_endpoints, "set_redis_api_cache", set_cache)
    try:
        first = await client.get("/api/v1/services")
        second = await client.get("/api/v1/services")
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert first.headers["x-cache"] == "MISS"
    assert second.status_code == 200
    assert second.headers["x-cache"] == "HIT"
    assert service.list_calls == 1


@pytest.mark.asyncio
async def test_specialty_search_cache_partitions_search_and_reuses_exact_query(client, monkeypatch):
    service = CountingCatalogService()
    entries = {}

    async def get_cache(family, params):
        return (True, entries[(family, params)], "0") if (family, params) in entries else (False, None, "0")

    async def set_cache(family, params, value, generation):
        entries[(family, params)] = value

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="patient", status="active")
    app.dependency_overrides[get_catalog_service] = lambda: service
    monkeypatch.setattr(specialty_endpoints, "get_redis_api_cache", get_cache)
    monkeypatch.setattr(specialty_endpoints, "set_redis_api_cache", set_cache)
    try:
        cardio = await client.get("/api/v1/specialties?search=cardio&facility_id=00000000-0000-0000-0000-000000000001")
        neuro = await client.get("/api/v1/specialties?search=neuro&facility_id=00000000-0000-0000-0000-000000000001")
        cardio_again = await client.get(
            "/api/v1/specialties?search=cardio&facility_id=00000000-0000-0000-0000-000000000001"
        )
    finally:
        app.dependency_overrides.clear()

    assert [cardio.status_code, neuro.status_code, cardio_again.status_code] == [200, 200, 200]
    assert cardio.headers["x-cache"] == neuro.headers["x-cache"] == "MISS"
    assert cardio_again.headers["x-cache"] == "HIT"
    assert len(service.specialty_calls) == 2


@pytest.mark.asyncio
async def test_doctor_search_cache_partitions_search_terms(client, monkeypatch):
    service = CountingCatalogService()
    requested = []

    async def get_cache(family, params):
        requested.append((family, params))
        return False, None, "0"

    async def set_cache(*_args):
        return None

    app.dependency_overrides[get_catalog_service] = lambda: service
    monkeypatch.setattr(doctor_endpoints, "get_redis_api_cache", get_cache)
    monkeypatch.setattr(doctor_endpoints, "set_redis_api_cache", set_cache)
    try:
        first = await client.get("/api/v1/doctors?name=An")
        second = await client.get("/api/v1/doctors?name=Binh")
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == second.status_code == 200
    assert service.doctor_calls[0]["name"] == "An"
    assert service.doctor_calls[1]["name"] == "Binh"
    assert requested[0] != requested[1]


@pytest.mark.asyncio
async def test_service_search_cache_partitions_search_terms(client, monkeypatch):
    service = CountingCatalogService()
    requested = []

    async def get_cache(family, params):
        requested.append((family, params))
        return False, None, "0"

    async def set_cache(*_args):
        return None

    app.dependency_overrides[get_catalog_service] = lambda: service
    monkeypatch.setattr(service_endpoints, "get_redis_api_cache", get_cache)
    monkeypatch.setattr(service_endpoints, "set_redis_api_cache", set_cache)
    try:
        first = await client.get("/api/v1/services?name=general")
        second = await client.get("/api/v1/services?name=cardio")
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == second.status_code == 200
    assert service.service_filters[0]["name"] == "general"
    assert service.service_filters[1]["name"] == "cardio"
    assert requested[0] != requested[1]
