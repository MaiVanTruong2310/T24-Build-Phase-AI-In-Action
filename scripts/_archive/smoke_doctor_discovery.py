"""Read-only API smoke test for doctor discovery."""

import asyncio
from getpass import getpass
from pathlib import Path
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.main import app


async def main(password: str) -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        public = await client.get("/api/v1/doctors/facets")
        assert public.status_code == 200, f"anonymous doctor facets: {public.status_code}"
        private = await client.get("/api/v1/staff/doctors")
        assert private.status_code == 401, f"anonymous staff route: {private.status_code}"
        login = await client.post("/api/v1/auth/login", json={"username": "admin123", "password": password})
        assert login.status_code == 200, f"login: {login.status_code}"
        headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
        for route in ("/api/v1/doctors/facets", "/api/v1/doctors", "/api/v1/staff/doctors"):
            response = await client.get(route, headers=headers)
            assert response.status_code == 200, f"{route}: {response.status_code} {response.text[:300]}"
            print(route, "OK", len(response.json()["data"]))
        doctors = (await client.get("/api/v1/doctors", headers=headers)).json()["data"]
        if doctors:
            one = await client.get(f"/api/v1/doctors/{doctors[0]['id']}", headers=headers)
            assert one.status_code == 200, f"doctor detail: {one.status_code} {one.text[:300]}"
            assert all(key in one.json()["data"] for key in ("honors", "degrees", "languages", "facilities"))
            print("doctor detail OK")
            staff_one = await client.get(f"/api/v1/staff/doctors/{doctors[0]['id']}", headers=headers)
            assert staff_one.status_code == 200, f"staff detail: {staff_one.status_code} {staff_one.text[:300]}"
            print("staff edit detail OK")


if __name__ == "__main__":
    value = getpass("Coordinator password for read-only doctor smoke check: ")
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(value))
