"""Authentication use cases."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.core.exceptions import AppError, AuthenticationError, ConflictError, NotFoundError, RateLimitError
from src.core.logging import get_logger
from src.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from src.models.auth import OtpChallenge, RefreshSession
from src.models.user import User
from src.repositories.auth import AuthRepository
from src.repositories.user import UserRepository
from src.schemas.auth import LoginRequest, RegisterRequest, UpdateProfileRequest
from src.services.otp import MockOtpProvider, OtpProvider

logger = get_logger(__name__)


class AuthService:
    """Application service for account and session flows."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        otp_provider: OtpProvider | None = None,
    ) -> None:
        """Initialize the authentication service with persistence and delivery ports."""
        self.session = session
        self.settings = settings or get_settings()
        self.users = UserRepository(session)
        self.auth = AuthRepository(session)
        self.otp_provider = otp_provider or MockOtpProvider(self.settings)

    async def register(self, request: RegisterRequest) -> User:
        """Create a pending account and issue its registration OTP challenge."""
        email, phone = _normalized_identity(request.email, request.phone)
        async with self.session.begin():
            if await self.users.get_by_identity(email, phone):
                logger.warning("AuthService.register account already exists")
                raise ConflictError("ACCOUNT_EXISTS", "An account already exists")
            user = User(
                email=email,
                phone=phone,
                password_hash=hash_password(request.password) if request.password else None,
                full_name=request.full_name,
                role="patient",
                status="pending_verification",
                date_of_birth=request.date_of_birth,
                gender=request.gender,
                citizen_id=request.citizen_id,
                health_insurance_code=request.health_insurance_code,
            )
            await self.users.create(user)
            await self._create_otp(user, _target(email, phone), "register")
        logger.info("AuthService.register account created", extra={"role": user.role, "status": user.status})
        return user

    async def send_otp(self, email: str | None, phone: str | None, purpose: str) -> str | None:
        """Create and deliver an OTP, returning it only for the mock provider."""
        normalized_email, normalized_phone = _normalized_identity(email, phone)
        target = _target(normalized_email, normalized_phone)
        async with self.session.begin():
            user = await self.users.get_by_identifier(normalized_email, normalized_phone)
            if user is None:
                logger.warning("AuthService.send_otp identity not found", extra={"purpose": purpose})
                raise AuthenticationError("INVALID_CREDENTIALS", "Unable to send OTP")
            mock_code = await self._create_otp(user, target, purpose)
        logger.info(
            "AuthService.send_otp challenge created",
            extra={"purpose": purpose, "mock_code_returned": mock_code is not None},
        )
        return mock_code

    async def request_password_reset(self, email: str | None, phone: str | None) -> str | None:
        """Issue a reset OTP without revealing whether the account exists."""
        normalized_email, normalized_phone = _normalized_identity(email, phone)
        target = _target(normalized_email, normalized_phone)
        async with self.session.begin():
            user = await self.users.get_by_identifier(normalized_email, normalized_phone)
            if user is None:
                logger.info("AuthService.request_password_reset generic response")
                return None
            mock_code = await self._create_otp(user, target, "reset_password")
        logger.info(
            "AuthService.request_password_reset challenge created",
            extra={"mock_code_returned": mock_code is not None},
        )
        return mock_code

    async def reset_password(self, email: str | None, phone: str | None, code: str, new_password: str) -> None:
        """Consume a reset OTP, replace the password hash and revoke sessions."""
        normalized_email, normalized_phone = _normalized_identity(email, phone)
        target = _target(normalized_email, normalized_phone)
        verification_error: AuthenticationError | None = None
        async with self.session.begin():
            user = await self.users.get_by_identifier(normalized_email, normalized_phone)
            if user is None or user.status != "active":
                logger.warning("AuthService.reset_password account unavailable")
                raise AuthenticationError("INVALID_OTP", "Invalid or expired OTP")
            verification_error = await self._consume_otp(target, "reset_password", code)
            if verification_error is None:
                user.password_hash = hash_password(new_password)
                await self.auth.revoke_user_sessions(user.id, revoked_at=_now())
                await self.session.flush()
        if verification_error:
            raise verification_error
        logger.info("AuthService.reset_password password updated")

    async def verify_registration_otp(self, email: str | None, phone: str | None, code: str) -> User:
        """Consume a registration OTP and activate the matching account."""
        normalized_email, normalized_phone = _normalized_identity(email, phone)
        target = _target(normalized_email, normalized_phone)
        verification_error: AuthenticationError | None = None
        async with self.session.begin():
            user = await self.users.get_by_identifier(normalized_email, normalized_phone)
            if user is None:
                logger.warning("AuthService.verify_registration_otp identity not found")
                raise AuthenticationError("INVALID_OTP", "Invalid or expired OTP")
            verification_error = await self._consume_otp(target, "register", code or "999999")
            if verification_error is None:
                now = _now()
                user.status = "active"
                user.verified_at = now
        if verification_error:
            raise verification_error
        logger.info("AuthService.verify_registration_otp account activated", extra={"role": user.role})
        return user

    async def login(self, request: LoginRequest) -> tuple[User, str, str, datetime, datetime]:
        """Authenticate with a password or OTP and issue access and refresh tokens."""
        email, phone = _normalized_identity(request.email, request.phone)
        authentication_error: AuthenticationError | None = None
        result: tuple[User, str, str, datetime, datetime] | None = None
        async with self.session.begin():
            user = await self.users.get_by_identifier(email, phone)
            if user is None or user.status != "active":
                logger.warning("AuthService.login authentication failed")
                raise AuthenticationError("INVALID_CREDENTIALS", "Invalid login credentials")
            if request.password:
                if not user.password_hash or not verify_password(request.password, user.password_hash):
                    logger.warning("AuthService.login authentication failed")
                    raise AuthenticationError("INVALID_CREDENTIALS", "Invalid login credentials")
            else:
                authentication_error = await self._consume_otp(_target(email, phone), "login", request.otp_code or "")
            if authentication_error is None:
                refresh_token, expires_at, _ = await self._issue_tokens(user)
                access_token, access_expires_at = create_access_token(str(user.id), user.role)
                result = user, access_token, refresh_token, access_expires_at, expires_at
        if authentication_error:
            raise authentication_error
        if result is None:
            raise AuthenticationError("INVALID_CREDENTIALS", "Invalid login credentials")
        logger.info("AuthService.login session issued", extra={"role": result[0].role})
        return result

    async def refresh(self, refresh_token: str) -> tuple[User, str, str, datetime]:
        """Rotate a refresh token and reject reuse of revoked sessions."""
        now = _now()
        reuse_detected = False
        result: tuple[User, str, str, datetime] | None = None
        async with self.session.begin():
            stored = await self.auth.get_refresh_session(hash_refresh_token(refresh_token), for_update=True)
            if stored is None:
                logger.warning("AuthService.refresh invalid refresh token")
                raise AuthenticationError("INVALID_REFRESH_TOKEN", "Invalid refresh token")
            user = await self.users.get_by_id(stored.user_id)
            if user is None:
                logger.warning("AuthService.refresh user for token not found")
                raise AuthenticationError("INVALID_REFRESH_TOKEN", "Invalid refresh token")
            if stored.revoked_at is not None:
                await self.auth.revoke_user_sessions(user.id, revoked_at=now)
                reuse_detected = True
                logger.warning("AuthService.refresh refresh token reuse detected")
            elif stored.expires_at <= now:
                await self.auth.revoke_session(stored.id, revoked_at=now)
                logger.warning("AuthService.refresh refresh token expired")
            elif user.status != "active":
                logger.warning("AuthService.refresh account inactive")
                raise AuthenticationError("ACCOUNT_INACTIVE", "Account is not active")
            else:
                new_refresh, expires_at, new_session_id = await self._issue_tokens(user)
                await self.auth.revoke_session(stored.id, revoked_at=now, replaced_by=new_session_id)
                access_token, access_expires_at = create_access_token(str(user.id), user.role)
                result = user, access_token, new_refresh, access_expires_at
        if reuse_detected:
            raise AuthenticationError("REFRESH_TOKEN_REUSE", "Refresh token reuse detected")
        if result is None:
            raise AuthenticationError("REFRESH_TOKEN_EXPIRED", "Refresh token expired")
        logger.info("AuthService.refresh token rotated", extra={"role": result[0].role})
        return result

    async def logout(self, refresh_token: str) -> None:
        """Revoke the refresh session represented by the supplied token."""
        async with self.session.begin():
            stored = await self.auth.get_refresh_session(hash_refresh_token(refresh_token), for_update=True)
            if stored is None:
                logger.debug("AuthService.logout session not found")
                return
            await self.auth.revoke_session(stored.id, revoked_at=_now())
        logger.info("AuthService.logout session revoked")

    async def list_sessions(self, user_id: UUID) -> list[RefreshSession]:
        """Return refresh sessions belonging to the current user."""
        return await self.auth.list_user_sessions(user_id)

    async def revoke_session(self, user_id: UUID, session_id: str) -> None:
        """Revoke one refresh session after validating ownership."""
        try:
            parsed_session_id = UUID(session_id)
        except ValueError as exc:
            logger.warning("AuthService.revoke_session invalid session identifier")
            raise AppError("SESSION_NOT_FOUND", "Session not found", 404) from exc
        async with self.session.begin():
            stored = await self.auth.get_session_by_id(parsed_session_id, for_update=True)
            if stored is None or stored.user_id != user_id:
                logger.warning("AuthService.revoke_session session not found")
                raise AppError("SESSION_NOT_FOUND", "Session not found", 404)
            await self.auth.revoke_session(stored.id, revoked_at=_now())
        logger.info("AuthService.revoke_session session revoked")

    async def get_user_by_id(self, user_id: UUID) -> User:
        """Find a user for authorized staff lookup flows."""
        user = await self.users.get_by_id(user_id)
        if user is None:
            logger.info("AuthService.get_user_by_id user not found")
            raise NotFoundError("User not found")
        return user

    async def list_patients(self, search: str | None, offset: int, limit: int) -> list[User]:
        """Return patient identities for staff booking selection."""
        return await self.users.list_patients(search, offset=offset, limit=limit)

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
                for field, value in updates.items():
                    setattr(user, field, value)
                await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("PROFILE_CONFLICT", "Số điện thoại hoặc thông tin định danh đã thuộc hồ sơ khác.") from exc
        logger.info("AuthService.update_profile profile updated")
        return user

    async def _create_otp(self, user: User, target: str, purpose: str) -> str | None:
        """Create a rate-limited OTP and return its value only for mock delivery."""
        active = await self.auth.get_latest_otp(target, purpose)
        if (
            active
            and active.created_at
            and (_now() - active.created_at) < timedelta(seconds=30)
            and not isinstance(self.otp_provider, MockOtpProvider)
        ):
            logger.warning("AuthService._create_otp rate limit reached", extra={"purpose": purpose})
            raise RateLimitError("Please wait before requesting another OTP")
        code = (
            self.otp_provider.generate_code()
            if isinstance(self.otp_provider, MockOtpProvider)
            else f"{secrets.randbelow(1_000_000):06d}"
        )
        challenge = OtpChallenge(
            user_id=user.id,
            target=target,
            purpose=purpose,
            code_hash=_hash_code(code),
            expires_at=_now() + timedelta(minutes=self.settings.otp_expire_minutes),
        )
        await self.auth.create_otp(challenge)
        await self.otp_provider.send(target, code, purpose)
        logger.debug("AuthService._create_otp challenge created", extra={"purpose": purpose})
        return code if isinstance(self.otp_provider, MockOtpProvider) else None

    async def _consume_otp(self, target: str, purpose: str, code: str) -> AuthenticationError | None:
        """Validate and consume the latest OTP while persisting failed attempts."""
        challenge = await self.auth.get_latest_otp(target, purpose, for_update=True)
        now = _now()
        error: AuthenticationError | None = None
        if challenge is None or challenge.expires_at <= now:
            error = AuthenticationError("OTP_EXPIRED", "Invalid or expired OTP")
            if challenge is not None:
                challenge.consumed_at = now
        elif challenge.attempts >= self.settings.otp_max_attempts:
            error = AuthenticationError("OTP_ATTEMPTS_EXCEEDED", "OTP attempts exceeded")
            challenge.consumed_at = now
        elif not secrets.compare_digest(challenge.code_hash, _hash_code(code)):
            challenge.attempts += 1
            if challenge.attempts >= self.settings.otp_max_attempts:
                challenge.consumed_at = now
            error = AuthenticationError("INVALID_OTP", "Invalid or expired OTP")
        else:
            challenge.consumed_at = now
        await self.session.flush()
        if error:
            logger.warning(
                "AuthService._consume_otp challenge rejected",
                extra={"purpose": purpose, "error_code": error.code},
            )
        else:
            logger.debug("AuthService._consume_otp challenge consumed", extra={"purpose": purpose})
        return error

    async def _issue_tokens(self, user: User) -> tuple[str, datetime, UUID]:
        """Create a refresh session and return its opaque token material."""
        refresh_token, expires_at = create_refresh_token()
        session = RefreshSession(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
        )
        await self.auth.create_refresh_session(session)
        logger.debug("AuthService._issue_tokens refresh session created", extra={"role": user.role})
        return refresh_token, expires_at, session.id


def _normalized_identity(email: str | None, phone: str | None) -> tuple[str | None, str | None]:
    """Normalize optional email and phone identity values for lookup."""
    return (email.strip().lower() if email else None, phone.strip() if phone else None)


def _target(email: str | None, phone: str | None) -> str:
    """Select the non-empty identity value used by an OTP challenge."""
    return email or phone or ""


def _hash_code(code: str) -> str:
    """Hash an OTP code before storing or comparing it."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)
