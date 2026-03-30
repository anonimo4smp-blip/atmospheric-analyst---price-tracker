from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_access_token,
    email_verification_expiration,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    normalize_email,
    password_reset_expiration,
    refresh_token_expiration,
    verify_password,
)
from app.db.models import (
    AuditEvent,
    EmailVerificationToken,
    PasswordResetToken,
    User,
    UserSession,
)


@dataclass
class SessionTokens:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    session_id: int


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _audit(
    session: Session,
    event_type: str,
    user_id: int | None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details_json: str | None = None,
) -> None:
    session.add(
        AuditEvent(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            details_json=details_json,
        )
    )


def _issue_session_tokens(
    session: Session,
    user: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> SessionTokens:
    raw_refresh = generate_opaque_token()
    refresh_expires_at = refresh_token_expiration()
    user_session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_opaque_token(raw_refresh),
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=refresh_expires_at,
        revoked_at=None,
    )
    session.add(user_session)
    session.flush()

    access_token, access_expires_at = create_access_token(user.id, user_session.id)
    return SessionTokens(
        access_token=access_token,
        refresh_token=raw_refresh,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
        session_id=user_session.id,
    )


def _create_email_verification_token(session: Session, user_id: int) -> str:
    now_utc = _utcnow()
    # Evita acumulacion de tokens validos para el mismo usuario.
    active_tokens = session.scalars(
        select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.used_at.is_(None),
        )
    ).all()
    for token in active_tokens:
        token.used_at = now_utc

    raw_token = generate_opaque_token()
    session.add(
        EmailVerificationToken(
            user_id=user_id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=email_verification_expiration(),
            used_at=None,
        )
    )
    return raw_token


def _create_password_reset_token(session: Session, user_id: int) -> str:
    now_utc = _utcnow()
    active_tokens = session.scalars(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
        )
    ).all()
    for token in active_tokens:
        token.used_at = now_utc

    raw_token = generate_opaque_token()
    session.add(
        PasswordResetToken(
            user_id=user_id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=password_reset_expiration(),
            used_at=None,
        )
    )
    return raw_token


