from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentSession, CurrentUser, get_client_ip, get_user_agent
from app.core.config import get_settings
from app.core.security import (
    ACCESS_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    cookie_max_age_seconds,
    cookie_samesite_value,
    generate_csrf_token,
    refresh_token_expiration,
)
from app.db.session import get_db_session
from app.schemas.auth import (
    AuthMessageResponse,
    AuthUserResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RevokeOtherSessionsResponse,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    UserSessionListResponse,
    UserSessionResponse,
    VerifyEmailRequest,
)
from app.services.auth_email_service import send_password_reset_email, send_verification_email
from app.services.auth_service import (
    change_password,
    login_user,
    logout_session,
    refresh_session,
    register_user,
    resend_email_verification,
    request_password_reset,
    revoke_other_user_sessions,
    reset_password_with_token,
    list_user_sessions,
    verify_email,
)
from app.services.auth_throttle import (
    build_email_action_throttle_key,
    build_login_throttle_key,
    check_recovery_rate_limit,
    check_login_rate_limit,
    clear_login_failures,
    register_recovery_attempt,
    register_login_failure,
)

settings = get_settings()
router = APIRouter(prefix="/auth")


def _cookie_domain() -> str | None:
    domain = settings.auth_cookie_domain.strip()
    return domain if domain else None


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, access_exp, refresh_exp) -> None:
    same_site = cookie_samesite_value()
    domain = _cookie_domain()

    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=same_site,
        domain=domain,
        path="/",
        max_age=cookie_max_age_seconds(access_exp),
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=same_site,
        domain=domain,
        path="/",
        max_age=cookie_max_age_seconds(refresh_exp),
    )


def _set_csrf_cookie(response: Response, csrf_token: str, refresh_expiration) -> None:
    same_site = cookie_samesite_value()
    domain = _cookie_domain()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite=same_site,
        domain=domain,
        path="/",
        max_age=cookie_max_age_seconds(refresh_expiration),
    )


def _clear_auth_cookies(response: Response) -> None:
    domain = _cookie_domain()
    response.delete_cookie(key=ACCESS_COOKIE_NAME, path="/", domain=domain)
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/", domain=domain)
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/", domain=domain)


