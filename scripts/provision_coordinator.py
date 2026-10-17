"""Provision the requested local staff login in the configured auth database.

Run from the project root: python scripts/provision_coordinator.py
The password is read without echo and never stored in this script or logs.
"""

import asyncio
from getpass import getpass
from pathlib import Path
import sys

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.security import hash_password
from src.db.session import get_auth_session_factory
from src.models.user import User


import argparse

async def provision(username: str, password: str, full_name: str = "Điều phối viên") -> None:
    async with get_auth_session_factory()() as db:
        async with db.begin():
            user = (await db.execute(select(User).where(User.phone == username).with_for_update())).scalar_one_or_none()
            if user is not None and user.role != "staff":
                raise RuntimeError(f"The username {username} is already assigned to a non-staff account")
            if user is None:
                user = User(phone=username, full_name=full_name, role="staff", status="active")
                db.add(user)
            user.password_hash = hash_password(password)
            user.status = "active"
    print(f"Coordinator account {username} is ready")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision local coordinator account")
    parser.add_argument("--username", "-u", default="admin123", help="Coordinator username (default: admin123)")
    parser.add_argument("--name", "-n", default="Điều phối viên", help="Full name for coordinator")
    args = parser.parse_args()

    value = getpass(f"Password for {args.username}: ")
    if len(value) < 8:
        raise SystemExit("Password must contain at least 8 characters")
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(provision(args.username, value, args.name))
