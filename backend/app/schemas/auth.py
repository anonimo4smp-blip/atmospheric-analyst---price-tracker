from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    new_password: str = Field(min_length=12, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_email_verified: bool
    is_active: bool
    created_at: datetime


class AuthMessageResponse(BaseModel):
    message: str
    debug_token: str | None = None


class LoginResponse(BaseModel):
    user: AuthUserResponse


class UserSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: str | None
    user_agent: str | None
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    is_current: bool = False


class UserSessionListResponse(BaseModel):
    sessions: list[UserSessionResponse]


class RevokeOtherSessionsResponse(BaseModel):
    message: str
    revoked_count: int
