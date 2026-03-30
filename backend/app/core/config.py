from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Price Tracker API"
    app_env: str = "dev"
    database_url: str = "postgresql+psycopg2://admin:supersecreto@postgres:5432/pricetracker"
    internal_api_key: str = "change-this-key"
    alert_email: str = "you@example.com"
    auth_jwt_secret: str = "change-me-super-secret"
    auth_jwt_algorithm: str = "HS256"
    auth_access_token_ttl_minutes: int = 15
    auth_refresh_token_ttl_days: int = 30
    auth_email_token_ttl_hours: int = 24
    auth_password_reset_ttl_minutes: int = 30
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    auth_cookie_domain: str = ""
    auth_enable_debug_tokens: bool = True
    auth_require_login_for_app: bool = True
    auth_login_max_attempts: int = 5
    auth_login_window_minutes: int = 15
    auth_recovery_max_attempts: int = 5
    auth_recovery_window_minutes: int = 15
    auth_email_send_enabled: bool = False
    auth_email_smtp_host: str = "smtp.gmail.com"
    auth_email_smtp_port: int = 587
    auth_email_smtp_user: str = ""
    auth_email_smtp_pass: str = ""
    auth_email_smtp_sender: str = "no-reply@example.com"
    auth_email_smtp_use_tls: bool = True
    auth_email_smtp_use_ssl: bool = False
    auth_email_timeout_seconds: int = 15
    auth_email_verify_url_template: str = "http://localhost:5174/?verify_token={token}"
    auth_email_reset_url_template: str = "http://localhost:5174/?reset_token={token}"
    security_csrf_enabled: bool = True
    security_headers_enabled: bool = True
    security_hsts_enabled: bool = False
    timezone: str = "Europe/Madrid"
    scraper_timeout_ms: int = 35000
    scraper_max_retries: int = 2
    scraper_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
    scraper_accept_language: str = "es-ES,es;q=0.9,en;q=0.8"
    scraper_proxy_server: str = ""
    scraper_proxy_username: str = ""
    scraper_proxy_password: str = ""
    cors_allow_origins: str = "*"
    cors_allow_credentials: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
