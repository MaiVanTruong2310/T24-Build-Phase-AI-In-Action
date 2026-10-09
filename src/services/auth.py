"""Application profile use cases.

Credentials, email confirmation and session tokens are owned by Supabase Auth
(``auth.users`` / ``auth.sessions``). This service only reads and writes the
application profile stored in ``public.users``.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger
from src.models.user import User
from src.repositories.user import UserRepository
from src.schemas.auth import UpdateProfileRequest

logger = get_logger(__name__)


class AuthService:
    """Application service for profile reads and updates."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with the request-scoped session."""
        self.session = session
        self.users = UserRepository(session)

    async def get_user_by_id(self, user_id: UUID) -> User:
        """Find a user for authorized staff lookup flows."""
        user = await self.users.get_by_id(user_id)
        if user is None:
            logger.info("AuthService.get_user_by_id user not found")
            raise NotFoundError("User not found")
        return user

    async def update_profile(self, user: User, request: UpdateProfileRequest) -> User:
        """Apply allowed profile changes and flush them in a transaction."""
        try:
            async with self.session.begin():
                # Serialize per-field edits to retain other saved details.
                await self.session.execute(select(User.id).where(User.id == user.id).with_for_update())
                updates = request.model_dump(exclude_unset=True)
                if "patient_details" in updates:
                    await self.session.refresh(user, attribute_names=["patient_details"])
                    updates["patient_details"] = {**(user.patient_details or {}), **(updates["patient_details"] or {})}
                if "full_name" in updates:
                    updates["full_name"] = updates["full_name"].strip() or None if updates["full_name"] else None
                if "citizen_id" in updates and updates["citizen_id"]:
                    existing_cid = await self.users.get_by_citizen_id(updates["citizen_id"])
                    if existing_cid and existing_cid.id != user.id:
                        raise ConflictError("CITIZEN_ID_EXISTS", "Số CCCD đã thuộc một hồ sơ khác trong hệ thống.")
                if "health_insurance_code" in updates and updates["health_insurance_code"]:
                    existing_bhyt = await self.users.get_by_health_insurance_code(updates["health_insurance_code"])
                    if existing_bhyt and existing_bhyt.id != user.id:
                        raise ConflictError(
                            "HEALTH_INSURANCE_EXISTS", "Số thẻ bảo hiểm y tế đã thuộc một hồ sơ khác trong hệ thống."
                        )
                for field, value in updates.items():
                    setattr(user, field, value)
                await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "PROFILE_CONFLICT", "Số điện thoại hoặc thông tin định danh đã thuộc hồ sơ khác."
            ) from exc
        logger.info("AuthService.update_profile profile updated")
        return user

    async def update_portrait(self, user: User, image: str | None) -> None:
        """Keep the bounded portrait private to this user's profile."""
        async with self.session.begin():
            await self.session.execute(select(User.id).where(User.id == user.id).with_for_update())
            await self.session.refresh(user, attribute_names=["patient_details"])
            details = dict(user.patient_details or {})
            if image is None:
                details.pop("portrait_image", None)
            else:
                details["portrait_image"] = image
            user.patient_details = details
            await self.session.flush()
