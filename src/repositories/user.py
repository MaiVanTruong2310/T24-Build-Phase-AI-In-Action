"""User persistence operations."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class UserRepository:
    """Repository for user lookup and persistence."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with an async database session."""
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Find a user by primary key."""
        return await self.session.get(User, user_id)

    async def get_by_identifier(self, email: str | None, phone: str | None) -> User | None:
        """Find a user by email, phone, or citizen_id."""
        if email:
            statement = select(User).where(User.email == email)
        elif phone:
            statement = select(User).where(or_(User.phone == phone, User.citizen_id == phone))
        else:
            return None
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_by_identity(self, email: str | None, phone: str | None) -> User | None:
        """Find a user matching either supplied identity field."""
        filters = [
            field for field in (User.email == email if email else None, User.phone == phone if phone else None) if field
        ]
        if not filters:
            return None
        return (await self.session.execute(select(User).where(or_(*filters)))).scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Persist a user and flush it so generated fields are available."""
        self.session.add(user)
        await self.session.flush()
        return user
