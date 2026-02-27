from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from superslurp.compare.aggregate import (
    _compute_category_rolling_averages,
    compare_receipt_dicts,
    compare_receipt_files,
)
from superslurp.compare.matcher import FuzzyMatcher

FIXTURES = Path(__file__).parent / "fixtures"


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


def test_matcher_pre_expanded_synonyms() -> None:
    """Synonyms are applied at parse time; matcher sees already-expanded names."""
    m = FuzzyMatcher(threshold=0.90)
    key1 = m.match("BLEDINA BOL CAR/RZ/JAMB 8M")
    key2 = m.match("BLEDINA BOL CAR/RZ/JAMB 8M")
    assert key1 == key2
    assert "BLEDINA" in key1


# --- aggregate (unit) ---


def test_compare_receipt_dicts_basic() -> None:
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "store": {
                "store_name": "SUPER U",
                "address": "1 RUE\nVILLE\n38000",
                "siret": "52380816000023",
                "naf": "4729Z",
            },
            "items": {
                "EPICERIE": [
                    {
                        "name": "SUCRE POUDRE",
                        "price": 1.50,
                        "bought": 2,
                        "grams": 1000.0,
                        "discount": None,
                    }
                ]
            },
        },
        {
            "date": "2025-02-20 11:00:00",
            "store": {
                "store_name": "SUPER U",
                "address": "1 RUE\nVILLE\n38000",
                "siret": "52380816000023",
                "naf": "4729Z",
            },
            "items": {
                "EPICERIE": [
                    {
                        "name": "SUCRE POUDRE",
                        "price": 1.60,
                        "bought": 1,
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
    # Observations reference sessions
    assert product["observations"][0]["session_id"] == 1
    assert product["observations"][1]["session_id"] == 2
    # Sessions carry date + store_id
    assert len(result["sessions"]) == 2
    assert result["sessions"][0]["date"] == "2025-01-15 10:00:00"
    assert result["sessions"][1]["date"] == "2025-02-20 11:00:00"
    assert result["sessions"][0]["store_id"] == "52380816000023_4729Z"
    # Store reference keyed by SIRET+NAF
    assert len(result["stores"]) == 1
    assert result["stores"][0]["id"] == "52380816000023_4729Z"
    assert result["stores"][0]["store_name"] == "SUPER U"
    assert result["stores"][0]["location"] == "VILLE"
    assert result["stores"][0]["siret"] == "52380816000023"
    assert result["stores"][0]["naf"] == "4729Z"


def test_compare_receipt_dicts_bio_flag() -> None:
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {
                "A": [
                    {
                        "name": "AIL BLC U BIO FILET",
                        "price": 4.70,
                        "bought": 1,
                        "grams": 250.0,
                        "properties": {"bio": True},
                    },
                    {
                        "name": "AIL BLANC",
                        "price": 3.13,
                        "bought": 1,
                        "grams": None,
                        "properties": {},
                    },
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
                        "bought": 1,
                        "grams": None,
                    }
                ]
            },
        }
    ]
    result = compare_receipt_dicts(receipts)
    product = result["products"][0]
    assert product["observations"][0]["price_per_kg"] is None


def test_compare_receipt_dicts_null_date_session() -> None:
    receipts: list[dict[str, Any]] = [
        {
            "date": None,
            "items": {"A": [{"name": "X", "price": 1.0, "bought": 1, "grams": None}]},
        },
        {
            "date": "2025-01-01 00:00:00",
            "items": {"A": [{"name": "X", "price": 2.0, "bought": 1, "grams": None}]},
        },
    ]
    result = compare_receipt_dicts(receipts)
    sessions = result["sessions"]
    assert sessions[0]["date"] is None
    assert sessions[1]["date"] == "2025-01-01 00:00:00"


def test_compare_receipt_dicts_sorted_by_name() -> None:
    receipts = [
        {
            "date": None,
            "items": {
                "A": [
                    {"name": "ZUCCHINI", "price": 1.0, "bought": 1, "grams": None},
                    {"name": "APPLE", "price": 2.0, "bought": 1, "grams": None},
                ]
            },
        }
    ]
    result = compare_receipt_dicts(receipts)
    names = [p["canonical_name"] for p in result["products"]]
    assert names == ["APPLE", "ZUCCHINI"]


def test_compare_receipt_dicts_pre_expanded_names() -> None:
    """Synonyms are applied at parse time; aggregate sees already-expanded names."""
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {
                "A": [
                    {"name": "BLEDINA BOL", "price": 1.0, "bought": 1, "grams": None},
                    {"name": "BLEDINA BOL", "price": 1.2, "bought": 1, "grams": None},
                ]
            },
        },
    ]
    result = compare_receipt_dicts(receipts)
    names = [p["canonical_name"] for p in result["products"]]
    assert len(names) == 1
    assert "BLEDINA" in names[0]


