import pytest

from src.classes.webScraper import WebScraper
from src.models.priceExtractionConfig import PriceExtractionConfig


def config():
    return PriceExtractionConfig(
        selectors=[".price", "#price"],
        price_regex=r"€\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?)",
        min_price=50,
        max_price=10000,
        currency_symbol="€",
    )


def test_extract_price_from_selector():
    html = "<html><span class='price'>€979.00</span></html>"
    scraper = WebScraper()
    assert scraper.extract_price(html, config()) == 979.0


def test_extract_price_from_text_fallback():
    html = "<html><div>Special today: €949.00 only</div></html>"
    scraper = WebScraper()
    assert scraper.extract_price(html, config()) == 949.0


def test_extract_price_returns_none_out_of_range():
    html = "<html><span class='price'>€9.99</span></html>"
    scraper = WebScraper()
    assert scraper.extract_price(html, config()) is None


def test_extract_price_invalid_regex_raises():
    html = "<html><span class='price'>€979.00</span></html>"
    bad = PriceExtractionConfig(
        selectors=[".price"],
        price_regex="(",
        min_price=0,
        max_price=10000,
        currency_symbol="€",
    )
    scraper = WebScraper()
    with pytest.raises(ValueError, match="Invalid price regex"):
        scraper.extract_price(html, bad)
