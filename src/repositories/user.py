"""User persistence operations."""

from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
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

    async def search_patients(
        self,
        *,
        query: str | None,
        status: str | None,
        gender: str | None,
        created_from: date | None,
        created_to: date | None,
        offset: int,
        limit: int,
    ) -> tuple[list[User], int]:
        """Search patient accounts and return a stable page with its total."""
        filters = [User.role == "patient"]
        if query:
            escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped_query}%"
            filters.append(User.full_name.ilike(pattern, escape="\\"))
        if status:
            filters.append(User.status == status)
        if gender:
            filters.append(User.gender == gender)
        if created_from:
            filters.append(
                User.created_at >= datetime.combine(created_from, time.min, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
            )
        if created_to:
            filters.append(
                User.created_at
                < datetime.combine(created_to + timedelta(days=1), time.min, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
            )

        total = int((await self.session.execute(select(func.count(User.id)).where(*filters))).scalar_one())
        statement = select(User).where(*filters).order_by(User.created_at.desc(), User.id).offset(offset).limit(limit)
        return list((await self.session.execute(statement)).scalars().all()), total

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

    async def get_by_citizen_id(self, citizen_id: str | None) -> User | None:
        """Find a user by citizen_id (CCCD)."""
        if not citizen_id:
            return None
        return (await self.session.execute(select(User).where(User.citizen_id == citizen_id))).scalar_one_or_none()

    async def get_by_health_insurance_code(self, health_insurance_code: str | None) -> User | None:
        """Find a user by health_insurance_code (BHYT)."""
        if not health_insurance_code:
            return None
        return (
            await self.session.execute(select(User).where(User.health_insurance_code == health_insurance_code))
        ).scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Persist a user and flush it so generated fields are available."""
        self.session.add(user)
        await self.session.flush()
        return user
