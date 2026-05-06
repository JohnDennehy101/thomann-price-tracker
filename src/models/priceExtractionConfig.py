from dataclasses import dataclass


@dataclass(frozen=True)
class PriceExtractionConfig:
    selectors: list[str]
    price_regex: str
    min_price: float
    max_price: float
    currency_symbol: str = "€"
