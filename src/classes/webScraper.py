import re
import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from src.models.priceExtractionConfig import PriceExtractionConfig


class WebScraper:
    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-IE,en;q=0.9",
        }

        retry = Retry(
            total=3,
            connect=3,
            read=3,
            status=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry)
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def fetch_html(self, url: str) -> str:
        try:
            resp = self.session.get(url, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.text
        except requests.Timeout as exc:
            raise RuntimeError(f"Timeout fetching {url}: {exc}") from exc
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            raise RuntimeError(f"HTTP {status} fetching {url}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Network error fetching {url}: {exc}") from exc

    def _compile_pattern(self, price_regex: str) -> re.Pattern[str]:
        try:
            return re.compile(price_regex)
        except re.error as exc:
            raise ValueError(f"Invalid price regex: {price_regex}") from exc

    def _extract_from_selectors(
        self,
        soup: BeautifulSoup,
        pattern: re.Pattern[str],
        config: PriceExtractionConfig,
    ) -> float | None:
        for selector in config.selectors:
            for node in soup.select(selector):
                text = " ".join(node.get_text(" ", strip=True).split())
                value = self._extract_first_valid_value(text, pattern, config)
                if value is not None:
                    return value
        return None

    @staticmethod
    def _parse_price(raw: str) -> float:
        value = raw.strip()
        if "," in value and "." in value:
            if value.rfind(",") > value.rfind("."):
                normalised = value.replace(".", "").replace(",", ".")
            else:
                normalised = value.replace(",", "")
            return float(normalised)
        if "," in value:
            return float(value.replace(".", "").replace(",", "."))
        return float(value.replace(",", ""))

    @staticmethod
    def _is_in_range(value: float, min_price: float, max_price: float) -> bool:
        return min_price <= value <= max_price

    def _extract_first_valid_value(
        self, text: str, pattern: re.Pattern[str], config: PriceExtractionConfig
    ) -> float | None:
        match = pattern.search(text)
        if not match:
            return None

        try:
            value = self._parse_price(match.group(1))
        except ValueError:
            return None

        return (
            value
            if self._is_in_range(value, config.min_price, config.max_price)
            else None
        )

    def _extract_from_text_nodes(
        self,
        soup: BeautifulSoup,
        pattern: re.Pattern[str],
        config: PriceExtractionConfig,
    ) -> float | None:
        for text in soup.find_all(
            string=lambda t: isinstance(t, str) and config.currency_symbol in t
        ):
            value = self._extract_first_valid_value(text, pattern, config)
            if value is not None:
                return value
        return None

    def extract_price(self, html: str, config: PriceExtractionConfig) -> float | None:
        soup = BeautifulSoup(html, "html.parser")
        pattern = self._compile_pattern(config.price_regex)

        by_selector = self._extract_from_selectors(soup, pattern, config)
        if by_selector is not None:
            return by_selector

        return self._extract_from_text_nodes(soup, pattern, config)
