"""Ẩn/hiện thành phần giao diện: GET công khai, PUT chỉ admin, thành phần an toàn bị khoá."""

import re
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.dependencies import require_coordination_admin
from src.api.endpoints.ui_visibility import LOCKED_UI_KEYS
from src.db.dependencies import get_db_session
from src.main import app
from src.models.ui_visibility import UiVisibility

REGISTRY = Path(__file__).resolve().parents[2] / "frontend/src/features/uiVisibility/registry.ts"


class FakeDb:
    """Bảng ui_visibility trong bộ nhớ, đủ cho get/add/execute(select hidden)."""

    def __init__(self, rows: dict[str, bool] | None = None):
        self.rows = {key: UiVisibility(key=key, visible=visible) for key, visible in (rows or {}).items()}
        self.commit = AsyncMock()

    async def get(self, _model, key):
        return self.rows.get(key)

    def add(self, row):
        self.rows[row.key] = row

    async def execute(self, _statement):
        result = MagicMock()
        result.scalars.return_value = [key for key, row in self.rows.items() if row.visible is False]
        return result


@pytest.fixture
def fake_db():
    db = FakeDb({"landing.story": False, "header.sos": False, "global.footer": True})

    async def override():
        yield db

    previous = app.dependency_overrides.get(get_db_session)
    app.dependency_overrides[get_db_session] = override
    yield db
    if previous is None:
        app.dependency_overrides.pop(get_db_session, None)
    else:
        app.dependency_overrides[get_db_session] = previous


@pytest.fixture
def as_admin():
    app.dependency_overrides[require_coordination_admin] = lambda: SimpleNamespace(id=uuid.uuid4())
    yield
    app.dependency_overrides.pop(require_coordination_admin, None)


@pytest.mark.asyncio
async def test_get_is_public_and_never_reports_locked_keys(client, fake_db):
    response = await client.get("/api/v1/ui-visibility")
    assert response.status_code == 200
    # header.sos bị ẩn trong DB (vd. sửa tay) vẫn không được trả về → trang người dùng luôn hiện nút 115.
    assert response.json()["data"]["hidden"] == ["landing.story"]


@pytest.mark.asyncio
async def test_put_requires_authentication(client, fake_db):
    response = await client.put("/api/v1/ui-visibility/landing.cta", json={"visible": False})
    assert response.status_code in (401, 403)
    assert "landing.cta" not in fake_db.rows


@pytest.mark.asyncio
async def test_admin_can_hide_and_show(client, fake_db, as_admin):
    response = await client.put("/api/v1/ui-visibility/landing.cta", json={"visible": False})
    assert response.status_code == 200
    assert response.json()["data"]["hidden"] == ["landing.cta", "landing.story"]

    response = await client.put("/api/v1/ui-visibility/landing.story", json={"visible": True})
    assert response.json()["data"]["hidden"] == ["landing.cta"]
    assert fake_db.commit.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("key", sorted(LOCKED_UI_KEYS))
async def test_locked_safety_keys_cannot_be_hidden(client, fake_db, as_admin, key):
    response = await client.put(f"/api/v1/ui-visibility/{key}", json={"visible": False})
    assert response.status_code == 400
    fake_db.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["footer", "Landing.Story", "landing..story", "landing.story;drop", "a." + "b" * 130])
async def test_invalid_keys_rejected(client, fake_db, as_admin, key):
    response = await client.put(f"/api/v1/ui-visibility/{key}", json={"visible": False})
    assert response.status_code == 400
    fake_db.commit.assert_not_awaited()


def test_locked_keys_match_frontend_registry():
    source = REGISTRY.read_text(encoding="utf-8")
    locked = set(re.findall(r"\{ id: '([a-z0-9_.]+)'[^\n]*locked: true", source))
    assert locked == set(LOCKED_UI_KEYS)
