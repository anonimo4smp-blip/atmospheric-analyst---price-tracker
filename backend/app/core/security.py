from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from app.core.config import get_settings

settings = get_settings()
password_hasher = PasswordHasher()

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def hash_opaque_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: int, session_id: int) -> tuple[str, datetime]:
    issued_at = _now_utc()
    expires_at = issued_at + timedelta(minutes=settings.auth_access_token_ttl_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sid": str(session_id),
        "typ": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)
    return token, expires_at


def decode_access_token(access_token: str) -> dict[str, Any]:
    payload = jwt.decode(
        access_token,
        settings.auth_jwt_secret,
        algorithms=[settings.auth_jwt_algorithm],
    )
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("Tipo de token invalido.")
    return payload


def refresh_token_expiration() -> datetime:
    return _now_utc() + timedelta(days=settings.auth_refresh_token_ttl_days)


def email_verification_expiration() -> datetime:
    return _now_utc() + timedelta(hours=settings.auth_email_token_ttl_hours)


def password_reset_expiration() -> datetime:
    return _now_utc() + timedelta(minutes=settings.auth_password_reset_ttl_minutes)


def cookie_max_age_seconds(expires_at: datetime) -> int:
    delta = expires_at - _now_utc()
    return max(1, int(delta.total_seconds()))


def cookie_samesite_value() -> str:
    raw = settings.auth_cookie_samesite.strip().lower()
    if raw in {"lax", "strict", "none"}:
        return raw
    return "lax"
