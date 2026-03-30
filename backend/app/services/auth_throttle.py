from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import normalize_email
from app.db.models import AuthLoginAttempt

settings = get_settings()


@dataclass
class ThrottleDecision:
    allowed: bool
    retry_after_seconds: int = 0
    attempts_left: int = 0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _window_duration(window_minutes: int) -> timedelta:
    return timedelta(minutes=window_minutes)


def _window_end(window_started_at: datetime, window_minutes: int) -> datetime:
    return _as_utc(window_started_at) + _window_duration(window_minutes)


def _supports_row_locking(session: Session) -> bool:
    bind = session.get_bind()
    if not bind:
        return False
    return bind.dialect.name != "sqlite"


def _attempt_row_query(throttle_key: str, for_update: bool = False) -> Select[tuple[AuthLoginAttempt]]:
    statement = select(AuthLoginAttempt).where(AuthLoginAttempt.throttle_key == throttle_key)
    if for_update:
        statement = statement.with_for_update()
    return statement


def _get_attempt_row(session: Session, throttle_key: str, for_update: bool = False) -> AuthLoginAttempt | None:
    statement = _attempt_row_query(
        throttle_key=throttle_key,
        for_update=for_update and _supports_row_locking(session),
    )
    return session.scalar(statement)


def _normalize_window_if_expired(attempt: AuthLoginAttempt, now_utc: datetime) -> None:
    if _window_end(attempt.window_started_at, settings.auth_login_window_minutes) > _as_utc(now_utc):
        return
    attempt.failure_count = 0
    attempt.window_started_at = now_utc
    attempt.blocked_until = None


def _build_decision(
    attempt: AuthLoginAttempt | None,
    now_utc: datetime,
    max_attempts: int,
    window_minutes: int,
) -> ThrottleDecision:
    if not attempt:
        return ThrottleDecision(
            allowed=True,
            retry_after_seconds=0,
            attempts_left=max_attempts,
        )

    current_utc = _as_utc(now_utc)

    blocked_until = _as_utc(attempt.blocked_until) if attempt.blocked_until else None
    if blocked_until and blocked_until > current_utc:
        retry_after = max(1, int((blocked_until - current_utc).total_seconds()))
        return ThrottleDecision(allowed=False, retry_after_seconds=retry_after, attempts_left=0)

    remaining = max(0, max_attempts - attempt.failure_count)
    if attempt.failure_count >= max_attempts:
        retry_after = max(1, int((_window_end(attempt.window_started_at, window_minutes) - current_utc).total_seconds()))
        return ThrottleDecision(allowed=False, retry_after_seconds=retry_after, attempts_left=0)

    return ThrottleDecision(allowed=True, retry_after_seconds=0, attempts_left=remaining)


def _commit_or_raise(session: Session, error_message: str) -> None:
    try:
        session.commit()
    except Exception as exc:
        session.rollback()
        raise RuntimeError(error_message) from exc


def build_login_throttle_key(ip_address: str | None, email: str) -> str:
    normalized_ip = (ip_address or "unknown_ip").strip().lower()
    if not normalized_ip:
        normalized_ip = "unknown_ip"
    normalized_email = normalize_email(email)
    return f"{normalized_ip}|{normalized_email}"


def build_email_action_throttle_key(ip_address: str | None, email: str, action: str) -> str:
    normalized_ip = (ip_address or "unknown_ip").strip().lower()
    if not normalized_ip:
        normalized_ip = "unknown_ip"
    normalized_email = normalize_email(email)
    normalized_action = action.strip().lower() or "unknown_action"
    return f"{normalized_action}|{normalized_ip}|{normalized_email}"


def check_login_rate_limit(
    session: Session,
    throttle_key: str,
    now_utc: datetime | None = None,
) -> ThrottleDecision:
    now_utc = _as_utc(now_utc or _utcnow())
    attempt = _get_attempt_row(session, throttle_key, for_update=False)
    if not attempt:
        return _build_decision(
            None,
            now_utc,
            max_attempts=settings.auth_login_max_attempts,
            window_minutes=settings.auth_login_window_minutes,
        )

    _normalize_window_if_expired(attempt, now_utc)
    return _build_decision(
        attempt,
        now_utc,
        max_attempts=settings.auth_login_max_attempts,
        window_minutes=settings.auth_login_window_minutes,
    )


