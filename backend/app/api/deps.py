import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import ACCESS_COOKIE_NAME, CSRF_COOKIE_NAME
from app.db.models import User, UserSession
from app.db.session import get_db_session
from app.services.auth_service import get_user_and_session_from_access_token
from app.services.product_service import resolve_owner_user

settings = get_settings()
UNSAFE_HTTP_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def require_internal_api_key(x_internal_api_key: str = Header(default="")) -> None:
    expected_key = settings.internal_api_key
    if not expected_key or not secrets.compare_digest(x_internal_api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave interna invalida.",
        )


def get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for", "").strip()
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


def get_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _extract_access_token(request: Request, authorization: str | None) -> str | None:
    cookie_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    if authorization:
        prefix = "bearer "
        lowered = authorization.lower()
        if lowered.startswith(prefix):
            return authorization[len(prefix) :].strip()
    return None


def should_enforce_csrf(
    *,
    method: str,
    path: str,
    access_cookie_present: bool,
    csrf_enabled: bool,
) -> bool:
    if not csrf_enabled:
        return False
    if not access_cookie_present:
        return False
    if not path.startswith("/api"):
        return False
    return method.upper() in UNSAFE_HTTP_METHODS


def is_valid_csrf_pair(cookie_token: str | None, header_token: str | None) -> bool:
    if not cookie_token or not header_token:
        return False
    cookie_value = cookie_token.strip()
    header_value = header_token.strip()
    if not cookie_value or not header_value:
        return False
    return secrets.compare_digest(cookie_value, header_value)


def require_csrf_protection(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
) -> None:
    access_cookie = request.cookies.get(ACCESS_COOKIE_NAME)
    enforce = should_enforce_csrf(
        method=request.method,
        path=request.url.path,
        access_cookie_present=bool(access_cookie),
        csrf_enabled=settings.security_csrf_enabled,
    )
    if not enforce:
        return

    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    if not is_valid_csrf_pair(csrf_cookie, x_csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token invalido.",
        )


def get_optional_auth_context(
    request: Request,
    db: Session = Depends(get_db_session),
    authorization: str | None = Header(default=None),
) -> tuple[User, UserSession] | None:
    access_token = _extract_access_token(request, authorization)
    if not access_token:
        return None

    try:
        return get_user_and_session_from_access_token(db, access_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesion no valida.",
        ) from exc


def get_current_auth_context(
    auth_context: tuple[User, UserSession] | None = Depends(get_optional_auth_context),
) -> tuple[User, UserSession]:
    if not auth_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debes iniciar sesion.",
        )
    return auth_context


def get_current_user(auth_context: tuple[User, UserSession] = Depends(get_current_auth_context)) -> User:
    user, _ = auth_context
    return user


def get_current_session(
    auth_context: tuple[User, UserSession] = Depends(get_current_auth_context),
) -> UserSession:
    _, user_session = auth_context
    return user_session


def get_app_owner_user(
    db: Session = Depends(get_db_session),
    auth_context: tuple[User, UserSession] | None = Depends(get_optional_auth_context),
) -> User:
    if auth_context:
        user, _ = auth_context
        return user

    if settings.auth_require_login_for_app:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debes iniciar sesion.",
        )

    return resolve_owner_user(db, None)


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentSession = Annotated[UserSession, Depends(get_current_session)]
AppOwnerUser = Annotated[User, Depends(get_app_owner_user)]
