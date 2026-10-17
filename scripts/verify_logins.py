"""Verify login and role resolution for newly deployed accounts."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import httpx
from src.config import get_settings
from src.main import app

TEST_USERS = [
    ("admin@vcare.vn", "Admin@123456", "staff"),
    ("coordinator@vcare.vn", "Coordinator@123456", "staff"),
    ("patient@vcare.vn", "Patient@123456", "patient"),
]


async def verify():
    settings = get_settings()
    token_url = settings.supabase_url.rstrip("/") + "/auth/v1/token?grant_type=password"
    headers = {"apikey": settings.supabase_key, "Content-Type": "application/json"}

    print("Verifying Supabase Auth & Application APIs...")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(timeout=20) as auth_client, httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=20) as app_client:
        for email, password, expected_role in TEST_USERS:
            # 1. Supabase Auth token
            resp = await auth_client.post(token_url, json={"email": email, "password": password}, headers=headers)
            assert resp.status_code == 200, f"Failed Supabase login for {email}: {resp.status_code} {resp.text}"
            access_token = resp.json()["access_token"]

            # 2. Application /users/me profile
            auth_headers = {"Authorization": f"Bearer {access_token}"}
            me_resp = await app_client.get("/api/v1/users/me", headers=auth_headers)
            assert me_resp.status_code == 200, f"Failed /users/me for {email}: {me_resp.status_code} {me_resp.text}"
            profile = me_resp.json()["data"]
            actual_role = profile["role"]
            assert actual_role == expected_role, f"Role mismatch for {email}: expected {expected_role}, got {actual_role}"

            print(f"  [PASSED] {email} -> role: {actual_role}, name: {profile.get('full_name')}")

    print("All account verifications passed successfully!")


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify())