# --- integration with fixture files ---


def test_compare_receipt_files_fixtures() -> None:
    """Load real fixture JSONs and write comparison result."""
    if not (json_files := sorted(FIXTURES.glob(".Ticket*.json"))):
        return  # skip if no fixtures available
    result = compare_receipt_files(json_files)
    expected_path = FIXTURES / ".compare_result.json"
    if not expected_path.exists():
        with open(expected_path, "w", encoding="utf8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        pytest.fail(f"Created {expected_path}")
    with open(expected_path, encoding="utf8") as f:
        expected = json.load(f)
    if result != expected:
        with open(expected_path, "w", encoding="utf8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        pytest.fail(f"Result changed, updated {expected_path}")


# --- session totals ---


def test_session_totals_basic() -> None:
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {
                "A": [
                    {"name": "X", "price": 10.0, "bought": 2, "grams": None},
                    {"name": "Y", "price": 5.0, "bought": 1, "grams": None},
                ]
            },
        },
        {
            "date": "2025-02-20 11:00:00",
            "items": {"A": [{"name": "X", "price": 3.0, "bought": 1, "grams": None}]},
        },
    ]
    result = compare_receipt_dicts(receipts)
    totals = result["session_totals"]
    assert len(totals) == 2
    assert totals[0]["date"] == "2025-01-15"
    assert totals[0]["total"] == 25.0  # 10*2 + 5*1
    assert totals[1]["date"] == "2025-02-20"
    assert totals[1]["total"] == 3.0


def test_session_totals_skips_null_date() -> None:
    receipts: list[dict[str, Any]] = [
        {
            "date": None,
            "items": {"A": [{"name": "X", "price": 1.0, "bought": 1, "grams": None}]},
        },
    ]
    result = compare_receipt_dicts(receipts)
    assert not result["session_totals"]


# --- rolling average ---


def test_rolling_average_single_week() -> None:
    """A single session produces one rolling avg point."""
    totals = [{"date": "2025-03-05", "categories": {"Epicerie": 70.0}}]
    avg = _compute_category_rolling_averages(totals)
    assert len(avg) >= 1
    # The point covering that session should have categories with positive values
    assert any(sum(p["categories"].values()) > 0 for p in avg)


def test_rolling_average_two_consecutive_weeks() -> None:
    """Two sessions in consecutive weeks."""
    totals = [
        {"date": "2025-03-03", "categories": {"Epicerie": 100.0}},
        {"date": "2025-03-10", "categories": {"Epicerie": 50.0}},
    ]
    avg = _compute_category_rolling_averages(totals)
    assert len(avg) >= 2
    # Both points should have positive category totals
    for point in avg:
        assert sum(point["categories"].values()) > 0


def test_rolling_average_gap_skipped() -> None:
    """Sessions 6+ months apart should not produce points in the gap."""
    totals = [
        {"date": "2025-01-06", "categories": {"Epicerie": 80.0}},
        {"date": "2025-07-07", "categories": {"Epicerie": 60.0}},
    ]
    avg = _compute_category_rolling_averages(totals)
    dates = [p["date"] for p in avg]
    # No point should fall in the gap (e.g. April)
    assert not any("2025-04" in d for d in dates)


def test_rolling_average_is_smoothed() -> None:
    """Five consecutive weekly sessions: middle point averages all five."""
    # All on Mondays
    totals = [
        {"date": f"2025-03-{3 + 7 * i:02d}", "categories": {"Epicerie": float(v)}}
        for i, v in enumerate([10, 20, 30, 40, 50])
    ]
    avg = _compute_category_rolling_averages(totals)
    # The middle week (2025-03-17) should average all 5 = 30.0
    mid = next((p for p in avg if p["date"] == "2025-03-17"), None)
    assert mid is not None
    assert mid["categories"]["Epicerie"] == 30.0


