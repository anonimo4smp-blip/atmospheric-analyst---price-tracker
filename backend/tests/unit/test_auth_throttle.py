from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.services.auth_throttle import (
    build_email_action_throttle_key,
    build_login_throttle_key,
    check_login_rate_limit,
    check_recovery_rate_limit,
    clear_login_failures,
    register_recovery_attempt,
    register_login_failure,
)

settings = get_settings()


def _build_session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def test_build_login_throttle_key_normalizes_values() -> None:
    key = build_login_throttle_key(" 127.0.0.1 ", " USER@Example.COM ")
    assert key == "127.0.0.1|user@example.com"


def test_build_email_action_throttle_key_normalizes_values() -> None:
    key = build_email_action_throttle_key(" 127.0.0.1 ", " USER@Example.COM ", " Forgot_Password ")
    assert key == "forgot_password|127.0.0.1|user@example.com"


def test_login_rate_limit_blocks_after_max_attempts() -> None:
    session_factory = _build_session_factory()
    key = build_login_throttle_key("127.0.0.1", "limit@example.com")

    with session_factory() as session:
        clear_login_failures(session, key)

        base = datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc)
        for index in range(settings.auth_login_max_attempts - 1):
            decision = register_login_failure(session, key, now_utc=base + timedelta(seconds=index))
            assert decision.allowed is True

        blocked = register_login_failure(
            session,
            key,
            now_utc=base + timedelta(seconds=settings.auth_login_max_attempts),
        )
        assert blocked.allowed is False
        assert blocked.retry_after_seconds > 0

        check_blocked = check_login_rate_limit(session, key, now_utc=base + timedelta(seconds=30))
        assert check_blocked.allowed is False


def test_login_rate_limit_unlocks_after_window() -> None:
    session_factory = _build_session_factory()
    key = build_login_throttle_key("127.0.0.1", "window@example.com")

    with session_factory() as session:
        clear_login_failures(session, key)

        base = datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc)
        for index in range(settings.auth_login_max_attempts):
            register_login_failure(session, key, now_utc=base + timedelta(seconds=index))

        unlocked_at = base + timedelta(minutes=settings.auth_login_window_minutes, seconds=2)
        unlocked = check_login_rate_limit(session, key, now_utc=unlocked_at)
        assert unlocked.allowed is True
        assert unlocked.retry_after_seconds == 0


def test_clear_login_failures_resets_state() -> None:
    session_factory = _build_session_factory()
    key = build_login_throttle_key("127.0.0.1", "reset@example.com")

    with session_factory() as session:
        clear_login_failures(session, key)
        register_login_failure(session, key)
        clear_login_failures(session, key)
        decision = check_login_rate_limit(session, key)
        assert decision.allowed is True


def test_login_rate_limit_persists_across_new_db_sessions() -> None:
    session_factory = _build_session_factory()
    key = build_login_throttle_key("127.0.0.1", "persist@example.com")
    base = datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc)

    with session_factory() as session:
        clear_login_failures(session, key)
        for index in range(settings.auth_login_max_attempts):
            register_login_failure(session, key, now_utc=base + timedelta(seconds=index))

    with session_factory() as new_session:
        decision = check_login_rate_limit(new_session, key, now_utc=base + timedelta(seconds=30))
        assert decision.allowed is False


def test_recovery_rate_limit_blocks_after_max_attempts() -> None:
    session_factory = _build_session_factory()
    key = build_email_action_throttle_key("127.0.0.1", "recover@example.com", "forgot_password")

    with session_factory() as session:
        clear_login_failures(session, key)

        base = datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc)
        for index in range(settings.auth_recovery_max_attempts - 1):
            decision = register_recovery_attempt(session, key, now_utc=base + timedelta(seconds=index))
            assert decision.allowed is True

        blocked = register_recovery_attempt(
            session,
            key,
            now_utc=base + timedelta(seconds=settings.auth_recovery_max_attempts),
        )
        assert blocked.allowed is False
        assert blocked.retry_after_seconds > 0

        check_blocked = check_recovery_rate_limit(session, key, now_utc=base + timedelta(seconds=30))
        assert check_blocked.allowed is False


def test_recovery_rate_limit_unlocks_after_window() -> None:
    session_factory = _build_session_factory()
    key = build_email_action_throttle_key("127.0.0.1", "recoverwindow@example.com", "resend_verification")

    with session_factory() as session:
        clear_login_failures(session, key)

        base = datetime(2026, 3, 23, 12, 0, tzinfo=timezone.utc)
        for index in range(settings.auth_recovery_max_attempts):
            register_recovery_attempt(session, key, now_utc=base + timedelta(seconds=index))

        unlocked_at = base + timedelta(minutes=settings.auth_recovery_window_minutes, seconds=2)
        unlocked = check_recovery_rate_limit(session, key, now_utc=unlocked_at)
        assert unlocked.allowed is True
        assert unlocked.retry_after_seconds == 0
