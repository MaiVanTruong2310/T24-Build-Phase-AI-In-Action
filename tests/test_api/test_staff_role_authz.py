"""Phân quyền role staff ở backend: không dựa vào việc giao diện đã ẩn trang.

- Điều phối viên bị thu hồi (enabled=false, role vẫn "staff") không gọi được API staff.
- Ghi danh mục chung (bác sĩ, cơ sở, chuyên khoa, dịch vụ) chỉ dành cho admin hệ thống.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.api.dependencies import get_current_user
from src.db.dependencies import get_db_session
from src.main import app


def _member(**values):
    return SimpleNamespace(**{"enabled": True, "is_admin": False, "facility_ids": [], **values})


@pytest.fixture
def staff_with_member():
    """Đăng nhập bằng một staff; trả về hàm đặt membership điều phối của người đó."""
    db = AsyncMock()

    async def override_db():
        yield db

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4(), role="staff", status="active")
    app.dependency_overrides[get_db_session] = override_db

    def set_member(member):
        db.get.return_value = member

    yield set_member
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


@pytest.mark.asyncio
@pytest.mark.parametrize("member", [None, _member(enabled=False), _member(enabled=False, is_admin=True)])
@pytest.mark.parametrize("path", ["/api/v1/staff/patients", "/api/v1/staff/bookings", "/api/v1/staff/doctors"])
async def test_revoked_or_missing_coordinator_cannot_call_staff_api(client, staff_with_member, member, path):
    staff_with_member(member)

    response = await client.get(path)

    assert response.status_code == 403


CATALOG_WRITES = [
    ("post", "/api/v1/staff/doctors"),
    ("patch", f"/api/v1/staff/doctors/{uuid4()}"),
    ("patch", f"/api/v1/staff/doctors/{uuid4()}/toggle-booking?enabled=false"),
    ("post", "/api/v1/staff/facilities"),
    ("patch", f"/api/v1/staff/facilities/{uuid4()}"),
    ("post", "/api/v1/staff/specialties"),
    ("patch", f"/api/v1/staff/specialties/{uuid4()}"),
    ("post", "/api/v1/staff/services"),
    ("patch", f"/api/v1/staff/services/{uuid4()}"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("member", [_member(), _member(is_admin=True, facility_ids=[str(uuid4())])])
@pytest.mark.parametrize(("method", "path"), CATALOG_WRITES)
async def test_catalog_writes_require_system_admin(client, staff_with_member, member, method, path):
    """Điều phối viên thường hoặc admin chỉ một cơ sở không sửa được danh mục chung."""
    staff_with_member(member)

    response = await getattr(client, method)(path, json={})

    assert response.status_code == 403
