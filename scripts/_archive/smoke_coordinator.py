"""Read-only API smoke check for the local coordinator login."""

import asyncio
from getpass import getpass
from pathlib import Path
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.main import app


async def main(password: str) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        login = await client.post("/api/v1/auth/login", json={"username": "admin123", "password": password})
        assert login.status_code == 200, f"login HTTP {login.status_code}: {login.text[:250]}"
        credentials = login.json()["data"]
        token = credentials["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        me = await client.get("/api/v1/users/me", headers=headers)
        assert me.status_code == 200 and me.json()["data"]["role"] == "staff", f"profile HTTP {me.status_code}"
        rules = await client.get("/api/v1/staff/coordination/rules", headers=headers)
        assert rules.status_code == 200, f"staff rules HTTP {rules.status_code}: {rules.text[:250]}"
        patient = await client.get("/api/v1/coordination/requests/mine", headers=headers)
        assert patient.status_code == 403, f"patient route HTTP {patient.status_code}"
        refresh = await client.post("/api/v1/auth/refresh-token", json={"refresh_token": credentials["refresh_token"]})
        assert refresh.status_code == 200, f"refresh HTTP {refresh.status_code}: {refresh.text[:250]}"
        fresh_headers = {"Authorization": f"Bearer {refresh.json()['data']['access_token']}"}
        refreshed_me = await client.get("/api/v1/users/me", headers=fresh_headers)
        assert refreshed_me.status_code == 200, f"refreshed profile HTTP {refreshed_me.status_code}"
        print("Coordinator login, refresh, staff access and patient role boundary: OK")


if __name__ == "__main__":
    password = getpass("Coordinator password for smoke check: ")
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(password))
