"""OTP challenge and refresh-session persistence operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.auth import OtpChallenge, RefreshSession


class AuthRepository:
    """Repository for authentication state."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session."""
        self.session = session

    async def create_otp(self, challenge: OtpChallenge) -> OtpChallenge:
        """Persist an OTP challenge and assign database-generated fields."""
        self.session.add(challenge)
        await self.session.flush()
        return challenge

    async def get_latest_otp(
        self,
        target: str,
        purpose: str,
        *,
        for_update: bool = False,
    ) -> OtpChallenge | None:
        """Find the newest unconsumed OTP for a target and purpose."""
        statement = (
            select(OtpChallenge)
            .where(
                OtpChallenge.target == target,
                OtpChallenge.purpose == purpose,
                OtpChallenge.consumed_at.is_(None),
            )
            .order_by(desc(OtpChallenge.created_at))
            .limit(1)
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def create_refresh_session(self, session: RefreshSession) -> RefreshSession:
        """Persist a refresh-token session."""
        self.session.add(session)
        await self.session.flush()
        return session

    async def get_refresh_session(self, token_hash: str, *, for_update: bool = False) -> RefreshSession | None:
        """Find a refresh session by its stored token hash."""
        statement = select(RefreshSession).where(RefreshSession.token_hash == token_hash)
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def revoke_session(
        self,
        session_id: UUID,
        *,
        revoked_at: datetime,
        replaced_by: UUID | None = None,
    ) -> None:
        """Revoke one active refresh session, optionally linking its replacement."""
        await self.session.execute(
            update(RefreshSession)
            .where(RefreshSession.id == session_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at, replaced_by=replaced_by, last_used_at=revoked_at)
        )

    async def revoke_user_sessions(self, user_id: UUID, *, revoked_at: datetime) -> None:
        """Revoke all active refresh sessions owned by a user."""
        await self.session.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at, last_used_at=revoked_at)
        )

    async def list_user_sessions(self, user_id: UUID) -> list[RefreshSession]:
        """List a user's refresh sessions from newest to oldest."""
        statement = (
            select(RefreshSession).where(RefreshSession.user_id == user_id).order_by(desc(RefreshSession.created_at))
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def get_session_by_id(self, session_id: UUID, *, for_update: bool = False) -> RefreshSession | None:
        """Find a refresh session by identifier, optionally locking the row."""
        statement = select(RefreshSession).where(RefreshSession.id == session_id)
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()
