import json
from pathlib import Path

import pytest

from src.classes.priceRepository import PriceRepository


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def valid_product(**overrides):
    base = {
        "key": "roland_fp_30_bk_home_bundle",
        "product_name": "Roland FP-30X BK Home Bundle",
        "url": "https://www.thomann.de/ie/roland_fp_30_bk_home_bundle.htm",
        "selectors": [".price"],
        "price_regex": r"€\s*([0-9]+(?:[.,][0-9]{2})?)",
        "min_price": 50,
        "max_price": 10000,
    }
    base.update(overrides)
    return base


def test_load_returns_empty_if_file_missing(tmp_path):
    repo = PriceRepository(tmp_path / "prices.json")
    assert repo.load() == []


def test_load_applies_defaults(tmp_path):
    p = valid_product()
    write_json(tmp_path / "prices.json", [p])

    repo = PriceRepository(tmp_path / "prices.json")
    state = repo.load()

    assert state[0]["currency"] == "EUR"
    assert state[0]["currency_symbol"] == "€"
    assert state[0]["previous_price"] is None


def test_load_raises_for_non_array_top_level(tmp_path):
    write_json(tmp_path / "prices.json", {"bad": "shape"})
    repo = PriceRepository(tmp_path / "prices.json")
    with pytest.raises(ValueError, match="top-level array"):
        repo.load()


def test_load_raises_for_duplicate_key(tmp_path):
    p1 = valid_product(key="same")
    p2 = valid_product(key="same", url="https://example.com/other")
    write_json(tmp_path / "prices.json", [p1, p2])

    repo = PriceRepository(tmp_path / "prices.json")
    with pytest.raises(ValueError, match="Duplicate product key"):
        repo.load()


def test_save_validates_required_fields(tmp_path):
    repo = PriceRepository(tmp_path / "prices.json")
    bad = [valid_product(product_name="")]

    with pytest.raises(ValueError, match="missing required fields"):
        repo.save(bad)
