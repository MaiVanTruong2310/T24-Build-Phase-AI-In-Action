"""Password, JWT and refresh-token security helpers.

.. warning::
   **No authentication path uses this module.** Supabase Auth owns credentials,
   email confirmation and sessions; every request is verified against
   ``SUPABASE_URL/auth/v1/user``. The helpers below are kept only so the
   regression tests can mint a locally signed token and prove that the
   application rejects it. Do not wire them back into a request path.
"""

import base64
import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from src.config import get_settings
from src.core.exceptions import AuthenticationError

_PASSWORD_SCHEME = "scrypt"
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def _encode(value: bytes) -> str:
    """Encode binary security material as URL-safe text."""
    return base64.urlsafe_b64encode(value).decode("ascii")


def hash_password(password: str) -> str:
    """Hash a password with salted scrypt using the Python standard library."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
    )
    return f"{_PASSWORD_SCHEME}${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_encode(salt)}${_encode(digest)}"


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password hash without revealing comparison timing."""
    try:
        scheme, n, r, p, salt_value, digest_value = encoded_hash.split("$", 5)
        if scheme != _PASSWORD_SCHEME:
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_value.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
        )
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def _secret_key() -> str:
    """Return the configured JWT secret or fail closed when it is absent."""
    secret = get_settings().jwt_secret_key
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY must be configured")
    return secret


def create_access_token(subject: str, role: str) -> tuple[str, datetime]:
    """Create a short-lived JWT access token."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=get_settings().jwt_access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "type": "access", "iat": now, "exp": expires_at}
    return jwt.encode(payload, _secret_key(), algorithm=get_settings().jwt_algorithm), expires_at


def create_refresh_token() -> tuple[str, datetime]:
    """Create an opaque refresh token and its expiry timestamp."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=get_settings().jwt_refresh_token_expire_days)
    return secrets.token_urlsafe(48), expires_at


def hash_refresh_token(token: str) -> str:
    """Hash an opaque refresh token before persistence."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token."""
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[get_settings().jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise AuthenticationError("INVALID_TOKEN", "Invalid or expired access token") from exc
    if payload.get("type") != "access" or not payload.get("sub"):
        raise AuthenticationError("INVALID_TOKEN", "Invalid access token")
    return payload
