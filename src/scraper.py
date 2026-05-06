#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
import json
from datetime import datetime, timezone

from src.classes.webScraper import WebScraper
from src.models.priceExtractionConfig import PriceExtractionConfig
from src.classes.priceRepository import PriceRepository


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def set_action_env(name: str, value: str) -> None:
    github_env = os.getenv("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"{name}={value}")


def main() -> int:
    changes: list[dict] = []
    set_action_env("PRICE_CHANGED", "false")
    set_action_env("CHANGED_PRODUCTS_JSON", "[]")

    try:
        repo = PriceRepository("prices.json")
        scraper = WebScraper(timeout=30)

        state = repo.load()

        if not state:
            print("No products configured in prices.json. Nothing to check.")
            return 0

        for product in state:
            config = PriceExtractionConfig(
                selectors=product.get("selectors", []),
                price_regex=product.get("price_regex", ""),
                min_price=float(product.get("min_price", 0)),
                max_price=float(product.get("max_price", 10_000_000)),
                currency_symbol=product.get("currency_symbol", "€"),
            )

            try:
                html = scraper.fetch_html(product["url"])
                current_price = scraper.extract_price(html, config)
            except RuntimeError as exc:
                print(f"Skipping {product.get('key', '<unknown>')}: {exc}")
                continue

            if current_price is None:
                print(f"Could not extract price for {product.get('key')}")
                continue

            previous = product.get("current_price")
            product["previous_price"] = previous
            product["current_price"] = round(current_price, 2)
            product["last_checked"] = now_iso()

            if previous is None:
                continue

            diff = round(current_price - float(previous), 2)

            if abs(diff) < 0.01:
                continue

            changes.append(
                {
                    "key": product.get("key", ""),
                    "product_name": product.get("product_name", ""),
                    "url": product["url"],
                    "currency_symbol": product.get("currency_symbol", "€"),
                    "old_price": round(float(previous), 2),
                    "new_price": round(current_price, 2),
                    "diff": diff,
                }
            )

        repo.save(state)
        set_action_env("PRICE_CHANGED", "true" if changes else "false")
        set_action_env(
            "CHANGED_PRODUCTS_JSON",
            json.dumps(changes, ensure_ascii=False, separators=(",", ":")),
        )
        return 0

    except Exception as exc:
        print(f"Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
