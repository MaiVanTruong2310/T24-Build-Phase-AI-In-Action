"""Unit tests for authentication business rules without a database."""

import asyncio
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from src.config import Settings, get_settings
from src.core.exceptions import AuthenticationError
from src.core.security import hash_refresh_token, verify_password
from src.models.auth import OtpChallenge, RefreshSession
from src.models.user import User
from src.schemas.auth import LoginRequest, RegisterRequest
from src.services.auth import AuthService
from src.services.otp import MockOtpProvider


class FakeTransaction:
    """Minimal async transaction context used by service unit tests."""

    async def __aenter__(self) -> "FakeTransaction":
        """Enter the fake transaction."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Leave the fake transaction without committing external state."""


class FakeSession:
    """Minimal async session surface required by AuthService."""

    def begin(self) -> FakeTransaction:
        """Return a fake transaction context manager."""
        return FakeTransaction()

    async def flush(self) -> None:
        """Match the async session flush operation."""


class FakeUserRepository:
    """In-memory user repository for isolated service tests."""

    def __init__(self) -> None:
        self.users: list[User] = []

    async def get_by_identity(self, email: str | None, phone: str | None) -> User | None:
        """Find a user by either identity field."""
        return next(
            (user for user in self.users if (email and user.email == email) or (phone and user.phone == phone)),
            None,
        )

    async def get_by_identifier(self, email: str | None, phone: str | None) -> User | None:
        """Find a user by one identity field."""
        return await self.get_by_identity(email, phone)

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Find a user by its identifier."""
        return next((user for user in self.users if user.id == user_id), None)

    async def create(self, user: User) -> User:
        """Store a user and assign its generated identifier."""
        if user.id is None:
            user.id = uuid4()
        self.users.append(user)
        return user


class FakeAuthRepository:
    """In-memory OTP and refresh-session repository for service tests."""

    def __init__(self) -> None:
        self.otp_challenges: list[OtpChallenge] = []
        self.refresh_sessions: list[RefreshSession] = []

    async def create_otp(self, challenge: OtpChallenge) -> OtpChallenge:
        """Store an OTP challenge with test-time defaults."""
        if challenge.id is None:
            challenge.id = uuid4()
        if challenge.created_at is None:
            challenge.created_at = datetime.now(UTC)
        if challenge.attempts is None:
            challenge.attempts = 0
        self.otp_challenges.append(challenge)
        return challenge

    async def get_latest_otp(
        self,
        target: str,
        purpose: str,
        *,
        for_update: bool = False,
    ) -> OtpChallenge | None:
        """Return the newest unconsumed OTP challenge."""
        del for_update
        values = [
            challenge
            for challenge in self.otp_challenges
            if challenge.target == target and challenge.purpose == purpose and challenge.consumed_at is None
        ]
        return max(values, key=lambda challenge: challenge.created_at) if values else None

    async def create_refresh_session(self, session: RefreshSession) -> RefreshSession:
        """Store a refresh session with a generated identifier."""
        if session.id is None:
            session.id = uuid4()
        self.refresh_sessions.append(session)
        return session

    async def get_refresh_session(self, token_hash: str, *, for_update: bool = False) -> RefreshSession | None:
        """Find a refresh session by its token hash."""
        del for_update
        return next((session for session in self.refresh_sessions if session.token_hash == token_hash), None)

    async def revoke_session(
        self,
        session_id: UUID,
        *,
        revoked_at: datetime,
        replaced_by: UUID | None = None,
    ) -> None:
        """Revoke one active refresh session."""
        session = next(session for session in self.refresh_sessions if session.id == session_id)
        if session.revoked_at is None:
            session.revoked_at = revoked_at
            session.last_used_at = revoked_at
            session.replaced_by = replaced_by

    async def revoke_user_sessions(self, user_id: UUID, *, revoked_at: datetime) -> None:
        """Revoke every active session belonging to a user."""
        for session in self.refresh_sessions:
            if session.user_id == user_id and session.revoked_at is None:
                session.revoked_at = revoked_at
                session.last_used_at = revoked_at

    async def list_user_sessions(self, user_id: UUID) -> list[RefreshSession]:
        """List sessions belonging to a user."""
        return [session for session in self.refresh_sessions if session.user_id == user_id]

    async def get_session_by_id(self, session_id: UUID, *, for_update: bool = False) -> RefreshSession | None:
        """Find a session by identifier."""
        del for_update
        return next((session for session in self.refresh_sessions if session.id == session_id), None)


def build_service(
    mock_otp_code: str = "123456",
) -> tuple[AuthService, FakeUserRepository, FakeAuthRepository, MockOtpProvider]:
    """Build an AuthService wired to in-memory dependencies."""
    settings = Settings(
        database_url="postgresql+psycopg://test:test@localhost/test",
        jwt_secret_key="test-secret-key-with-at-least-32-bytes",
        mock_otp_code=mock_otp_code,
    )
    provider = MockOtpProvider(settings)
    service = AuthService(FakeSession(), settings=settings, otp_provider=provider)
    users = FakeUserRepository()
    auth = FakeAuthRepository()
    service.users = users
    service.auth = auth
    return service, users, auth, provider


def configure_security_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure deterministic JWT settings for token-related tests."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes")
    get_settings.cache_clear()


def test_register_creates_pending_user_and_safe_log(caplog):
    """Registration creates a pending user and never logs the OTP value."""
    service, users, _, provider = build_service()

    with caplog.at_level("DEBUG"):
        user = asyncio.run(service.register(RegisterRequest(email=" User@Example.com ", password="correct-password")))

    assert user.email == "user@example.com"
    assert user.status == "pending_verification"
    assert provider.sent_codes[("user@example.com", "register")] == "123456"
    assert users.users == [user]
    assert "AuthService.register account created" in caplog.text
    assert "123456" not in caplog.text


def test_register_persists_patient_personal_information():
    """Registration stores optional demographic and healthcare identifiers."""
    service, _, _, _ = build_service()
    user = asyncio.run(
        service.register(
            RegisterRequest(
                email="user@example.com",
                password="correct-password",
                date_of_birth=date(1990, 5, 20),
                gender="female",
                citizen_id="012345678901",
                health_insurance_code="BH1234567890",
            )
        )
    )

    assert user.date_of_birth == date(1990, 5, 20)
    assert user.gender == "female"
    assert user.citizen_id == "012345678901"
    assert user.health_insurance_code == "BH1234567890"


def test_send_otp_returns_mock_code_for_existing_user():
    """OTP sending returns the mock code without writing it to the logs."""
    service, _, _, _ = build_service()
    asyncio.run(service.register(RegisterRequest(email="user@example.com", password="correct-password")))

    code = asyncio.run(service.send_otp("user@example.com", None, "login"))

    assert code == "123456"


def test_send_otp_generates_random_six_digit_code_when_not_configured():
    """The default mock provider generates a six-digit numeric OTP."""
    service, _, _, _ = build_service(mock_otp_code="")
    asyncio.run(service.register(RegisterRequest(email="user@example.com", password="correct-password")))

    code = asyncio.run(service.send_otp("user@example.com", None, "login"))

    assert code is not None
    assert len(code) == 6
    assert code.isdigit()


def test_password_reset_request_returns_mock_otp_for_existing_account():
    """An existing account receives a reset OTP with the dedicated purpose."""
    service, _, auth, _ = build_service()
    user = asyncio.run(service.register(RegisterRequest(email="user@example.com", password="old-password")))
    user.status = "active"

    code = asyncio.run(service.request_password_reset("user@example.com", None))

    assert code == "123456"
    assert auth.otp_challenges[-1].purpose == "reset_password"


def test_password_reset_request_hides_unknown_account():
    """An unknown account gets the same empty result without an OTP challenge."""
    service, _, auth, _ = build_service()

    code = asyncio.run(service.request_password_reset("missing@example.com", None))

    assert code is None
    assert auth.otp_challenges == []


def test_reset_password_changes_hash_and_revokes_sessions():
    """A valid reset OTP changes the password and revokes active sessions."""
    service, _, auth, _ = build_service()
    user = asyncio.run(service.register(RegisterRequest(email="user@example.com", password="old-password")))
    user.status = "active"
    session = RefreshSession(
        user_id=user.id,
        token_hash=hash_refresh_token("refresh-token-for-test"),
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    asyncio.run(auth.create_refresh_session(session))
    asyncio.run(service.request_password_reset("user@example.com", None))

    asyncio.run(service.reset_password("user@example.com", None, "123456", "new-password"))

    assert user.password_hash is not None
    assert verify_password("new-password", user.password_hash)
    assert not verify_password("old-password", user.password_hash)
    assert session.revoked_at is not None


def test_verify_registration_otp_persists_failed_attempt_and_activates_user():
    """An invalid OTP increments attempts before a valid OTP activates the user."""
    service, _, auth, _ = build_service()
    asyncio.run(service.register(RegisterRequest(email="user@example.com", password="correct-password")))

    with pytest.raises(AuthenticationError) as error:
        asyncio.run(service.verify_registration_otp("user@example.com", None, "000000"))

    assert error.value.code == "INVALID_OTP"
    assert auth.otp_challenges[0].attempts == 1
    assert auth.otp_challenges[0].consumed_at is None

    user = asyncio.run(service.verify_registration_otp("user@example.com", None, "123456"))

    assert user.status == "active"
    assert user.verified_at is not None
    assert auth.otp_challenges[0].consumed_at is not None


def test_login_issues_refresh_session_and_refresh_rotation(monkeypatch):
    """Password login issues tokens and rotating a token revokes the original session."""
    configure_security_environment(monkeypatch)
    service, _, auth, _ = build_service()
    user = asyncio.run(service.register(RegisterRequest(email="user@example.com", password="correct-password")))
    user.status = "active"

    try:
        _, access_token, refresh_token, _, _ = asyncio.run(
            service.login(LoginRequest(email="user@example.com", password="correct-password"))
        )
        _, rotated_access_token, rotated_refresh_token, _ = asyncio.run(service.refresh(refresh_token))

        assert access_token
        assert rotated_access_token
        assert refresh_token != rotated_refresh_token
        assert len(auth.refresh_sessions) == 2
        assert auth.refresh_sessions[0].revoked_at is not None

        with pytest.raises(AuthenticationError) as error:
            asyncio.run(service.refresh(refresh_token))
        assert error.value.code == "REFRESH_TOKEN_REUSE"
        assert all(session.revoked_at is not None for session in auth.refresh_sessions)
    finally:
        get_settings.cache_clear()


def test_expired_refresh_token_is_rejected(monkeypatch):
    """An expired refresh session is revoked and rejected."""
    configure_security_environment(monkeypatch)
    service, _, auth, _ = build_service()
    user = asyncio.run(service.register(RegisterRequest(email="user@example.com", password="correct-password")))
    user.status = "active"

    try:
        _, _, refresh_token, _, _ = asyncio.run(
            service.login(LoginRequest(email="user@example.com", password="correct-password"))
        )
        auth.refresh_sessions[0].expires_at = datetime.now(UTC) - timedelta(seconds=1)

        with pytest.raises(AuthenticationError) as error:
            asyncio.run(service.refresh(refresh_token))

        assert error.value.code == "REFRESH_TOKEN_EXPIRED"
        assert auth.refresh_sessions[0].revoked_at is not None
    finally:
        get_settings.cache_clear()


def test_logout_revokes_session_by_refresh_token():
    """Logout revokes the session without requiring an access-token user lookup."""
    service, _, auth, _ = build_service()
    user = asyncio.run(service.register(RegisterRequest(email="user@example.com", password="correct-password")))
    user.status = "active"

    try:
        _, _, refresh_token, _, _ = asyncio.run(
            service.login(LoginRequest(email="user@example.com", password="correct-password"))
        )

        asyncio.run(service.logout(refresh_token))

        assert auth.refresh_sessions[0].revoked_at is not None
    finally:
        get_settings.cache_clear()