@router.post("/register", response_model=AuthMessageResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db_session),
) -> AuthMessageResponse:
    try:
        user, raw_verification_token = register_user(
            db,
            email=payload.email,
            password=payload.password,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    email_was_sent = False
    if settings.auth_email_send_enabled:
        try:
            email_was_sent = send_verification_email(user.email, raw_verification_token)
        except RuntimeError:
            email_was_sent = False

    debug_token = raw_verification_token if settings.auth_enable_debug_tokens else None
    if email_was_sent:
        message = "Cuenta creada. Revisa tu email para verificar la cuenta."
    elif settings.auth_email_send_enabled:
        message = "Cuenta creada, pero el email de verificacion no se pudo enviar ahora. Usa reenviar verificacion."
    else:
        message = "Cuenta creada. Verifica la cuenta con el token (modo desarrollo)."

    return AuthMessageResponse(
        message=message,
        debug_token=debug_token,
    )


@router.post("/resend-verification", response_model=AuthMessageResponse)
def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(get_db_session),
) -> AuthMessageResponse:
    client_ip = get_client_ip(request)
    throttle_key = build_email_action_throttle_key(client_ip, payload.email, "resend_verification")
    try:
        pre_check = check_recovery_rate_limit(db, throttle_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    if not pre_check.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas solicitudes de verificacion. Intentalo mas tarde.",
            headers={"Retry-After": str(pre_check.retry_after_seconds)},
        )

    try:
        after_register = register_recovery_attempt(db, throttle_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    if not after_register.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas solicitudes de verificacion. Intentalo mas tarde.",
            headers={"Retry-After": str(after_register.retry_after_seconds)},
        )

    try:
        raw_token = resend_email_verification(
            db,
            email=payload.email,
            ip_address=client_ip,
            user_agent=get_user_agent(request),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    if raw_token and settings.auth_email_send_enabled:
        try:
            send_verification_email(payload.email, raw_token)
        except RuntimeError:
            pass

    debug_token = raw_token if (raw_token and settings.auth_enable_debug_tokens) else None
    return AuthMessageResponse(
        message="Si la cuenta existe y no esta verificada, enviamos un nuevo email de verificacion.",
        debug_token=debug_token,
    )


@router.post("/verify-email", response_model=AuthMessageResponse)
def verify_email_token(
    payload: VerifyEmailRequest,
    request: Request,
    db: Session = Depends(get_db_session),
) -> AuthMessageResponse:
    try:
        verify_email(
            db,
            raw_token=payload.token,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return AuthMessageResponse(message="Email verificado correctamente.")


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
) -> LoginResponse:
    client_ip = get_client_ip(request)
    throttle_key = build_login_throttle_key(client_ip, payload.email)
    try:
        throttle = check_login_rate_limit(db, throttle_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    if not throttle.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos de login. Intentalo mas tarde.",
            headers={"Retry-After": str(throttle.retry_after_seconds)},
        )

    try:
        user, tokens = login_user(
            db,
            email=payload.email,
            password=payload.password,
            ip_address=client_ip,
            user_agent=get_user_agent(request),
        )
    except ValueError:
        try:
            updated_throttle = register_login_failure(db, throttle_key)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        if not updated_throttle.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiados intentos de login. Intentalo mas tarde.",
                headers={"Retry-After": str(updated_throttle.retry_after_seconds)},
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas.")
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    try:
        clear_login_failures(db, throttle_key)
    except RuntimeError:
        # Si falla la limpieza del contador, no impedimos el login correcto.
        pass
    _set_auth_cookies(
        response=response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_exp=tokens.access_expires_at,
        refresh_exp=tokens.refresh_expires_at,
    )
    _set_csrf_cookie(response, generate_csrf_token(), tokens.refresh_expires_at)
    return LoginResponse(user=AuthUserResponse.model_validate(user))


@router.post("/refresh", response_model=LoginResponse)
def refresh_login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
) -> LoginResponse:
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No hay sesion para refrescar.",
        )

    try:
        user, tokens = refresh_session(
            db,
            raw_refresh_token=raw_refresh,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except ValueError as exc:
        _clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    _set_auth_cookies(
        response=response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_exp=tokens.access_expires_at,
        refresh_exp=tokens.refresh_expires_at,
    )
    _set_csrf_cookie(response, generate_csrf_token(), tokens.refresh_expires_at)
    return LoginResponse(user=AuthUserResponse.model_validate(user))


@router.post("/logout", response_model=AuthMessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
) -> AuthMessageResponse:
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    try:
        logout_session(
            db,
            raw_refresh_token=raw_refresh,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    _clear_auth_cookies(response)
    return AuthMessageResponse(message="Sesion cerrada.")


@router.get("/sessions", response_model=UserSessionListResponse)
def get_my_sessions(
    user: CurrentUser,
    current_session: CurrentSession,
    db: Session = Depends(get_db_session),
) -> UserSessionListResponse:
    try:
        active_sessions = list_user_sessions(db, user_id=user.id, include_revoked=False)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return UserSessionListResponse(
        sessions=[
            UserSessionResponse(
                id=user_session.id,
                ip_address=user_session.ip_address,
                user_agent=user_session.user_agent,
                expires_at=user_session.expires_at,
                revoked_at=user_session.revoked_at,
                created_at=user_session.created_at,
                is_current=user_session.id == current_session.id,
            )
            for user_session in active_sessions
        ]
    )


@router.post("/sessions/revoke-others", response_model=RevokeOtherSessionsResponse)
def revoke_other_sessions(
    request: Request,
    user: CurrentUser,
    current_session: CurrentSession,
    db: Session = Depends(get_db_session),
) -> RevokeOtherSessionsResponse:
    try:
        revoked_count = revoke_other_user_sessions(
            db,
            user_id=user.id,
            current_session_id=current_session.id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return RevokeOtherSessionsResponse(
        message="Sesiones remotas cerradas correctamente.",
        revoked_count=revoked_count,
    )


@router.get("/me", response_model=AuthUserResponse)
def get_me(
    request: Request,
    response: Response,
    user: CurrentUser,
) -> AuthUserResponse:
    if not request.cookies.get(CSRF_COOKIE_NAME):
        _set_csrf_cookie(response, generate_csrf_token(), refresh_token_expiration())
    return AuthUserResponse.model_validate(user)


@router.post("/change-password", response_model=AuthMessageResponse)
def change_my_password(
    payload: ChangePasswordRequest,
    request: Request,
    user: CurrentUser,
    current_session: CurrentSession,
    db: Session = Depends(get_db_session),
) -> AuthMessageResponse:
    try:
        change_password(
            db,
            user=user,
            current_password=payload.current_password,
            new_password=payload.new_password,
            current_session_id=current_session.id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return AuthMessageResponse(message="Contrasena actualizada.")


@router.post("/forgot-password", response_model=AuthMessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db_session),
) -> AuthMessageResponse:
    client_ip = get_client_ip(request)
    throttle_key = build_email_action_throttle_key(client_ip, payload.email, "forgot_password")
    try:
        pre_check = check_recovery_rate_limit(db, throttle_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    if not pre_check.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas solicitudes de recuperacion. Intentalo mas tarde.",
            headers={"Retry-After": str(pre_check.retry_after_seconds)},
        )

    try:
        after_register = register_recovery_attempt(db, throttle_key)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    if not after_register.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas solicitudes de recuperacion. Intentalo mas tarde.",
            headers={"Retry-After": str(after_register.retry_after_seconds)},
        )

    try:
        raw_token = request_password_reset(
            db,
            email=payload.email,
            ip_address=client_ip,
            user_agent=get_user_agent(request),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    if raw_token and settings.auth_email_send_enabled:
        try:
            send_password_reset_email(payload.email, raw_token)
        except RuntimeError:
            pass

    # Mensaje uniforme para evitar enumeracion de usuarios.
    return AuthMessageResponse(
        message="Si la cuenta existe, enviamos instrucciones de recuperacion.",
        debug_token=raw_token if (raw_token and settings.auth_enable_debug_tokens) else None,
    )


@router.post("/reset-password", response_model=AuthMessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db_session),
) -> AuthMessageResponse:
    try:
        reset_password_with_token(
            db,
            raw_token=payload.token,
            new_password=payload.new_password,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return AuthMessageResponse(message="Contrasena restablecida correctamente.")
