import json
import re
from decimal import Decimal

from bs4 import BeautifulSoup

from app.scrapers.base import BaseStoreScraper, ScrapeResult, ScraperError
from app.scrapers.utils import parse_price_to_decimal


class AmazonEsScraper(BaseStoreScraper):
    store_code = "amazon_es"

    def can_handle(self, url: str) -> bool:
        return "amazon.es" in url.lower()

    def _extract_asin(self, url: str) -> str | None:
        patterns = [
            r"/dp/([A-Z0-9]{10})",
            r"/gp/product/([A-Z0-9]{10})",
            r"/gp/aw/d/([A-Z0-9]{10})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url.upper())
            if match:
                return match.group(1)
        return None

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        title_node = soup.select_one("#productTitle")
        if title_node:
            title = title_node.get_text(strip=True)
            if title:
                return title

        og_title = soup.select_one("meta[property='og:title']")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()
        return None

    def _extract_image_url(self, soup: BeautifulSoup) -> str | None:
        selectors = [
            "#landingImage",
            "#imgTagWrapperId img",
            "meta[property='og:image']",
        ]
        for selector in selectors:
            node = soup.select_one(selector)
            if not node:
                continue
            candidate = (
                node.get("content")
                or node.get("data-old-hires")
                or node.get("data-a-dynamic-image")
                or node.get("src")
                or ""
            )
            candidate = str(candidate).strip()
            if not candidate:
                continue
            if candidate.startswith("{"):
                # `data-a-dynamic-image` contiene JSON con URL->dimensiones.
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and parsed:
                        first_key = next(iter(parsed.keys()))
                        return self.normalize_image_url(first_key)
                except Exception:
                    continue
            return self.normalize_image_url(candidate)
        return None

    def _parse_candidate_price(self, candidate: str) -> Decimal | None:
        try:
            return parse_price_to_decimal(candidate)
        except ValueError:
            return None

    def _extract_price(self, soup: BeautifulSoup) -> Decimal | None:
        candidates: list[str] = []

        for selector in [
            "span.a-price span.a-offscreen",
            "#corePrice_feature_div span.a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            "#price_inside_buybox",
            "meta[property='product:price:amount']",
            "meta[name='twitter:data1']",
        ]:
            node = soup.select_one(selector)
            if not node:
                continue
            value = (node.get("content") or node.get_text(strip=True) or "").strip()
            if value:
                candidates.append(value)

        whole_node = soup.select_one(".a-price-whole")
        fraction_node = soup.select_one(".a-price-fraction")
        if whole_node and fraction_node:
            whole = whole_node.get_text(strip=True).replace(".", "").replace(",", "")
            fraction = fraction_node.get_text(strip=True)
            if whole and fraction:
                candidates.append(f"{whole},{fraction} EUR")

        def collect_json_prices(payload, target: list[str]) -> None:
            if isinstance(payload, dict):
                for key, value in payload.items():
                    lowered = str(key).lower()
                    if lowered in {"price", "lowprice", "highprice"} and isinstance(
                        value, (str, int, float)
                    ):
                        target.append(str(value))
                    collect_json_prices(value, target)
            elif isinstance(payload, list):
                for item in payload:
                    collect_json_prices(item, target)

        for script in soup.select("script[type='application/ld+json']"):
            raw_json = (script.string or script.get_text() or "").strip()
            if not raw_json:
                continue
            try:
                parsed = json.loads(raw_json)
            except Exception:
                continue
            collect_json_prices(parsed, candidates)

        for candidate in candidates:
            parsed_price = self._parse_candidate_price(candidate)
            if parsed_price is not None:
                return parsed_price
        return None

    def _is_out_of_stock(self, soup: BeautifulSoup) -> bool:
        availability_node = soup.select_one("#availability span")
        availability_text = (
            availability_node.get_text(" ", strip=True).lower() if availability_node else ""
        )
        strong_markers = [
            "actualmente no disponible",
            "este producto no esta disponible",
            "temporarily out of stock",
            "this item is currently unavailable",
        ]
        return any(marker in availability_text for marker in strong_markers)

    def parse_from_html(self, html: str) -> ScrapeResult:
        try:
            lowered_html = html.lower()
            if (
                "documento no encontrado" in lowered_html
                and "api-services-support@amazon.com" in lowered_html
            ):
                raise ScraperError(
                    "Amazon esta bloqueando el scraping automatico para esta IP. "
                    "Configura SCRAPER_PROXY_SERVER para usar proxy residencial."
                )

            soup = BeautifulSoup(html, "html.parser")
            title = self._extract_title(soup)
            image_url = self._extract_image_url(soup)
            price = self._extract_price(soup)

            if price is not None:
                return ScrapeResult(
                    title=title,
                    image_url=image_url,
                    price=price,
                    currency="EUR",
                    in_stock=True,
                )

            if self._is_out_of_stock(soup):
                return ScrapeResult(
                    title=title,
                    image_url=image_url,
                    price=None,
                    currency="EUR",
                    in_stock=False,
                )

            raise ScraperError("No se encontro el precio en Amazon ES.")
        except ScraperError:
            raise
        except Exception as exc:
            raise ScraperError(f"Error al parsear HTML de Amazon ES: {exc}") from exc

    def fetch_price(self, url: str) -> ScrapeResult:
        primary_html = self._fetch_html(url)
        try:
            return self.parse_from_html(primary_html)
        except ScraperError as primary_error:
            if "bloqueando el scraping automatico" not in str(primary_error).lower():
                raise

            asin = self._extract_asin(url)
            if not asin:
                raise

            fallback_url = f"https://www.amazon.es/gp/aw/d/{asin}"
            fallback_html = self._fetch_html(fallback_url)
            try:
                return self.parse_from_html(fallback_html)
            except ScraperError as fallback_error:
                raise ScraperError(
                    f"{primary_error} Fallback movil tambien fallo: {fallback_error}"
                ) from fallback_error
