from __future__ import annotations

from pathlib import Path

from superslurp.compare.aggregate import compare_receipt_dicts, compare_receipt_files
from superslurp.compare.matcher import FuzzyMatcher
from superslurp.compare.normalize import normalize_for_matching

FIXTURES = Path(__file__).parent / "fixtures"


# --- normalize ---


def test_normalize_basic() -> None:
    assert normalize_for_matching("  brioche tressee  ") == "BRIOCHE TRESSEE"


def test_normalize_accents() -> None:
    assert normalize_for_matching("crème brûlée") == "CREME BRULEE"


def test_normalize_collapse_whitespace() -> None:
    assert normalize_for_matching("a   b\t c") == "A B C"


# --- matcher ---


def test_matcher_exact() -> None:
    m = FuzzyMatcher(threshold=0.90)
    key1 = m.match("BRIOCHE TRESSEE PASQUIER", 630.0)
    key2 = m.match("BRIOCHE TRESSEE PASQUIER", 630.0)
    assert key1 == key2
    assert key1 == ("BRIOCHE TRESSEE PASQUIER", 630.0)


def test_matcher_accent_variation() -> None:
    m = FuzzyMatcher(threshold=0.90)
    key1 = m.match("CREME BRULEE", None)
    key2 = m.match("CRÈME BRÛLÉE", None)
    assert key1 == key2


def test_matcher_different_grams_separate() -> None:
    m = FuzzyMatcher(threshold=0.90)
    key1 = m.match("LAIT ENTIER U", 1000.0)
    key2 = m.match("LAIT ENTIER U", 500.0)
    assert key1 != key2


def test_matcher_different_products() -> None:
    m = FuzzyMatcher(threshold=0.90)
    key1 = m.match("BRIOCHE TRESSEE PASQUIER", 630.0)
    key2 = m.match("SUCRE POUDRE BLANC", 1000.0)
    assert key1 != key2


def test_matcher_fuzzy_match() -> None:
    m = FuzzyMatcher(threshold=0.90)
    key1 = m.match("CHOCO.PATIS.NOIR 52% U", 600.0)
    key2 = m.match("CHOCO PATIS NOIR 52% U", 600.0)
    assert key1 == key2


# --- aggregate (unit) ---


def test_compare_receipt_dicts_basic() -> None:
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "_source": "receipt1.json",
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
            "_source": "receipt2.json",
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
    assert product["grams"] == 1000.0
    assert len(product["observations"]) == 2
    # Sorted by date
    assert product["observations"][0]["date"] == "2025-01-15 10:00:00"
    assert product["observations"][1]["date"] == "2025-02-20 11:00:00"
    # Stats
    stats = product["stats"]
    assert stats["observation_count"] == 2
    assert stats["min_price"] == 1.50
    assert stats["max_price"] == 1.60
    assert stats["avg_price"] == 1.55
    # price_per_kg present because grams is not None
    assert "min_price_per_kg" in stats
    assert stats["min_price_per_kg"] == 1.50
    assert stats["max_price_per_kg"] == 1.60


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
    assert "min_price_per_kg" not in product["stats"]


def test_compare_receipt_dicts_null_date_last() -> None:
    receipts = [
        {
            "date": None,
            "items": {
                "A": [{"name": "X", "price": 1.0, "quantity": 1, "grams": None}]
            },
        },
        {
            "date": "2025-01-01 00:00:00",
            "items": {
                "A": [{"name": "X", "price": 2.0, "quantity": 1, "grams": None}]
            },
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
        assert "grams" in product
        assert "observations" in product
        assert "stats" in product
        assert len(product["observations"]) > 0
        stats = product["stats"]
        assert stats["observation_count"] == len(product["observations"])
        assert stats["min_price"] <= stats["max_price"]
        for obs in product["observations"]:
            assert "date" in obs
            assert "price" in obs
            assert "source" in obs
