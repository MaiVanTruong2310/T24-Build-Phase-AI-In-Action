"""Authentication use cases."""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.core.exceptions import AppError, AuthenticationError, ConflictError, NotFoundError, RateLimitError
from src.core.logging import get_logger, log_event
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
        log_event(
            logger,
            logging.INFO,
            "auth.register.start",
            description="Starting patient account registration and OTP challenge creation",
            identity_type="email" if request.email else "phone",
        )
        email, phone = _normalized_identity(request.email, request.phone)
        async with self.session.begin():
            if await self.users.get_by_identity(email, phone):
                log_event(
                    logger,
                    logging.WARNING,
                    "auth.register.conflict",
                    description="Registration was rejected because the account already exists",
                    reason="account_exists",
                )
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
        log_event(
            logger,
            logging.INFO,
            "auth.register.done",
            description="Patient account and registration challenge were created",
            user_id=str(user.id),
            role=user.role,
            status=user.status,
        )
        return user

    async def send_otp(self, email: str | None, phone: str | None, purpose: str) -> str | None:
        """Create and deliver an OTP, returning it only for the mock provider."""
        log_event(
            logger,
            logging.INFO,
            "auth.otp.start",
            description="Starting OTP lookup, persistence, and delivery",
            purpose=purpose,
            identity_type="email" if email else "phone",
        )
        normalized_email, normalized_phone = _normalized_identity(email, phone)
        target = _target(normalized_email, normalized_phone)
        async with self.session.begin():
            user = await self.users.get_by_identifier(normalized_email, normalized_phone)
            if user is None:
                log_event(
                    logger,
                    logging.WARNING,
                    "auth.otp.error",
                    description="OTP was not created because the identity was not found",
                    purpose=purpose,
                    error_type="identity_not_found",
                )
                raise AuthenticationError("INVALID_CREDENTIALS", "Unable to send OTP")
            mock_code = await self._create_otp(user, target, purpose)
        log_event(
            logger,
            logging.INFO,
            "auth.otp.created",
            description="An OTP challenge was created and handed to the configured provider",
            user_id=str(user.id),
            purpose=purpose,
            mock_code_returned=mock_code is not None,
        )
        return mock_code

    async def request_password_reset(self, email: str | None, phone: str | None) -> str | None:
        """Issue a reset OTP without revealing whether the account exists."""
        log_event(
            logger,
            logging.INFO,
            "auth.password_reset.start",
            description="Starting password reset identity lookup and OTP creation",
            identity_type="email" if email else "phone",
        )
        normalized_email, normalized_phone = _normalized_identity(email, phone)
        target = _target(normalized_email, normalized_phone)
        async with self.session.begin():
            user = await self.users.get_by_identifier(normalized_email, normalized_phone)
            if user is None:
                log_event(
                    logger,
                    logging.INFO,
                    "auth.password_reset.skipped",
                    description="Password reset returned a generic response for an unknown identity",
                    reason="identity_not_found",
                )
                return None
            mock_code = await self._create_otp(user, target, "reset_password")
        log_event(
            logger,
            logging.INFO,
            "auth.password_reset.otp_created",
            description="Password reset OTP challenge was created",
            user_id=str(user.id),
            mock_code_returned=mock_code is not None,
        )
        return mock_code

    async def reset_password(self, email: str | None, phone: str | None, code: str, new_password: str) -> None:
        """Consume a reset OTP, replace the password hash and revoke sessions."""
        log_event(
            logger,
            logging.INFO,
            "auth.password_reset.start",
            description="Starting OTP verification and password update",
            identity_type="email" if email else "phone",
        )
        normalized_email, normalized_phone = _normalized_identity(email, phone)
        target = _target(normalized_email, normalized_phone)
        verification_error: AuthenticationError | None = None
        async with self.session.begin():
            user = await self.users.get_by_identifier(normalized_email, normalized_phone)
            if user is None or user.status != "active":
                log_event(
                    logger,
                    logging.WARNING,
                    "auth.password_reset.error",
                    description="Password reset was rejected because the account is unavailable",
                    error_type="account_unavailable",
                )
                raise AuthenticationError("INVALID_OTP", "Invalid or expired OTP")
            verification_error = await self._consume_otp(target, "reset_password", code)
            if verification_error is None:
                user.password_hash = hash_password(new_password)
                await self.auth.revoke_user_sessions(user.id, revoked_at=_now())
                await self.session.flush()
        if verification_error:
            raise verification_error
        log_event(logger, logging.INFO, "auth.password_reset.done", description="Password was updated and active sessions were revoked")

    async def verify_registration_otp(self, email: str | None, phone: str | None, code: str) -> User:
        """Consume a registration OTP and activate the matching account."""
        log_event(
            logger,
            logging.INFO,
            "auth.registration_verification.start",
            description="Starting registration OTP verification and account activation",
            identity_type="email" if email else "phone",
        )
        normalized_email, normalized_phone = _normalized_identity(email, phone)
        target = _target(normalized_email, normalized_phone)
        verification_error: AuthenticationError | None = None
        async with self.session.begin():
            user = await self.users.get_by_identifier(normalized_email, normalized_phone)
            if user is None:
                log_event(
                    logger,
                    logging.WARNING,
                    "auth.registration_verification.error",
                    description="Registration verification was rejected because the identity was not found",
                    error_type="identity_not_found",
                )
                raise AuthenticationError("INVALID_OTP", "Invalid or expired OTP")
            verification_error = await self._consume_otp(target, "register", code or "999999")
            if verification_error is None:
                now = _now()
                user.status = "active"
                user.verified_at = now
        if verification_error:
            raise verification_error
        log_event(
            logger,
            logging.INFO,
            "auth.registration_verification.done",
            description="Registration OTP was accepted and the account was activated",
            user_id=str(user.id),
            role=user.role,
        )
        return user

    async def login(self, request: LoginRequest) -> tuple[User, str, str, datetime, datetime]:
        """Authenticate with a password or OTP and issue access and refresh tokens."""
        log_event(
            logger,
            logging.INFO,
            "auth.login.start",
            description="Starting credential or OTP authentication",
            identity_type="email" if request.email else "phone",
            method="password" if request.password else "otp",
        )
        email, phone = _normalized_identity(request.email, request.phone)
        authentication_error: AuthenticationError | None = None
        result: tuple[User, str, str, datetime, datetime] | None = None
        async with self.session.begin():
            user = await self.users.get_by_identifier(email, phone)
            if user is None or user.status != "active":
                log_event(
                    logger,
                    logging.WARNING,
                    "auth.login.failed",
                    description="Login was rejected because the account is unavailable",
                    reason="account_unavailable",
                )
                raise AuthenticationError("INVALID_CREDENTIALS", "Invalid login credentials")
            if request.password:
                if not user.password_hash or not verify_password(request.password, user.password_hash):
                    log_event(
                        logger,
                        logging.WARNING,
                        "auth.login.failed",
                        description="Login was rejected because the supplied password was invalid",
                        reason="invalid_password",
                    )
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
        log_event(
            logger,
            logging.INFO,
            "auth.login.done",
            description="Credentials were accepted and a new session was issued",
            user_id=str(result[0].id),
            role=result[0].role,
        )
        return result

    async def refresh(self, refresh_token: str) -> tuple[User, str, str, datetime]:
        """Rotate a refresh token and reject reuse of revoked sessions."""
        log_event(
            logger,
            logging.INFO,
            "auth.refresh.start",
            description="Starting refresh-token validation and rotation",
        )
        now = _now()
        reuse_detected = False
        result: tuple[User, str, str, datetime] | None = None
        async with self.session.begin():
            stored = await self.auth.get_refresh_session(hash_refresh_token(refresh_token), for_update=True)
            if stored is None:
                log_event(
                    logger,
                    logging.WARNING,
                    "auth.refresh.failed",
                    description="Refresh failed because the token was not recognized",
                    reason="invalid_token",
                )
                raise AuthenticationError("INVALID_REFRESH_TOKEN", "Invalid refresh token")
            user = await self.users.get_by_id(stored.user_id)
            if user is None:
                log_event(
                    logger,
                    logging.WARNING,
                    "auth.refresh.failed",
                    description="Refresh failed because the token owner was not found",
                    reason="user_not_found",
                )
                raise AuthenticationError("INVALID_REFRESH_TOKEN", "Invalid refresh token")
            if stored.revoked_at is not None:
                await self.auth.revoke_user_sessions(user.id, revoked_at=now)
                reuse_detected = True
                log_event(
                    logger,
                    logging.WARNING,
                    "auth.refresh.failed",
                    description="Refresh token reuse was detected and all user sessions were revoked",
                    user_id=str(user.id),
                    reason="token_reuse",
                )
            elif stored.expires_at <= now:
                await self.auth.revoke_session(stored.id, revoked_at=now)
                log_event(
                    logger,
                    logging.WARNING,
                    "auth.refresh.failed",
                    description="Refresh failed because the token had expired",
                    user_id=str(user.id),
                    reason="token_expired",
                )
            elif user.status != "active":
                log_event(
                    logger,
                    logging.WARNING,
                    "auth.refresh.failed",
                    description="Refresh failed because the account is inactive",
                    user_id=str(user.id),
                    reason="account_inactive",
                )
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
        log_event(
            logger,
            logging.INFO,
            "auth.refresh.done",
            description="Refresh token was rotated and a new access session was issued",
            user_id=str(result[0].id),
            role=result[0].role,
        )
        return result

    async def logout(self, refresh_token: str) -> None:
        """Revoke the refresh session represented by the supplied token."""
        log_event(logger, logging.INFO, "auth.logout.start", description="Starting refresh-session revocation")
        async with self.session.begin():
            stored = await self.auth.get_refresh_session(hash_refresh_token(refresh_token), for_update=True)
            if stored is None:
                log_event(
                    logger,
                    logging.DEBUG,
                    "auth.logout.skipped",
                    description="Logout found no active session to revoke",
                    reason="session_not_found",
                )
                return
            await self.auth.revoke_session(stored.id, revoked_at=_now())
        log_event(logger, logging.INFO, "auth.logout.done", description="Refresh session was revoked during logout")

    async def list_sessions(self, user_id: UUID) -> list[RefreshSession]:
        """Return refresh sessions belonging to the current user."""
        log_event(
            logger,
            logging.INFO,
            "auth.sessions.list.start",
            description="Starting active session lookup for the user",
            user_id=str(user_id),
        )
        values = await self.auth.list_user_sessions(user_id)
        log_event(
            logger,
            logging.INFO,
            "auth.sessions.list.done",
            description="Active sessions were listed for the authenticated user",
            user_id=str(user_id),
            count=len(values),
        )
        return values

    async def revoke_session(self, user_id: UUID, session_id: str) -> None:
        """Revoke one refresh session after validating ownership."""
        log_event(
            logger,
            logging.INFO,
            "auth.session_revoke.start",
            description="Starting ownership validation and refresh-session revocation",
            user_id=str(user_id),
            session_id=session_id,
        )
        try:
            parsed_session_id = UUID(session_id)
        except ValueError as exc:
            log_event(
                logger,
                logging.WARNING,
                "auth.session_revoke.failed",
                description="Session revoke was rejected because the session ID was invalid",
                user_id=str(user_id),
                reason="invalid_session_id",
            )
            raise AppError("SESSION_NOT_FOUND", "Session not found", 404) from exc
        async with self.session.begin():
            stored = await self.auth.get_session_by_id(parsed_session_id, for_update=True)
            if stored is None or stored.user_id != user_id:
                log_event(
                    logger,
                    logging.WARNING,
                    "auth.session_revoke.failed",
                    description="Session revoke was rejected because the session was not owned by the user",
                    user_id=str(user_id),
                    reason="session_not_found",
                )
                raise AppError("SESSION_NOT_FOUND", "Session not found", 404)
            await self.auth.revoke_session(stored.id, revoked_at=_now())
        log_event(
            logger,
            logging.INFO,
            "auth.session_revoke.done",
            description="A user refresh session was revoked",
            user_id=str(user_id),
            session_id=str(parsed_session_id),
        )

    async def get_user_by_id(self, user_id: UUID) -> User:
        """Find a user for authorized staff lookup flows."""
        log_event(
            logger,
            logging.INFO,
            "auth.user.get.start",
            description="Starting user account lookup",
            user_id=str(user_id),
        )
        user = await self.users.get_by_id(user_id)
        if user is None:
            log_event(
                logger,
                logging.WARNING,
                "auth.user.get.not_found",
                description="User lookup returned no matching account",
                user_id=str(user_id),
            )
            raise NotFoundError("User not found")
        log_event(logger, logging.INFO, "auth.user.get.done", description="User account was loaded", user_id=str(user_id))
        return user

    async def list_patients(self, search: str | None, offset: int, limit: int) -> list[User]:
        """Return patient identities for staff booking selection."""
        log_event(
            logger,
            logging.INFO,
            "auth.patient.list.start",
            description="Starting patient lookup for a staff workflow",
            offset=offset,
            limit=limit,
            search_provided=bool(search),
        )
        values = await self.users.list_patients(search, offset=offset, limit=limit)
        log_event(
            logger,
            logging.INFO,
            "auth.patient.list.done",
            description="Patient accounts were listed for a staff workflow",
            count=len(values),
        )
        return values

    async def update_profile(self, user: User, request: UpdateProfileRequest) -> User:
        """Apply allowed profile changes and flush them in a transaction."""
        log_event(
            logger,
            logging.INFO,
            "auth.profile_update.start",
            description="Starting allowed profile field update",
            user_id=str(user.id),
            field_count=len(request.model_dump(exclude_unset=True)),
        )
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
            log_event(
                logger,
                logging.ERROR,
                "auth.profile_update.error",
                description="Profile update failed because an identity field conflicted",
                user_id=str(user.id),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            raise ConflictError(
                "PROFILE_CONFLICT", "Số điện thoại hoặc thông tin định danh đã thuộc hồ sơ khác."
            ) from exc
        log_event(
            logger,
            logging.INFO,
            "auth.profile_update.done",
            description="Allowed profile fields were updated",
            user_id=str(user.id),
        )
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
            log_event(
                logger,
                logging.WARNING,
                "auth.otp.rate_limited",
                description="OTP creation was rate limited for the identity",
                user_id=str(user.id),
                purpose=purpose,
            )
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
        log_event(
            logger,
            logging.DEBUG,
            "auth.otp.persisted",
            description="OTP challenge was persisted and delivery was requested",
            user_id=str(user.id),
            purpose=purpose,
        )
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
            log_event(
                logger,
                logging.WARNING,
                "auth.otp.rejected",
                description="OTP verification was rejected",
                purpose=purpose,
                error_code=error.code,
            )
        else:
            log_event(logger, logging.DEBUG, "auth.otp.consumed", description="OTP verification succeeded", purpose=purpose)
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
        log_event(
            logger,
            logging.DEBUG,
            "auth.token_session.created",
            description="A refresh-token session record was created",
            user_id=str(user.id),
            session_id=str(session.id),
            role=user.role,
        )
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
