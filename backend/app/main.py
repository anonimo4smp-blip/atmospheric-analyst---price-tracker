from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import api_router, internal_api_router
from app.core.config import get_settings
from app.db.init_db import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Endurece configuraciones inseguras en arranque.
    if settings.auth_cookie_samesite.strip().lower() == "none" and not settings.auth_cookie_secure:
        raise RuntimeError("AUTH_COOKIE_SAMESITE=none requiere AUTH_COOKIE_SECURE=true.")
    if settings.auth_login_max_attempts <= 0:
        raise RuntimeError("AUTH_LOGIN_MAX_ATTEMPTS debe ser mayor que 0.")
    if settings.auth_login_window_minutes <= 0:
        raise RuntimeError("AUTH_LOGIN_WINDOW_MINUTES debe ser mayor que 0.")
    if settings.auth_recovery_max_attempts <= 0:
        raise RuntimeError("AUTH_RECOVERY_MAX_ATTEMPTS debe ser mayor que 0.")
    if settings.auth_recovery_window_minutes <= 0:
        raise RuntimeError("AUTH_RECOVERY_WINDOW_MINUTES debe ser mayor que 0.")
    init_db()
    yield


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")

        if settings.security_hsts_enabled:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

allow_origins = [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]
if not allow_origins:
    allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.security_headers_enabled:
    app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api_router)
app.include_router(internal_api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
