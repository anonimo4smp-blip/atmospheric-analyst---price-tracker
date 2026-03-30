import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import get_settings

settings = get_settings()


def _build_action_url(template: str, token: str) -> str:
    if "{token}" in template:
        return template.replace("{token}", token)
    separator = "&" if "?" in template else "?"
    return f"{template}{separator}token={token}"


def _validate_smtp_configuration() -> None:
    if settings.auth_email_smtp_port <= 0:
        raise RuntimeError("AUTH_EMAIL_SMTP_PORT debe ser mayor que 0.")
    if not settings.auth_email_smtp_host.strip():
        raise RuntimeError("AUTH_EMAIL_SMTP_HOST no puede estar vacio.")
    if not settings.auth_email_smtp_sender.strip():
        raise RuntimeError("AUTH_EMAIL_SMTP_SENDER no puede estar vacio.")
    if settings.auth_email_smtp_use_ssl and settings.auth_email_smtp_use_tls:
        raise RuntimeError("No puedes activar AUTH_EMAIL_SMTP_USE_SSL y AUTH_EMAIL_SMTP_USE_TLS a la vez.")


def _send_smtp_email(to_email: str, subject: str, body: str) -> None:
    _validate_smtp_configuration()
    message = EmailMessage()
    message["From"] = settings.auth_email_smtp_sender
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    host = settings.auth_email_smtp_host
    port = settings.auth_email_smtp_port
    timeout = settings.auth_email_timeout_seconds
    username = settings.auth_email_smtp_user
    password = settings.auth_email_smtp_pass

    try:
        if settings.auth_email_smtp_use_ssl:
            with smtplib.SMTP_SSL(host=host, port=port, timeout=timeout) as server:
                if username.strip():
                    server.login(username, password)
                server.send_message(message)
            return

        with smtplib.SMTP(host=host, port=port, timeout=timeout) as server:
            if settings.auth_email_smtp_use_tls:
                server.starttls(context=ssl.create_default_context())
            if username.strip():
                server.login(username, password)
            server.send_message(message)
    except Exception as exc:
        raise RuntimeError(f"No se pudo enviar el email via SMTP: {exc}") from exc


def send_verification_email(to_email: str, token: str) -> bool:
    if not settings.auth_email_send_enabled:
        return False

    verify_url = _build_action_url(settings.auth_email_verify_url_template, token)
    subject = "Verifica tu cuenta en Price Tracker"
    body = (
        "Hola,\n\n"
        "Gracias por registrarte en Price Tracker.\n"
        "Para verificar tu cuenta, abre este enlace:\n"
        f"{verify_url}\n\n"
        "Si no solicitaste esta cuenta, ignora este mensaje.\n"
    )
    _send_smtp_email(to_email=to_email, subject=subject, body=body)
    return True


def send_password_reset_email(to_email: str, token: str) -> bool:
    if not settings.auth_email_send_enabled:
        return False

    reset_url = _build_action_url(settings.auth_email_reset_url_template, token)
    subject = "Restablece tu contrasena de Price Tracker"
    body = (
        "Hola,\n\n"
        "Recibimos una solicitud para restablecer tu contrasena.\n"
        "Usa este enlace para continuar:\n"
        f"{reset_url}\n\n"
        "Si no solicitaste este cambio, ignora este mensaje.\n"
    )
    _send_smtp_email(to_email=to_email, subject=subject, body=body)
    return True

