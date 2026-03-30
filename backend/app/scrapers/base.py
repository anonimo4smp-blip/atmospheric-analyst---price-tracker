import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.core.config import get_settings

settings = get_settings()


class ScraperError(Exception):
    pass


@dataclass
class ScrapeResult:
    title: str | None
    image_url: str | None
    price: Decimal | None
    currency: str
    in_stock: bool


class BaseStoreScraper(ABC):
    store_code: str

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse_from_html(self, html: str) -> ScrapeResult:
        raise NotImplementedError

    def fetch_price(self, url: str) -> ScrapeResult:
        try:
            html = self._fetch_html(url)
            return self.parse_from_html(html)
        except ScraperError:
            raise
        except Exception as exc:
            raise ScraperError(f"Error inesperado al procesar {url}: {exc}") from exc

    @staticmethod
    def normalize_image_url(image_url: str | None) -> str | None:
        if not image_url:
            return None
        normalized = image_url.strip()
        if not normalized:
            return None
        if normalized.startswith("//"):
            return f"https:{normalized}"
        return normalized

    def _proxy_settings(self) -> dict | None:
        server = settings.scraper_proxy_server.strip()
        if not server:
            return None

        proxy = {"server": server}
        if settings.scraper_proxy_username.strip():
            proxy["username"] = settings.scraper_proxy_username.strip()
        if settings.scraper_proxy_password.strip():
            proxy["password"] = settings.scraper_proxy_password.strip()
        return proxy

    def _fetch_html(self, url: str) -> str:
        max_attempts = max(1, settings.scraper_max_retries + 1)
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                with sync_playwright() as playwright:
                    launch_kwargs = {
                        "headless": True,
                        "args": [
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                        ],
                    }
                    proxy = self._proxy_settings()
                    if proxy:
                        launch_kwargs["proxy"] = proxy

                    browser = playwright.chromium.launch(**launch_kwargs)
                    context = browser.new_context(
                        user_agent=settings.scraper_user_agent,
                        locale="es-ES",
                        timezone_id=settings.timezone,
                        viewport={"width": 1366, "height": 768},
                        extra_http_headers={
                            "Accept-Language": settings.scraper_accept_language,
                            "DNT": "1",
                            "Upgrade-Insecure-Requests": "1",
                        },
                    )
                    page = context.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=settings.scraper_timeout_ms)
                    page.wait_for_timeout(1200)
                    html = page.content()
                    context.close()
                    browser.close()

                    if not html or len(html.strip()) < 200:
                        raise ScraperError("Se recibio una respuesta HTML vacia o incompleta.")

                    return html
            except (PlaywrightTimeoutError, PlaywrightError, ScraperError) as exc:
                last_error = exc
                if attempt < max_attempts:
                    time.sleep(1.2 * attempt)
                    continue
                break

        raise ScraperError(f"No se pudo cargar la pagina tras {max_attempts} intentos: {last_error}")