def register_user(
    session: Session,
    email: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, str]:
    normalized_email = normalize_email(email)
    existing_user = session.scalar(select(User).where(User.email == normalized_email))
    if existing_user:
        raise ValueError("Ya existe una cuenta para ese email.")

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        is_email_verified=False,
        is_active=True,
    )
    try:
        session.add(user)
        session.flush()

        raw_verification_token = _create_email_verification_token(session, user.id)
        _audit(
            session,
            event_type="auth.register",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.commit()
        session.refresh(user)

        return user, raw_verification_token
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudo registrar la cuenta: {exc}") from exc


def verify_email(
    session: Session,
    raw_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    now_utc = _utcnow()
    hashed = hash_opaque_token(raw_token)
    token_row = session.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == hashed,
            EmailVerificationToken.used_at.is_(None),
            EmailVerificationToken.expires_at > now_utc,
        )
    )
    if not token_row:
        raise ValueError("Token de verificacion invalido o expirado.")

    user = session.get(User, token_row.user_id)
    if not user or not user.is_active:
        raise ValueError("No se puede verificar esta cuenta.")

    try:
        token_row.used_at = now_utc
        user.is_email_verified = True
        _audit(
            session,
            event_type="auth.verify_email",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.commit()
        session.refresh(user)
        return user
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudo verificar el email: {exc}") from exc


def login_user(
    session: Session,
    email: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, SessionTokens]:
    normalized_email = normalize_email(email)
    user = session.scalar(select(User).where(User.email == normalized_email))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise ValueError("Credenciales invalidas.")
    if not user.is_email_verified:
        raise ValueError("Debes verificar tu email antes de iniciar sesion.")

    try:
        issued = _issue_session_tokens(
            session=session,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        _audit(
            session,
            event_type="auth.login",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.commit()
        session.refresh(user)
        return user, issued
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudo iniciar sesion: {exc}") from exc


def refresh_session(
    session: Session,
    raw_refresh_token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, SessionTokens]:
    now_utc = _utcnow()
    hashed = hash_opaque_token(raw_refresh_token)
    current_session = session.scalar(
        select(UserSession).where(
            UserSession.refresh_token_hash == hashed,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now_utc,
        )
    )
    if not current_session:
        raise ValueError("Sesion invalida o expirada.")

    user = session.get(User, current_session.user_id)
    if not user or not user.is_active:
        raise ValueError("Sesion invalida o expirada.")

    try:
        current_session.revoked_at = now_utc
        issued = _issue_session_tokens(
            session=session,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        _audit(
            session,
            event_type="auth.refresh",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.commit()
        session.refresh(user)
        return user, issued
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudo refrescar la sesion: {exc}") from exc


def logout_session(
    session: Session,
    raw_refresh_token: str | None = None,
    session_id: int | None = None,
    user_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    now_utc = _utcnow()
    target_session: UserSession | None = None

    if raw_refresh_token:
        hashed = hash_opaque_token(raw_refresh_token)
        target_session = session.scalar(select(UserSession).where(UserSession.refresh_token_hash == hashed))
    elif session_id and user_id:
        target_session = session.scalar(
            select(UserSession).where(UserSession.id == session_id, UserSession.user_id == user_id)
        )

    if not target_session:
        session.rollback()
        return

    try:
        if target_session.revoked_at is None:
            target_session.revoked_at = now_utc
        _audit(
            session,
            event_type="auth.logout",
            user_id=target_session.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudo cerrar sesion: {exc}") from exc


def list_user_sessions(
    session: Session,
    user_id: int,
    include_revoked: bool = False,
) -> list[UserSession]:
    try:
        statement = select(UserSession).where(UserSession.user_id == user_id)
        if not include_revoked:
            statement = statement.where(UserSession.revoked_at.is_(None))

        statement = statement.order_by(UserSession.created_at.desc(), UserSession.id.desc())
        return list(session.scalars(statement).all())
    except Exception as exc:
        raise RuntimeError(f"No se pudieron consultar las sesiones del usuario: {exc}") from exc


def revoke_other_user_sessions(
    session: Session,
    user_id: int,
    current_session_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> int:
    now_utc = _utcnow()
    try:
        active_other_sessions = session.scalars(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.id != current_session_id,
            )
        ).all()
        revoked_count = 0
        for user_session in active_other_sessions:
            user_session.revoked_at = now_utc
            revoked_count += 1

        _audit(
            session,
            event_type="auth.revoke_other_sessions",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details_json=f'{{"revoked_count": {revoked_count}}}',
        )
        session.commit()
        return revoked_count
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudieron revocar las otras sesiones: {exc}") from exc


def get_user_and_session_from_access_token(
    session: Session,
    access_token: str,
) -> tuple[User, UserSession]:
    now_utc = _utcnow()
    try:
        payload = decode_access_token(access_token)
    except Exception as exc:
        raise ValueError("Token de acceso invalido.") from exc
    try:
        user_id = int(payload.get("sub"))
        session_id = int(payload.get("sid"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Token de acceso invalido.") from exc

    user_session = session.scalar(
        select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now_utc,
        )
    )
    if not user_session:
        raise ValueError("Sesion de acceso invalida o expirada.")

    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise ValueError("Usuario inactivo.")

    return user, user_session


def request_password_reset(
    session: Session,
    email: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> str | None:
    normalized_email = normalize_email(email)
    user = session.scalar(select(User).where(User.email == normalized_email, User.is_active.is_(True)))

    # Respuesta uniforme para evitar enumeracion de cuentas.
    if not user:
        return None

    try:
        raw_token = _create_password_reset_token(session, user.id)
        _audit(
            session,
            event_type="auth.forgot_password",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.commit()
        return raw_token
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudo iniciar recuperacion de contrasena: {exc}") from exc


def resend_email_verification(
    session: Session,
    email: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> str | None:
    normalized_email = normalize_email(email)
    user = session.scalar(select(User).where(User.email == normalized_email, User.is_active.is_(True)))
    if not user or user.is_email_verified:
        return None

    try:
        raw_token = _create_email_verification_token(session, user.id)
        _audit(
            session,
            event_type="auth.resend_verification",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.commit()
        return raw_token
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudo reenviar verificacion de email: {exc}") from exc


def reset_password_with_token(
    session: Session,
    raw_token: str,
    new_password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    now_utc = _utcnow()
    hashed = hash_opaque_token(raw_token)
    token_row = session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hashed,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now_utc,
        )
    )
    if not token_row:
        raise ValueError("Token de recuperacion invalido o expirado.")

    user = session.get(User, token_row.user_id)
    if not user or not user.is_active:
        raise ValueError("No se puede actualizar la contrasena para esta cuenta.")

    try:
        token_row.used_at = now_utc
        user.password_hash = hash_password(new_password)

        active_sessions = session.scalars(
            select(UserSession).where(
                UserSession.user_id == user.id,
                UserSession.revoked_at.is_(None),
            )
        ).all()
        for active_session in active_sessions:
            active_session.revoked_at = now_utc

        _audit(
            session,
            event_type="auth.reset_password",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudo restablecer la contrasena: {exc}") from exc


def change_password(
    session: Session,
    user: User,
    current_password: str,
    new_password: str,
    current_session_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ValueError("La contrasena actual no es correcta.")

    now_utc = _utcnow()
    try:
        user.password_hash = hash_password(new_password)
        active_sessions = session.scalars(
            select(UserSession).where(
                UserSession.user_id == user.id,
                UserSession.revoked_at.is_(None),
            )
        ).all()
        for active_session in active_sessions:
            if current_session_id and active_session.id == current_session_id:
                continue
            active_session.revoked_at = now_utc

        _audit(
            session,
            event_type="auth.change_password",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"No se pudo cambiar la contrasena: {exc}") from exc
