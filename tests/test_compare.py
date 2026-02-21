from __future__ import annotations

from pathlib import Path
from typing import Any

from superslurp.compare.aggregate import compare_receipt_dicts, compare_receipt_files
from superslurp.compare.matcher import FuzzyMatcher
from superslurp.compare.normalize import is_bio, normalize_for_matching

FIXTURES = Path(__file__).parent / "fixtures"


# --- normalize ---


def test_normalize_basic() -> None:
    assert normalize_for_matching("  brioche tressee  ") == "BRIOCHE TRESSEE"


def test_normalize_accents() -> None:
    assert normalize_for_matching("crème brûlée") == "CREME BRULEE"


def test_normalize_collapse_whitespace() -> None:
    assert normalize_for_matching("a   b\t c") == "A B C"


def test_normalize_strips_colors() -> None:
    assert normalize_for_matching("AIL BLANC") == "AIL"
    assert normalize_for_matching("AIL VIOLET") == "AIL"


def test_normalize_strips_packaging() -> None:
    assert normalize_for_matching("AIL BLC U BIO FILET") == "AIL"


def test_normalize_strips_count_pattern() -> None:
    assert normalize_for_matching("AIL BLANC 3 TETES") == "AIL"


def test_normalize_strips_origin() -> None:
    assert normalize_for_matching("NECTARINE JAUNE FR") == "NECTARINE"


def test_is_bio() -> None:
    assert is_bio("AIL BLC U BIO FILET") is True
    assert is_bio("AUBERGINE") is False
    assert is_bio("ABRICOT BIO") is True


# --- matcher ---


def test_matcher_exact() -> None:
    m = FuzzyMatcher(threshold=0.90)
    key1 = m.match("BRIOCHE TRESSEE PASQUIER")
    key2 = m.match("BRIOCHE TRESSEE PASQUIER")
    assert key1 == key2
    assert key1 == "BRIOCHE TRESSEE PASQUIER"


def test_matcher_accent_variation() -> None:
    m = FuzzyMatcher(threshold=0.90)
    key1 = m.match("CREME BRULEE")
    key2 = m.match("CRÈME BRÛLÉE")
    assert key1 == key2


def test_matcher_different_products() -> None:
    m = FuzzyMatcher(threshold=0.90)
    key1 = m.match("BRIOCHE TRESSEE PASQUIER")
    key2 = m.match("SUCRE POUDRE")
    assert key1 != key2


def test_matcher_fuzzy_match() -> None:
    m = FuzzyMatcher(threshold=0.90)
    key1 = m.match("CHOCO.PATIS.NOIR 52% U")
    key2 = m.match("CHOCO PATIS NOIR 52% U")
    assert key1 == key2


def test_matcher_groups_produce_variants() -> None:
    m = FuzzyMatcher(threshold=0.90)
    key1 = m.match("AIL BLANC")
    key2 = m.match("AIL BLANC 3 TETES")
    key3 = m.match("AIL BLC U BIO FILET")
    key4 = m.match("AIL VIOLET")
    key5 = m.match("AIL VIOLET 3 TETES")
    assert key1 == key2 == key3 == key4 == key5


# --- aggregate (unit) ---


def test_compare_receipt_dicts_basic() -> None:
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "store": {"store_name": "SUPER U", "address": "1 RUE\nVILLE\n38000"},
            "items": {
                "EPICERIE": [
                    {
                        "name": "SUCRE POUDRE",
                        "price": 1.50,
                        "quantity": 2,
                        "grams": 1000.0,
                        "discount": None,
                    }
                ]
            },
        },
        {
            "date": "2025-02-20 11:00:00",
            "store": {"store_name": "SUPER U", "address": "1 RUE\nVILLE\n38000"},
            "items": {
                "EPICERIE": [
                    {
                        "name": "SUCRE POUDRE",
                        "price": 1.60,
                        "quantity": 1,
                        "grams": 1000.0,
                        "discount": -0.10,
                    }
                ]
            },
        },
    ]
    result = compare_receipt_dicts(receipts)
    products = result["products"]
    assert len(products) == 1
    product = products[0]
    assert product["canonical_name"] == "SUCRE POUDRE"
    assert len(product["observations"]) == 2
    assert product["observations"][0]["grams"] == 1000.0
    # Sorted by date
    assert product["observations"][0]["date"] == "2025-01-15 10:00:00"
    assert product["observations"][1]["date"] == "2025-02-20 11:00:00"
    # Store reference
    assert product["observations"][0]["store_id"] == "SUPER U - VILLE"
    assert len(result["stores"]) == 1
    assert result["stores"][0]["store_name"] == "SUPER U"
    assert result["stores"][0]["location"] == "VILLE"


def test_compare_receipt_dicts_bio_flag() -> None:
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {
                "A": [
                    {
                        "name": "AIL BLC U BIO FILET",
                        "price": 4.70,
                        "quantity": 1,
                        "grams": 250.0,
                    },
                    {"name": "AIL BLANC", "price": 3.13, "quantity": 1, "grams": None},
                ]
            },
        }
    ]
    result = compare_receipt_dicts(receipts)
    assert len(result["products"]) == 1
    obs = result["products"][0]["observations"]
    assert obs[0].get("bio") is True
    assert "bio" not in obs[1]


def test_compare_receipt_dicts_no_grams() -> None:
    receipts = [
        {
            "date": None,
            "items": {
                "EPICERIE": [
                    {
                        "name": "PILE LR06",
                        "price": 3.99,
                        "quantity": 1,
                        "grams": None,
                    }
                ]
            },
        }
    ]
    result = compare_receipt_dicts(receipts)
    product = result["products"][0]
    assert product["observations"][0]["price_per_kg"] is None


def test_compare_receipt_dicts_null_date_last() -> None:
    receipts: list[dict[str, Any]] = [
        {
            "date": None,
            "items": {"A": [{"name": "X", "price": 1.0, "quantity": 1, "grams": None}]},
        },
        {
            "date": "2025-01-01 00:00:00",
            "items": {"A": [{"name": "X", "price": 2.0, "quantity": 1, "grams": None}]},
        },
    ]
    result = compare_receipt_dicts(receipts)
    obs = result["products"][0]["observations"]
    assert obs[0]["date"] == "2025-01-01 00:00:00"
    assert obs[1]["date"] is None


def test_compare_receipt_dicts_sorted_by_name() -> None:
    receipts = [
        {
            "date": None,
            "items": {
                "A": [
                    {"name": "ZUCCHINI", "price": 1.0, "quantity": 1, "grams": None},
                    {"name": "APPLE", "price": 2.0, "quantity": 1, "grams": None},
                ]
            },
        }
    ]
    result = compare_receipt_dicts(receipts)
    names = [p["canonical_name"] for p in result["products"]]
    assert names == ["APPLE", "ZUCCHINI"]


# --- integration with fixture files ---


def test_compare_receipt_files_fixtures() -> None:
    """Load a few real fixture JSONs and verify basic structure."""
    json_files = sorted(FIXTURES.glob(".Ticket*.json"))[:5]
    if not json_files:
        return  # skip if no fixtures available
    result = compare_receipt_files(json_files)
    assert "products" in result
    assert len(result["products"]) > 0
    for product in result["products"]:
        assert "canonical_name" in product
        assert "observations" in product
        assert len(product["observations"]) > 0
        for obs in product["observations"]:
            assert "date" in obs
            assert "price" in obs
            assert "store_id" in obs
    assert "stores" in result
    assert len(result["stores"]) > 0
    for store in result["stores"]:
        assert "id" in store
        assert "store_name" in store
        assert "location" in store