def register_login_failure(
    session: Session,
    throttle_key: str,
    now_utc: datetime | None = None,
) -> ThrottleDecision:
    now_utc = _as_utc(now_utc or _utcnow())
    attempt = _get_attempt_row(session, throttle_key, for_update=True)

    if not attempt:
        attempt = AuthLoginAttempt(
            throttle_key=throttle_key,
            failure_count=1,
            window_started_at=now_utc,
            last_attempt_at=now_utc,
            blocked_until=None,
        )
        session.add(attempt)
        _commit_or_raise(session, "No se pudo registrar el intento fallido de login.")
        session.refresh(attempt)
        return _build_decision(
            attempt,
            now_utc,
            max_attempts=settings.auth_login_max_attempts,
            window_minutes=settings.auth_login_window_minutes,
        )

    blocked_until = _as_utc(attempt.blocked_until) if attempt.blocked_until else None
    if blocked_until and blocked_until > now_utc:
        return _build_decision(
            attempt,
            now_utc,
            max_attempts=settings.auth_login_max_attempts,
            window_minutes=settings.auth_login_window_minutes,
        )

    if _window_end(attempt.window_started_at, settings.auth_login_window_minutes) <= now_utc:
        attempt.failure_count = 1
        attempt.window_started_at = now_utc
        attempt.blocked_until = None
    else:
        attempt.failure_count += 1

    attempt.last_attempt_at = now_utc
    if attempt.failure_count >= settings.auth_login_max_attempts:
        attempt.blocked_until = _window_end(attempt.window_started_at, settings.auth_login_window_minutes)

    _commit_or_raise(session, "No se pudo actualizar el contador de intentos de login.")
    session.refresh(attempt)
    return _build_decision(
        attempt,
        now_utc,
        max_attempts=settings.auth_login_max_attempts,
        window_minutes=settings.auth_login_window_minutes,
    )


def clear_login_failures(session: Session, throttle_key: str) -> None:
    attempt = _get_attempt_row(session, throttle_key, for_update=True)
    if not attempt:
        return
    session.delete(attempt)
    _commit_or_raise(session, "No se pudo limpiar el contador de intentos de login.")


def check_recovery_rate_limit(
    session: Session,
    throttle_key: str,
    now_utc: datetime | None = None,
) -> ThrottleDecision:
    now_utc = _as_utc(now_utc or _utcnow())
    attempt = _get_attempt_row(session, throttle_key, for_update=False)
    if not attempt:
        return _build_decision(
            None,
            now_utc,
            max_attempts=settings.auth_recovery_max_attempts,
            window_minutes=settings.auth_recovery_window_minutes,
        )

    if _window_end(attempt.window_started_at, settings.auth_recovery_window_minutes) <= now_utc:
        attempt.failure_count = 0
        attempt.window_started_at = now_utc
        attempt.blocked_until = None

    return _build_decision(
        attempt,
        now_utc,
        max_attempts=settings.auth_recovery_max_attempts,
        window_minutes=settings.auth_recovery_window_minutes,
    )


def register_recovery_attempt(
    session: Session,
    throttle_key: str,
    now_utc: datetime | None = None,
) -> ThrottleDecision:
    now_utc = _as_utc(now_utc or _utcnow())
    attempt = _get_attempt_row(session, throttle_key, for_update=True)

    if not attempt:
        attempt = AuthLoginAttempt(
            throttle_key=throttle_key,
            failure_count=1,
            window_started_at=now_utc,
            last_attempt_at=now_utc,
            blocked_until=None,
        )
        session.add(attempt)
        _commit_or_raise(session, "No se pudo registrar el intento de recuperacion.")
        session.refresh(attempt)
        return _build_decision(
            attempt,
            now_utc,
            max_attempts=settings.auth_recovery_max_attempts,
            window_minutes=settings.auth_recovery_window_minutes,
        )

    blocked_until = _as_utc(attempt.blocked_until) if attempt.blocked_until else None
    if blocked_until and blocked_until > now_utc:
        return _build_decision(
            attempt,
            now_utc,
            max_attempts=settings.auth_recovery_max_attempts,
            window_minutes=settings.auth_recovery_window_minutes,
        )

    if _window_end(attempt.window_started_at, settings.auth_recovery_window_minutes) <= now_utc:
        attempt.failure_count = 1
        attempt.window_started_at = now_utc
        attempt.blocked_until = None
    else:
        attempt.failure_count += 1

    attempt.last_attempt_at = now_utc
    if attempt.failure_count >= settings.auth_recovery_max_attempts:
        attempt.blocked_until = _window_end(attempt.window_started_at, settings.auth_recovery_window_minutes)

    _commit_or_raise(session, "No se pudo actualizar el contador de recuperacion.")
    session.refresh(attempt)
    return _build_decision(
        attempt,
        now_utc,
        max_attempts=settings.auth_recovery_max_attempts,
        window_minutes=settings.auth_recovery_window_minutes,
    )
