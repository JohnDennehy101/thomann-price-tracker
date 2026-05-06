from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PriceRepository:
    def __init__(self, file_path: str | Path = "prices.json") -> None:
        self.file_path = Path(file_path)

    def _read_json(self) -> list[Any]:
        with self.file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("prices.json must contain a top-level array")

        return data

    def _normalise_item(
        self,
        idx: int,
        raw_product: Any,
        seen_keys: set[str],
    ) -> dict[str, Any]:
        if not isinstance(raw_product, dict):
            raise ValueError(f"Item at index {idx} must be an object")

        product = self._with_defaults(raw_product)
        key = self._validate_and_get_key(product, idx)

        if key in seen_keys:
            raise ValueError(f"Duplicate product key: '{key}'")
        seen_keys.add(key)

        return product

    def _normalise_items(self, data: list[Any]) -> list[dict[str, Any]]:
        normalised: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        for idx, raw_product in enumerate(data):
            normalised.append(self._normalise_item(idx, raw_product, seen_keys))

        return normalised

    def _validate_and_get_key(self, product: dict[str, Any], idx: int) -> str:
        key = product.get("key")
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"Item at index {idx} is missing a valid 'key'")
        return key

    def load(self) -> list[dict[str, Any]]:
        if not self.file_path.exists():
            return []
        data = self._read_json()
        return self._normalise_items(data)

    def save(self, state: list[dict[str, Any]]) -> None:
        for product in state:
            key = product.get("key", "<unknown>")
            self._validate_product(key, product)

        tmp = self.file_path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        tmp.replace(self.file_path)

    def _with_defaults(self, product: dict[str, Any]) -> dict[str, Any]:
        merged = {
            "key": "",
            "currency": "EUR",
            "currency_symbol": "€",
            "selectors": [],
            "price_regex": "",
            "min_price": 0.0,
            "max_price": 10_000_000.0,
            "current_price": None,
            "previous_price": None,
            "last_checked": None,
            **product,
        }
        return merged

    def _validate_required_fields(
        self, product_key: str, product: dict[str, Any]
    ) -> None:
        required = ["key", "product_name", "url", "selectors", "price_regex"]
        missing = [k for k in required if not product.get(k)]
        if missing:
            raise ValueError(
                f"Product '{product_key}' missing required fields: {', '.join(missing)}"
            )

    def _validate_selectors(self, product_key: str, selectors: Any) -> None:
        if not isinstance(selectors, list) or not all(
            isinstance(s, str) for s in selectors
        ):
            raise ValueError(f"Product '{product_key}' selectors must be list[str]")

    def _validate_price_bounds(
        self, product_key: str, min_price: Any, max_price: Any
    ) -> None:
        if not isinstance(min_price, (int, float)):
            raise ValueError(f"Product '{product_key}' min_price must be numeric")
        if not isinstance(max_price, (int, float)):
            raise ValueError(f"Product '{product_key}' max_price must be numeric")
        if float(min_price) > float(max_price):
            raise ValueError(
                f"Product '{product_key}' min_price cannot exceed max_price"
            )

    def _validate_product(self, product_key: str, product: dict[str, Any]) -> None:
        self._validate_required_fields(product_key, product)
        self._validate_selectors(product_key, product.get("selectors"))
        self._validate_price_bounds(
            product_key, product.get("min_price"), product.get("max_price")
        )