def test_compare_output_contains_totals_and_rolling() -> None:
    """compare_receipt_dicts includes session_totals and category_rolling_averages."""
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {"A": [{"name": "X", "price": 5.0, "bought": 1, "grams": None}]},
        },
    ]
    result = compare_receipt_dicts(receipts)
    assert "session_totals" in result
    assert "category_rolling_averages" in result
    assert len(result["session_totals"]) == 1
    assert len(result["category_rolling_averages"]) >= 1


# --- unit count & price per unit in observations ---


def test_price_per_unit_in_observation() -> None:
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {
                "A": [
                    {
                        "name": "OEUFS PA CAL.MIXTE U X12",
                        "price": 3.0,
                        "bought": 1,
                        "grams": None,
                        "units": 12,
                    },
                    {
                        "name": "SUCRE POUDRE",
                        "price": 1.50,
                        "bought": 1,
                        "grams": 1000.0,
                        "units": None,
                    },
                ]
            },
        },
    ]
    result = compare_receipt_dicts(receipts)
    eggs = next(p for p in result["products"] if "OEUF" in p["canonical_name"])
    assert eggs["observations"][0]["unit_count"] == 12
    assert "price_per_unit" not in eggs["observations"][0]
    sugar = next(p for p in result["products"] if "SUCRE" in p["canonical_name"])
    assert sugar["observations"][0]["unit_count"] == 1
    assert "price_per_unit" not in sugar["observations"][0]


def test_eggs_grouped_together() -> None:
    """Different egg variants should all be grouped as one product."""
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {
                "A": [
                    {
                        "name": "OEUFS PA CAL.MIXTE U X12",
                        "price": 3.0,
                        "bought": 1,
                        "grams": None,
                    },
                    {
                        "name": "OEUFS PLEIN AIR MOYEN X12",
                        "price": 3.95,
                        "bought": 1,
                        "grams": None,
                    },
                    {
                        "name": "18 OEUFS FRAIS",
                        "price": 5.66,
                        "bought": 1,
                        "grams": None,
                    },
                    {
                        "name": "OEUFS CAL.MIXTE U BIO BTE X6",
                        "price": 2.39,
                        "bought": 1,
                        "grams": None,
                    },
                ]
            },
        },
    ]
    result = compare_receipt_dicts(receipts)
    egg_products = [p for p in result["products"] if "OEUF" in p["canonical_name"]]
    assert len(egg_products) == 1
    assert len(egg_products[0]["observations"]) == 4


# --- volume & price per liter in observations ---


def test_price_per_liter_in_observation() -> None:
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {
                "A": [
                    {
                        "name": "PUR JUS 1L",
                        "price": 2.70,
                        "bought": 1,
                        "grams": None,
                        "volume_ml": 1000.0,
                    },
                    {
                        "name": "SUCRE POUDRE",
                        "price": 1.50,
                        "bought": 1,
                        "grams": 1000.0,
                        "volume_ml": None,
                    },
                ]
            },
        },
    ]
    result = compare_receipt_dicts(receipts)
    juice = next(p for p in result["products"] if "JUS" in p["canonical_name"])
    assert juice["observations"][0]["volume_ml"] == 1000.0
    assert juice["observations"][0]["price_per_liter"] == 2.70
    sugar = next(p for p in result["products"] if "SUCRE" in p["canonical_name"])
    assert sugar["observations"][0]["volume_ml"] is None
    assert sugar["observations"][0]["price_per_liter"] is None


# --- brand/label in observations ---


def test_compare_receipt_dicts_brand_label() -> None:
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {
                "A": [
                    {
                        "name": "BRIOCHE TRESSEE PASQUIER",
                        "price": 3.50,
                        "bought": 1,
                        "grams": None,
                        "properties": {"brand": "PASQUIER"},
                    },
                    {
                        "name": "COMTE AOP",
                        "price": 5.20,
                        "bought": 1,
                        "grams": 200.0,
                        "properties": {"label": "AOP"},
                    },
                    {
                        "name": "SUCRE POUDRE",
                        "price": 1.50,
                        "bought": 1,
                        "grams": 1000.0,
                        "properties": {},
                    },
                ]
            },
        }
    ]
    result = compare_receipt_dicts(receipts)
    brioche = next(p for p in result["products"] if "BRIOCHE" in p["canonical_name"])
    assert brioche["observations"][0].get("brand") == "PASQUIER"
    assert "label" not in brioche["observations"][0]
    comte = next(p for p in result["products"] if "COMTE" in p["canonical_name"])
    assert comte["observations"][0].get("label") == "AOP"
    assert "brand" not in comte["observations"][0]
    sugar = next(p for p in result["products"] if "SUCRE" in p["canonical_name"])
    assert "brand" not in sugar["observations"][0]
    assert "label" not in sugar["observations"][0]


