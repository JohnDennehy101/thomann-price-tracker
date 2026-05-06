import json

import src.scraper as app


def test_main_no_products(monkeypatch):
    class Repo:
        def __init__(self, *_):
            pass

        def load(self):
            return []

        def save(self, _):
            pass

    env = {}
    monkeypatch.setattr(app, "PriceRepository", Repo)
    monkeypatch.setattr(app, "set_action_env", lambda k, v: env.__setitem__(k, v))

    assert app.main() == 0
    assert env["PRICE_CHANGED"] == "false"
    assert env["CHANGED_PRODUCTS_JSON"] == "[]"


def test_main_collects_change(monkeypatch):
    state = [
        {
            "key": "k1",
            "product_name": "P1",
            "url": "https://example.com",
            "selectors": [".price"],
            "price_regex": r"€\s*([0-9]+(?:[.,][0-9]{2})?)",
            "min_price": 1,
            "max_price": 9999,
            "currency_symbol": "€",
            "current_price": 100.0,
        }
    ]

    class Repo:
        def __init__(self, *_):
            pass

        def load(self):
            return state

        def save(self, _):
            pass

    class Scraper:
        def __init__(self, **_):
            pass

        def fetch_html(self, _):
            return "<html/>"

        def extract_price(self, *_):
            return 120.0

    env = {}
    monkeypatch.setattr(app, "PriceRepository", Repo)
    monkeypatch.setattr(app, "WebScraper", Scraper)
    monkeypatch.setattr(app, "set_action_env", lambda k, v: env.__setitem__(k, v))

    assert app.main() == 0
    assert env["PRICE_CHANGED"] == "true"

    changes = json.loads(env["CHANGED_PRODUCTS_JSON"])
    assert len(changes) == 1
    assert changes[0]["key"] == "k1"
    assert changes[0]["diff"] == 20.0
