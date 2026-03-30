from app.scrapers.amazon import AmazonEsScraper
from app.scrapers.base import BaseStoreScraper
from app.scrapers.pccomponentes import PcComponentesScraper


def build_scrapers() -> list[BaseStoreScraper]:
    return [AmazonEsScraper(), PcComponentesScraper()]


def resolve_scraper(url: str) -> BaseStoreScraper | None:
    for scraper in build_scrapers():
        if scraper.can_handle(url):
            return scraper
    return None
