import json
from decimal import Decimal

from bs4 import BeautifulSoup

from app.scrapers.base import BaseStoreScraper, ScrapeResult, ScraperError
from app.scrapers.utils import parse_price_to_decimal


class PcComponentesScraper(BaseStoreScraper):
    store_code = "pccomponentes"

    def can_handle(self, url: str) -> bool:
        return "pccomponentes.com" in url.lower()

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        title_node = (
            soup.select_one("h1[itemprop='name']")
            or soup.select_one("h1[data-testid='product-title']")
            or soup.select_one("h1")
        )
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
            "meta[property='og:image']",
            "img[itemprop='image']",
            "[data-testid='product-image'] img",
            ".product-gallery img",
        ]
        for selector in selectors:
            node = soup.select_one(selector)
            if not node:
                continue
            candidate = (
                node.get("content")
                or node.get("src")
                or node.get("data-src")
                or node.get("srcset")
                or ""
            )
            candidate = str(candidate).strip()
            if not candidate:
                continue
            if "," in candidate and " " in candidate:
                candidate = candidate.split(",")[0].strip().split(" ")[0].strip()
            return self.normalize_image_url(candidate)
        return None

    def _parse_candidate_price(self, candidate: str) -> Decimal | None:
        try:
            return parse_price_to_decimal(candidate)
        except ValueError:
            return None

    def _extract_price(self, soup: BeautifulSoup) -> Decimal | None:
        selector_candidates: list[str] = []

        for selector in [
            "[data-testid='precio']",
            "[data-testid='price-current']",
            "[data-testid='price']",
            ".price-current",
            ".product-card__price",
            ".price__amount",
            "[itemprop='price']",
            "meta[property='product:price:amount']",
        ]:
            node = soup.select_one(selector)
            if not node:
                continue
            value = (node.get("content") or node.get_text(strip=True) or "").strip()
            if value:
                selector_candidates.append(value)

        for candidate in selector_candidates:
            parsed_price = self._parse_candidate_price(candidate)
            if parsed_price is not None:
                return parsed_price

        # Priorizamos price/lowPrice frente a highPrice en agregados de ofertas.
        json_candidates: list[tuple[int, str]] = []

        def collect_json_prices(payload, target: list[tuple[int, str]]) -> None:
            if isinstance(payload, dict):
                for key, value in payload.items():
                    lowered = str(key).lower()
                    if lowered in {"price", "lowprice", "highprice"} and isinstance(
                        value, (str, int, float)
                    ):
                        priority = {"price": 0, "lowprice": 1, "highprice": 2}[lowered]
                        target.append((priority, str(value)))
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
            collect_json_prices(parsed, json_candidates)

        for _, candidate in sorted(json_candidates, key=lambda item: item[0]):
            parsed_price = self._parse_candidate_price(candidate)
            if parsed_price is not None:
                return parsed_price
        return None

    def _is_out_of_stock(self, soup: BeautifulSoup) -> bool:
        page_text = soup.get_text(" ", strip=True).lower()
        return any(marker in page_text for marker in ["agotado", "sin stock", "no disponible"])

    def parse_from_html(self, html: str) -> ScrapeResult:
        try:
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

            raise ScraperError("No se encontro el precio en PCComponentes.")
        except ScraperError:
            raise
        except Exception as exc:
            raise ScraperError(f"Error al parsear HTML de PCComponentes: {exc}") from exc
