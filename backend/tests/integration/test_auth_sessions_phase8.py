from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.services.auth_service import (
    list_user_sessions,
    login_user,
    register_user,
    revoke_other_user_sessions,
    verify_email,
)


def _build_session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def _register_verified_user(session: Session, email: str, password: str) -> int:
    user, verification_token = register_user(session, email=email, password=password)
    verify_email(session, verification_token)
    return user.id


def test_revoke_other_user_sessions_keeps_current_session_active() -> None:
    session_factory = _build_session_factory()
    password = "StrongPass1234!"

    with session_factory() as session:
        user_id = _register_verified_user(session, email="owner@example.com", password=password)
        _, first_tokens = login_user(session, email="owner@example.com", password=password)
        _, second_tokens = login_user(session, email="owner@example.com", password=password)

        revoked_count = revoke_other_user_sessions(
            session,
            user_id=user_id,
            current_session_id=second_tokens.session_id,
        )
        assert revoked_count == 1

        active_sessions = list_user_sessions(session, user_id=user_id, include_revoked=False)
        assert len(active_sessions) == 1
        assert active_sessions[0].id == second_tokens.session_id
        assert active_sessions[0].revoked_at is None

        all_sessions = list_user_sessions(session, user_id=user_id, include_revoked=True)
        first_row = next(session_row for session_row in all_sessions if session_row.id == first_tokens.session_id)
        assert first_row.revoked_at is not None


def test_revoke_other_user_sessions_returns_zero_when_there_are_no_other_sessions() -> None:
    session_factory = _build_session_factory()
    password = "StrongPass1234!"

    with session_factory() as session:
        user_id = _register_verified_user(session, email="solo@example.com", password=password)
        _, tokens = login_user(session, email="solo@example.com", password=password)

        revoked_count = revoke_other_user_sessions(
            session,
            user_id=user_id,
            current_session_id=tokens.session_id,
        )
        assert revoked_count == 0

        active_sessions = list_user_sessions(session, user_id=user_id, include_revoked=False)
        assert len(active_sessions) == 1
        assert active_sessions[0].id == tokens.session_id
