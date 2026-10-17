"""Provision verified coordinator accounts; credentials remain in Supabase Auth."""
import argparse
import asyncio
from sqlalchemy import select
from src.db.session import get_session_factory
from src.models.user import User
from src.models.workbench import CoordinatorMember


async def run(args):
    async with get_session_factory()() as db, db.begin():
        user = (await db.execute(select(User).where(User.email == args.email.strip().lower()).with_for_update())).scalar_one_or_none()
        if not user or user.status != 'active' or not user.auth_user_id:
            raise SystemExit('Account must exist, be active and linked to verified Supabase Auth.')
        member = await db.get(CoordinatorMember, user.id, with_for_update=True)
        if not member:
            member = CoordinatorMember(user_id=user.id)
            db.add(member)
        user.role = 'staff'
        member.enabled = not args.disable
        member.is_admin = args.admin
        member.facility_ids = args.facility
        member.clinical_qualification = args.qualification
    print('Coordinator membership saved. No passwords changed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', required=True)
    parser.add_argument('--qualification', required=True)
    parser.add_argument('--admin', action='store_true')
    parser.add_argument('--disable', action='store_true')
    parser.add_argument('--facility', action='append', default=[])
    args = parser.parse_args()
    from uuid import UUID
    for value in args.facility:
        UUID(value)
    asyncio.run(run(args))
