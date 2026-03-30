import app.services.auth_email_service as auth_email_service


def _set_email_settings(**kwargs):
    previous: dict[str, object] = {}
    for key, value in kwargs.items():
        previous[key] = getattr(auth_email_service.settings, key)
        setattr(auth_email_service.settings, key, value)
    return previous


def _restore_email_settings(previous: dict[str, object]) -> None:
    for key, value in previous.items():
        setattr(auth_email_service.settings, key, value)


def test_build_action_url_replaces_token_placeholder() -> None:
    url = auth_email_service._build_action_url("https://app.example.com/verify/{token}", "abc123")
    assert url == "https://app.example.com/verify/abc123"


def test_build_action_url_appends_token_as_query_param() -> None:
    url_no_query = auth_email_service._build_action_url("https://app.example.com/reset", "abc123")
    url_with_query = auth_email_service._build_action_url("https://app.example.com/reset?lang=es", "abc123")
    assert url_no_query == "https://app.example.com/reset?token=abc123"
    assert url_with_query == "https://app.example.com/reset?lang=es&token=abc123"


def test_send_verification_email_returns_false_when_sending_disabled() -> None:
    previous = _set_email_settings(auth_email_send_enabled=False)
    try:
        result = auth_email_service.send_verification_email("user@example.com", "raw-token")
        assert result is False
    finally:
        _restore_email_settings(previous)


def test_send_verification_email_builds_expected_payload(monkeypatch) -> None:
    sent: dict[str, str] = {}

    def fake_send(to_email: str, subject: str, body: str) -> None:
        sent["to_email"] = to_email
        sent["subject"] = subject
        sent["body"] = body

    monkeypatch.setattr(auth_email_service, "_send_smtp_email", fake_send)
    previous = _set_email_settings(
        auth_email_send_enabled=True,
        auth_email_verify_url_template="https://app.example.com/verify?token={token}",
    )
    try:
        result = auth_email_service.send_verification_email("user@example.com", "verify-token")
        assert result is True
        assert sent["to_email"] == "user@example.com"
        assert "Verifica tu cuenta" in sent["subject"]
        assert "https://app.example.com/verify?token=verify-token" in sent["body"]
    finally:
        _restore_email_settings(previous)


def test_send_password_reset_email_builds_expected_payload(monkeypatch) -> None:
    sent: dict[str, str] = {}

    def fake_send(to_email: str, subject: str, body: str) -> None:
        sent["to_email"] = to_email
        sent["subject"] = subject
        sent["body"] = body

    monkeypatch.setattr(auth_email_service, "_send_smtp_email", fake_send)
    previous = _set_email_settings(
        auth_email_send_enabled=True,
        auth_email_reset_url_template="https://app.example.com/reset/{token}",
    )
    try:
        result = auth_email_service.send_password_reset_email("user@example.com", "reset-token")
        assert result is True
        assert sent["to_email"] == "user@example.com"
        assert "Restablece tu contrasena" in sent["subject"]
        assert "https://app.example.com/reset/reset-token" in sent["body"]
    finally:
        _restore_email_settings(previous)


def test_validate_smtp_configuration_rejects_tls_and_ssl_enabled_simultaneously() -> None:
    previous = _set_email_settings(
        auth_email_smtp_host="smtp.example.com",
        auth_email_smtp_sender="no-reply@example.com",
        auth_email_smtp_port=587,
        auth_email_smtp_use_tls=True,
        auth_email_smtp_use_ssl=True,
    )
    try:
        try:
            auth_email_service._validate_smtp_configuration()
            assert False, "Deberia fallar si TLS y SSL estan activos al mismo tiempo"
        except RuntimeError as exc:
            assert "AUTH_EMAIL_SMTP_USE_SSL" in str(exc)
    finally:
        _restore_email_settings(previous)
