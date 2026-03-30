from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.services.auth_service import (
    register_user,
    resend_email_verification,
    request_password_reset,
    verify_email,
)


def _build_session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def test_resend_verification_returns_new_token_for_unverified_user() -> None:
    session_factory = _build_session_factory()

    with session_factory() as session:
        _, first_token = register_user(session, email="pending@example.com", password="StrongPass1234!")
        resent_token = resend_email_verification(session, email="pending@example.com")

        assert first_token
        assert resent_token
        assert resent_token != first_token


def test_resend_verification_returns_none_for_verified_user() -> None:
    session_factory = _build_session_factory()

    with session_factory() as session:
        _, token = register_user(session, email="verified@example.com", password="StrongPass1234!")
        verify_email(session, token)

        resent_token = resend_email_verification(session, email="verified@example.com")
        assert resent_token is None


def test_request_password_reset_returns_none_for_non_existing_user() -> None:
    session_factory = _build_session_factory()

    with session_factory() as session:
        reset_token = request_password_reset(session, email="missing@example.com")
        assert reset_token is None
