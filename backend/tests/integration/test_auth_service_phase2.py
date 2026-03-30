from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import UserSession
from app.services.auth_service import (
    get_user_and_session_from_access_token,
    login_user,
    refresh_session,
    register_user,
    request_password_reset,
    reset_password_with_token,
    verify_email,
)


def _build_session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def _register_and_verify(
    session: Session,
    email: str = "auth.user@example.com",
    password: str = "StrongPass1234!",
) -> tuple[str, str]:
    _, verification_token = register_user(session, email=email, password=password)
    assert verification_token
    verify_email(session, verification_token)
    return email, password


def test_login_requires_verified_email() -> None:
    session_factory = _build_session_factory()

    with session_factory() as session:
        register_user(session, email="pending@example.com", password="StrongPass1234!")

        try:
            login_user(session, email="pending@example.com", password="StrongPass1234!")
            assert False, "login_user deberia fallar si el email no esta verificado"
        except ValueError as exc:
            assert "verificar" in str(exc).lower()


def test_access_token_invalid_signature_returns_value_error() -> None:
    session_factory = _build_session_factory()

    with session_factory() as session:
        email, password = _register_and_verify(session)
        _, tokens = login_user(session, email=email, password=password)

        tampered_token = f"{tokens.access_token}tampered"
        try:
            get_user_and_session_from_access_token(session, tampered_token)
            assert False, "el token manipulado deberia fallar"
        except ValueError as exc:
            assert "token de acceso invalido" in str(exc).lower()


def test_refresh_rotates_active_session() -> None:
    session_factory = _build_session_factory()

    with session_factory() as session:
        email, password = _register_and_verify(session)
        _, issued = login_user(session, email=email, password=password)
        _, refreshed = refresh_session(session, raw_refresh_token=issued.refresh_token)

        sessions = list(session.scalars(select(UserSession).order_by(UserSession.id.asc())).all())
        assert len(sessions) == 2
        assert sessions[0].revoked_at is not None
        assert sessions[1].revoked_at is None
        assert refreshed.session_id == sessions[1].id


def test_reset_password_revokes_sessions_and_allows_new_login() -> None:
    session_factory = _build_session_factory()
    original_password = "StrongPass1234!"
    new_password = "EvenStrongerPass1234!"

    with session_factory() as session:
        email, _ = _register_and_verify(session, password=original_password)
        _, issued = login_user(session, email=email, password=original_password)

        reset_token = request_password_reset(session, email=email)
        assert reset_token
        reset_password_with_token(session, raw_token=reset_token, new_password=new_password)

        updated_first_session = session.get(UserSession, issued.session_id)
        assert updated_first_session is not None
        assert updated_first_session.revoked_at is not None

        try:
            login_user(session, email=email, password=original_password)
            assert False, "la contrasena anterior ya no deberia ser valida"
        except ValueError:
            pass

        _, new_login_tokens = login_user(session, email=email, password=new_password)
        assert new_login_tokens.access_token
        assert new_login_tokens.refresh_token