# --- affinage in observations ---


def test_compare_receipt_dicts_affinage() -> None:
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {
                "A": [
                    {
                        "name": "BEAUFORT 5 MOIS AFFINAGE",
                        "price": 12.50,
                        "bought": 1,
                        "grams": 250.0,
                        "properties": {"affinage_months": 5},
                    },
                    {
                        "name": "SUCRE POUDRE",
                        "price": 1.50,
                        "bought": 1,
                        "grams": 1000.0,
                        "properties": {},
                    },
                ]
            },
        }
    ]
    result = compare_receipt_dicts(receipts)
    beaufort = next(p for p in result["products"] if "BEAUFORT" in p["canonical_name"])
    assert beaufort["observations"][0].get("affinage_months") == 5
    sugar = next(p for p in result["products"] if "SUCRE" in p["canonical_name"])
    assert "affinage_months" not in sugar["observations"][0]


# --- production in observations ---


def test_session_category_totals() -> None:
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {
                "EPICERIE": [
                    {"name": "SUCRE POUDRE", "price": 1.50, "bought": 2, "grams": None},
                ],
                "FROMAGE LS": [
                    {"name": "COMTE AOP", "price": 5.20, "bought": 1, "grams": 200.0},
                ],
            },
        },
        {
            "date": "2025-02-20 11:00:00",
            "items": {
                "EPICERIE": [
                    {"name": "SUCRE POUDRE", "price": 1.60, "bought": 1, "grams": None},
                ],
            },
        },
    ]
    result = compare_receipt_dicts(receipts)
    cat_totals = result["session_category_totals"]
    assert len(cat_totals) == 2
    # First session: Epicerie 1.50*2=3.00, Fromage 5.20*1=5.20
    first = cat_totals[0]
    assert first["date"] == "2025-01-15"
    assert first["categories"]["Epicerie"] == 3.0
    assert first["categories"]["Fromage"] == 5.2
    # Second session: Epicerie 1.60*1=1.60
    second = cat_totals[1]
    assert second["date"] == "2025-02-20"
    assert second["categories"]["Epicerie"] == 1.6
    assert "Fromage" not in second["categories"]


def test_session_category_totals_unmapped_category() -> None:
    """Unmapped categories fall into 'Autre'."""
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {
                "SOME UNKNOWN CATEGORY": [
                    {"name": "MYSTERY ITEM", "price": 7.50, "bought": 1, "grams": None},
                ],
            },
        },
    ]
    result = compare_receipt_dicts(receipts)
    cat_totals = result["session_category_totals"]
    assert len(cat_totals) == 1
    assert cat_totals[0]["categories"]["Autre"] == 7.5


def test_session_category_totals_skips_null_date() -> None:
    receipts: list[dict[str, Any]] = [
        {
            "date": None,
            "items": {
                "EPICERIE": [{"name": "X", "price": 1.0, "bought": 1, "grams": None}]
            },
        },
    ]
    result = compare_receipt_dicts(receipts)
    assert not result["session_category_totals"]


def test_compare_receipt_dicts_production() -> None:
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {
                "A": [
                    {
                        "name": "REBLOCHON AOP FERMIER",
                        "price": 5.50,
                        "bought": 1,
                        "grams": 450.0,
                        "properties": {"production": "fermier"},
                    },
                    {
                        "name": "SUCRE POUDRE",
                        "price": 1.50,
                        "bought": 1,
                        "grams": 1000.0,
                        "properties": {},
                    },
                ]
            },
        }
    ]
    result = compare_receipt_dicts(receipts)
    reblochon = next(
        p for p in result["products"] if "REBLOCHON" in p["canonical_name"]
    )
    assert reblochon["observations"][0].get("production") == "fermier"
    sugar = next(p for p in result["products"] if "SUCRE" in p["canonical_name"])
    assert "production" not in sugar["observations"][0]
