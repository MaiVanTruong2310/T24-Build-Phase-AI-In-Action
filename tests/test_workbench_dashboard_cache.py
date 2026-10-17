from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.api.endpoints import workbench as workbench_api


@pytest.mark.asyncio
async def test_workbench_dashboard_cache_is_scoped_by_user_and_facilities(monkeypatch):
    user_id = uuid4()
    facilities = [str(uuid4()), str(uuid4())]
    expected = {"counts": {}, "overdue": 0, "emergency": 0, "followups": []}
    captured = {}

    async def get_cache(namespace, params):
        captured["namespace"] = namespace
        captured["params"] = params
        return True, expected, "0"

    monkeypatch.setattr(workbench_api, "get_redis_api_cache", get_cache)

    await workbench_api.dashboard(
        (SimpleNamespace(id=user_id), SimpleNamespace(facility_ids=facilities)),
        None,
    )

    assert captured == {
        "namespace": "workbench-dashboard",
        "params": (str(user_id), tuple(sorted(facilities))),
    }
