"""Authentication request and response schemas."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RegisterRequest(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=320)
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=200)
    date_of_birth: date | None = None
    gender: Literal["male", "female", "other", "unspecified"] | None = None
    citizen_id: str | None = Field(default=None, pattern=r"^\d{12}$")
    health_insurance_code: str | None = Field(default=None, min_length=1, max_length=32)

    @model_validator(mode="after")
    def validate_identity(self) -> "RegisterRequest":
        """Require at least one account identity during registration."""
        if not self.email and not self.phone:
            raise ValueError("email or phone is required")
        if self.date_of_birth and self.date_of_birth >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return self


class OtpSendRequest(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=320)
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    purpose: Literal["register", "login", "reset_password"] = "register"

    @model_validator(mode="after")
    def validate_target(self) -> "OtpSendRequest":
        """Require an email or phone target for OTP delivery."""
        if not self.email and not self.phone:
            raise ValueError("email or phone is required")
        return self


class OtpVerifyRequest(OtpSendRequest):
    code: str = Field(min_length=6, max_length=6)


class OtpSendResponse(BaseModel):
    """Return the OTP only when the configured delivery provider is a mock."""

    otp: str | None = None


class ForgotPasswordRequest(BaseModel):
    """Identify the account that should receive a password-reset OTP."""

    email: str | None = Field(default=None, min_length=3, max_length=320)
    phone: str | None = Field(default=None, min_length=7, max_length=32)

    @model_validator(mode="after")
    def validate_identity(self) -> "ForgotPasswordRequest":
        """Require an email or phone without exposing account existence."""
        if not self.email and not self.phone:
            raise ValueError("email or phone is required")
        return self


class ResetPasswordRequest(BaseModel):
    """Verify a reset OTP and provide the replacement password."""

    email: str | None = Field(default=None, min_length=3, max_length=320)
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_identity(self) -> "ResetPasswordRequest":
        """Require an email or phone for password reset."""
        if not self.email and not self.phone:
            raise ValueError("email or phone is required")
        return self


class LoginRequest(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=320)
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    otp_code: str | None = Field(default=None, min_length=6, max_length=6)

    @model_validator(mode="after")
    def validate_login(self) -> "LoginRequest":
        """Require an identity and one supported authentication factor."""
        if not self.email and not self.phone:
            raise ValueError("email or phone is required")
        if not self.password and not self.otp_code:
            raise ValueError("password or otp_code is required")
        return self


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    phone: str | None
    role: str
    status: str
    full_name: str | None
    date_of_birth: date | None
    gender: str | None
    citizen_id: str | None
    health_insurance_code: str | None
    verified_at: datetime | None


class SessionResponse(BaseModel):
    id: str
    expires_at: datetime
    revoked_at: datetime | None


class UpdateProfileRequest(BaseModel):
    """Patient-editable profile fields."""

    full_name: str | None = Field(default=None, max_length=200)
    date_of_birth: date | None = None
    gender: Literal["male", "female", "other", "unspecified"] | None = None
    citizen_id: str | None = Field(default=None, pattern=r"^\d{12}$")
    health_insurance_code: str | None = Field(default=None, min_length=1, max_length=32)

    @model_validator(mode="after")
    def validate_date_of_birth(self) -> "UpdateProfileRequest":
        """Prevent a profile from containing a future birth date."""
        if self.date_of_birth and self.date_of_birth >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return self
