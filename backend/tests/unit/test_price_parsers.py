from decimal import Decimal

import pytest

from app.scrapers.amazon import AmazonEsScraper
from app.scrapers.pccomponentes import PcComponentesScraper
from app.scrapers.utils import parse_price_to_decimal


def test_parse_price_to_decimal_eur() -> None:
    assert parse_price_to_decimal("1.299,99 EUR") == Decimal("1299.99")


def test_parse_price_to_decimal_us_style() -> None:
    assert parse_price_to_decimal("$1,299.99") == Decimal("1299.99")


def test_parse_price_to_decimal_invalid() -> None:
    with pytest.raises(ValueError):
        parse_price_to_decimal("sin precio")


def test_amazon_parser_detects_price_and_image() -> None:
    html = """
    <html>
      <span id="productTitle">Teclado Mecanico</span>
      <meta property="og:image" content="https://images.example.com/amazon-product.jpg" />
      <span class="a-price"><span class="a-offscreen">89,90 EUR</span></span>
    </html>
    """
    scraper = AmazonEsScraper()
    result = scraper.parse_from_html(html)

    assert result.title == "Teclado Mecanico"
    assert result.image_url == "https://images.example.com/amazon-product.jpg"
    assert result.price == Decimal("89.90")
    assert result.in_stock is True


def test_amazon_parser_does_not_flag_unavailable_if_price_exists() -> None:
    html = """
    <html>
      <span id="productTitle">Tarjeta Grafica</span>
      <div>Actualmente no disponible en algunos vendedores</div>
      <span class="a-price"><span class="a-offscreen">599,00 EUR</span></span>
    </html>
    """
    scraper = AmazonEsScraper()
    result = scraper.parse_from_html(html)

    assert result.price == Decimal("599.00")
    assert result.in_stock is True


def test_pccomponentes_parser_detects_out_of_stock_and_image() -> None:
    html = """
    <html>
      <h1 itemprop="name">Portatil Gaming</h1>
      <meta property="og:image" content="https://img.pccomponentes.com/sample.jpg" />
      <div>Producto agotado temporalmente</div>
    </html>
    """
    scraper = PcComponentesScraper()
    result = scraper.parse_from_html(html)

    assert result.title == "Portatil Gaming"
    assert result.image_url == "https://img.pccomponentes.com/sample.jpg"
    assert result.price is None
    assert result.in_stock is False


def test_pccomponentes_parser_reads_jsonld_price() -> None:
    html = """
    <html>
      <head>
        <script type="application/ld+json">
          {"@type":"Product","name":"Portatil","offers":{"price":"1499.95","priceCurrency":"EUR"}}
        </script>
      </head>
      <body><h1>Portatil</h1></body>
    </html>
    """
    scraper = PcComponentesScraper()
    result = scraper.parse_from_html(html)

    assert result.price == Decimal("1499.95")
    assert result.in_stock is True


def test_pccomponentes_parser_reads_nested_jsonld_price() -> None:
    html = """
    <html>
      <head>
        <script type="application/ld+json">
          {"@graph":[{"@type":"OfferCatalog","itemListElement":[{"offers":{"price":629}}]}]}
        </script>
      </head>
      <body><h1>Producto X</h1></body>
    </html>
    """
    scraper = PcComponentesScraper()
    result = scraper.parse_from_html(html)

    assert result.price == Decimal("629.00")
    assert result.in_stock is True


def test_pccomponentes_parser_prefers_offer_price_over_aggregate_high_price() -> None:
    html = """
    <html>
      <head>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "Product",
            "offers": {
              "@type": "AggregateOffer",
              "highPrice": "476.22",
              "lowPrice": "349.99",
              "offers": {
                "@type": "Offer",
                "price": "349.99",
                "priceCurrency": "EUR"
              }
            }
          }
        </script>
      </head>
      <body><h1>Memoria RAM</h1></body>
    </html>
    """
    scraper = PcComponentesScraper()
    result = scraper.parse_from_html(html)

    assert result.price == Decimal("349.99")
    assert result.in_stock is True
