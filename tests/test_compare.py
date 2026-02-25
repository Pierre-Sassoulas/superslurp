from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from superslurp.compare.aggregate import (
    _compute_rolling_average,
    compare_receipt_dicts,
    compare_receipt_files,
)
from superslurp.compare.matcher import FuzzyMatcher
from superslurp.compare.normalize import (
    extract_unit_count,
    get_affinage_months,
    get_brand,
    get_milk_treatment,
    get_packaging,
    get_quality_label,
    is_bio,
    normalize_for_matching,
    strip_affinage,
)
from superslurp.parse.v1.parse_items import _get_volume, _infer_milk_fat_pct

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


def test_infer_milk_fat_pct_entier() -> None:
    assert _infer_milk_fat_pct("LAIT UHT ENTIER U BK 1 LITRE") == 3.6
    assert _infer_milk_fat_pct("LAIT UHT ENTIER U BRIQUE 6X1L") == 3.6
    assert _infer_milk_fat_pct("1L BK LAIT ENTIER UHT U") == 3.6


def test_infer_milk_fat_pct_demi_ecreme() -> None:
    assert _infer_milk_fat_pct("LAIT UHT 1/2 ECREM U BK 1L") == 1.5
    assert _infer_milk_fat_pct("LAIT DEMI-ECREME U 1L") == 1.5
    assert _infer_milk_fat_pct("LAIT DEMI ECREME LACTEL 6X1L") == 1.5


def test_infer_milk_fat_pct_ecreme() -> None:
    assert _infer_milk_fat_pct("LAIT ECREME U BK 1L") == 0.5


def test_infer_milk_fat_pct_no_match() -> None:
    assert _infer_milk_fat_pct("CREME UHT ENTIERE 35% U BK 1L") is None
    assert _infer_milk_fat_pct("CHOCOLAT LAIT/NOISET") is None
    assert _infer_milk_fat_pct("PAIN AU LAIT PASQUIER X10 350G") is None
    assert _infer_milk_fat_pct("BLEDILAIT CROISSANCE+ 12M 900G") is None
    assert _infer_milk_fat_pct("LAITUE ICEBERG") is None
    assert _infer_milk_fat_pct("SUCRE POUDRE 1KG") is None


def test_get_milk_treatment() -> None:
    assert get_milk_treatment("FROMAGE BLANC NATURE LAIT PASTEURISE U") == "pasteurise"
    assert get_milk_treatment("BRIE PASTEURISE ROITELET") == "pasteurise"
    assert get_milk_treatment("BEAUFORT AOP LAIT CRU") == "cru"
    assert get_milk_treatment("REBLOCHON SAVOIE AOP LAIT CRU") == "cru"
    assert get_milk_treatment("TOMME AIL OURS LT PASTEURISE") == "pasteurise"
    assert get_milk_treatment("AUBERGINE") is None
    assert get_milk_treatment("BAGUETTE TRADITION") is None


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


# --- integration with fixture files ---


def test_compare_receipt_files_fixtures() -> None:
    """Load real fixture JSONs and write comparison result."""
    json_files = sorted(FIXTURES.glob(".Ticket*.json"))[:5]
    if not json_files:
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
    totals = [{"session_id": 1, "date": "2025-03-05", "total": 70.0}]
    avg = _compute_rolling_average(totals)
    assert len(avg) >= 1
    # The point covering that session should have value based on
    # a window that includes the session's week
    values = [p["value"] for p in avg]
    assert any(v > 0 for v in values)


def test_rolling_average_two_consecutive_weeks() -> None:
    """Two sessions in consecutive weeks."""
    totals = [
        {"session_id": 1, "date": "2025-03-03", "total": 100.0},
        {"session_id": 2, "date": "2025-03-10", "total": 50.0},
    ]
    avg = _compute_rolling_average(totals)
    assert len(avg) >= 2
    # Both points should be positive
    for point in avg:
        assert point["value"] > 0


def test_rolling_average_gap_skipped() -> None:
    """Sessions 6+ months apart should not produce points in the gap."""
    totals = [
        {"session_id": 1, "date": "2025-01-06", "total": 80.0},
        {"session_id": 2, "date": "2025-07-07", "total": 60.0},
    ]
    avg = _compute_rolling_average(totals)
    dates = [p["date"] for p in avg]
    # No point should fall in the gap (e.g. April)
    assert not any("2025-04" in d for d in dates)


def test_rolling_average_is_smoothed() -> None:
    """Five consecutive weekly sessions: middle point averages all five."""
    # All on Mondays
    totals = [
        {"session_id": i + 1, "date": f"2025-03-{3 + 7 * i:02d}", "total": float(v)}
        for i, v in enumerate([10, 20, 30, 40, 50])
    ]
    avg = _compute_rolling_average(totals)
    # The middle week (2025-03-17) should average all 5 = 30.0
    mid = next((p for p in avg if p["date"] == "2025-03-17"), None)
    assert mid is not None
    assert mid["value"] == 30.0


def test_compare_output_contains_totals_and_rolling() -> None:
    """compare_receipt_dicts includes session_totals and rolling_average."""
    receipts = [
        {
            "date": "2025-01-15 10:00:00",
            "items": {"A": [{"name": "X", "price": 5.0, "bought": 1, "grams": None}]},
        },
    ]
    result = compare_receipt_dicts(receipts)
    assert "session_totals" in result
    assert "rolling_average" in result
    assert len(result["session_totals"]) == 1
    assert len(result["rolling_average"]) >= 1


# --- unit count & price per unit ---


def test_extract_unit_count_x_pattern() -> None:
    assert extract_unit_count("OEUFS PA CAL.MIXTE U X12") == 12
    assert extract_unit_count("OEUFS LABEL X6") == 6
    assert extract_unit_count("SAUCISSE STRASBOURG HOT DOGX10") == 10


def test_extract_unit_count_btex_pattern() -> None:
    assert extract_unit_count("OEUFS PA LR CAL.MIXTE U BTEX12") == 12


def test_extract_unit_count_with_off() -> None:
    assert extract_unit_count("OEUF.PA.MOYEN LR LOUE X10+5OFF") == 15


def test_extract_unit_count_leading() -> None:
    assert extract_unit_count("18 OEUFS FRAIS") == 18


def test_extract_unit_count_leading_plus() -> None:
    assert extract_unit_count("3+1RAC TRUF ETE") == 4
    assert extract_unit_count("3+1RACL MOUTARDE") == 4


def test_extract_unit_count_leading_fraction() -> None:
    assert extract_unit_count("1/2 REBLOCH USAV") == 0.5


def test_extract_unit_count_none() -> None:
    assert extract_unit_count("OEUFS DATE COURTE") is None
    assert extract_unit_count("SUCRE POUDRE") is None


def test_normalize_strips_unit_count() -> None:
    assert normalize_for_matching("OEUFS PA CAL.MIXTE U X12") == "OEUFS"
    assert normalize_for_matching("18 OEUFS FRAIS") == "OEUFS"


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


# --- synonyms ---


def test_normalize_with_synonyms() -> None:
    synonyms = {"BLED": "BLEDINA", "CRST": "CROISSANT"}
    assert (
        normalize_for_matching("BLED BOL CAR/RZ/JAMB 8M", synonyms)
        == "BLEDINA BOL CAR/RZ/JAMB 8M"
    )
    assert normalize_for_matching("CRST CHOCO", synonyms) == "CROISSANT CHOCO"


def test_normalize_synonyms_after_dot_expansion() -> None:
    synonyms = {"BLED": "BLEDINA"}
    assert "BLEDINA" in normalize_for_matching("BLED.BOL", synonyms)


def test_normalize_synonyms_none_unchanged() -> None:
    assert normalize_for_matching("BLED BOL") == "BLED BOL"


def test_matcher_pre_expanded_synonyms() -> None:
    """Synonyms are applied at parse time; matcher sees already-expanded names."""
    m = FuzzyMatcher(threshold=0.90)
    key1 = m.match("BLEDINA BOL CAR/RZ/JAMB 8M")
    key2 = m.match("BLEDINA BOL CAR/RZ/JAMB 8M")
    assert key1 == key2
    assert "BLEDINA" in key1


def test_normalize_multiword_synonym_priority() -> None:
    """Multi-word patterns fire before single-word fallbacks."""
    synonyms = {
        "CHOCO PATIS": "CHOCOLAT PATISSIER",
        "CHOCO": "CHOCOLAT",
        "PATIS": "PATISSERIE",
    }
    # Multi-word match: CHOCO PATIS → CHOCOLAT PATISSIER
    result = normalize_for_matching("CHOCO.PATIS.NOIR 52%", synonyms)
    assert result == "CHOCOLAT PATISSIER 52%"
    # Single-word fallback: standalone PATIS → PATISSERIE
    result = normalize_for_matching("PATIS FRAMB", synonyms)
    assert result == "PATISSERIE FRAMB"
    # Single-word fallback: standalone CHOCO → CHOCOLAT
    result = normalize_for_matching("CHOCO NOIR", synonyms)
    assert result == "CHOCOLAT"


def test_normalize_dot_pattern_synonym() -> None:
    """Patterns with dots are normalized to spaces before matching."""
    synonyms = {"FROM.BLC": "FROMAGE BLANC", "FROM": "FROMAGE"}
    # BLANC is kept because FROMAGE BLANC is a protected compound
    result = normalize_for_matching("FROM.BLC NAT", synonyms)
    assert result == "FROMAGE BLANC NAT"
    # Standalone FROM fallback
    result = normalize_for_matching("FROM.RAPE", synonyms)
    assert result == "FROMAGE RAPE"


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


def test_synonyms_fixture_loads_and_expands() -> None:
    """Load synonyms.json fixture and verify real-world abbreviation expansion."""
    synonyms_path = FIXTURES / "synonyms.json"
    with open(synonyms_path, encoding="utf8") as f:
        synonyms: dict[str, str] = json.load(f)

    # TABS LAVE VAISS.STANDARD U → TABLETTES LAVE VAISSELLE STANDARD
    result = normalize_for_matching("TABS LAVE VAISS.STANDARD U", synonyms)
    assert result == "TABLETTES LAVE VAISSELLE STANDARD"

    # CHOCO.PATIS → CHOCOLAT PATISSIER (multi-word match, NOIR stripped as color)
    result = normalize_for_matching("CHOCO.PATIS.NOIR 52%", synonyms)
    assert result == "CHOCOLAT PATISSIER 52%"

    # FROM.BLC → FROMAGE BLANC (BLANC kept: protected compound), NAT expanded
    result = normalize_for_matching("FROM.BLC NAT.7,6%MG", synonyms)
    assert result == "FROMAGE BLANC NATURE 7,6%MG"

    # PAP.TOIL → PAPIER TOILETTE (BLC/U stripped)
    result = normalize_for_matching("PAP.TOIL.BLC 2PL.U", synonyms)
    assert result == "PAPIER TOILETTE 2PL"


# --- volume ---


def test_get_volume_liters() -> None:
    name, vol, units = _get_volume("PUR JUS MULTIFRUITS U BIO 1L")
    assert vol == 1000.0
    assert units is None
    assert "1L" not in name


def test_get_volume_centiliters() -> None:
    name, vol, units = _get_volume("VIN ROGUE BORDEAUX 75CL")
    assert vol == 750.0
    assert units is None
    assert "75CL" not in name


def test_get_volume_milliliters() -> None:
    _name, vol, units = _get_volume("CREME LIQUIDE 250ML")
    assert vol == 250.0
    assert units is None


def test_get_volume_multiplier() -> None:
    name, vol, units = _get_volume("LAIT DEMI-ECREME 6X1L")
    assert vol == 6000.0
    assert units == 6
    assert "6X1L" not in name


def test_get_volume_none() -> None:
    _name, vol, units = _get_volume("SUCRE POUDRE 1KG")
    assert vol is None
    assert units is None


def test_normalize_strips_volume() -> None:
    assert "1L" not in normalize_for_matching("PUR JUS MULTIFRUITS U BIO 1L")
    assert "75CL" not in normalize_for_matching("VIN ROGUE 75CL")


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


# --- brand ---


def test_get_brand() -> None:
    assert get_brand("BRIOCHE TRESSEE PASQUIER") == "PASQUIER"
    assert get_brand("SPAGHETTI PANZANI 500G") == "PANZANI"
    assert get_brand("LAIT DEMI-ECREME LACTEL 1L") == "LACTEL"
    assert get_brand("BRIE PASTEURISE ROITELET") == "ROITELET"
    assert get_brand("OEUFS PA CAL.MIXTE U X12") == "U"
    assert get_brand("SUCRE POUDRE 1KG") is None
    assert get_brand("AUBERGINE") is None


def test_get_brand_u_standalone() -> None:
    """U should only match as a standalone word, not inside other words."""
    assert get_brand("SUCRE POUDRE") is None
    assert get_brand("AIL BLC U BIO FILET") == "U"


# --- quality label ---


def test_get_quality_label() -> None:
    assert get_quality_label("BEAUFORT AOP LAIT CRU") == "AOP"
    assert get_quality_label("COMTE AOP") == "AOP"
    assert get_quality_label("SAUCISSE SECHE IGP") == "IGP"
    assert get_quality_label("POULET LABEL ROUGE") == "Label Rouge"
    assert get_quality_label("OEUF.PA.MOYEN LR LOUE X10+5OFF") == "Label Rouge"
    assert get_quality_label("SUCRE POUDRE") is None


def test_get_quality_label_label_rouge_before_lr() -> None:
    """LABEL ROUGE should be detected even when LR also appears."""
    assert get_quality_label("POULET LABEL ROUGE LR") == "Label Rouge"


# --- packaging ---


def test_get_packaging() -> None:
    assert get_packaging("LAIT UHT ENTIER U BRIQUE 6X1L") == "BRIQUE"
    assert get_packaging("EAU MINERALE BOUTEILLE 1,5L") == "BOUTEILLE"
    assert get_packaging("SUCRE POUDRE 1KG") is None
    # Abbreviations BK/BL are NOT detected — they're ambiguous (BL = blanc in clothing).
    # Synonym expansion (BK→BRIQUE, BL→BOUTEILLE) handles them upstream.
    assert get_packaging("LAIT UHT 1/2 ECREM U BK 1L") is None
    assert get_packaging("MCH UNI MBLC BL/MA 21/23") is None


def test_normalize_strips_packaging_brique_bouteille() -> None:
    assert "BRIQUE" not in normalize_for_matching("LAIT UHT ENTIER U BRIQUE 6X1L")
    assert "BOUTEILLE" not in normalize_for_matching("EAU MINERALE BOUTEILLE 1,5L")


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


# --- affinage (cheese aging) ---


def test_get_affinage_months() -> None:
    assert get_affinage_months("BEAUFORT 5 MOIS AFFINAGE") == 5
    assert get_affinage_months("BEAUFORT 5 MOIS D'AFFINAGE") == 5
    assert get_affinage_months("BEAUFORT AFFINE 9 MOIS") == 9
    assert get_affinage_months("BEAUFORT AFFINÉ 9 MOIS") == 9
    assert get_affinage_months("COMTE AFFINAGE 12 MOIS") == 12
    assert get_affinage_months("MONT JURA 9MOIS AFFINAGE") == 9
    # Standalone N MOIS without affinage keyword → only detected in cheese mode
    assert get_affinage_months("COMTE 18 MOIS") is None
    assert get_affinage_months("COMTE 18 MOIS", cheese=True) == 18
    assert get_affinage_months("BLEDINE BISCUIT 6MOIS") is None
    assert get_affinage_months("BLEDINE BISCUIT 6MOIS", cheese=True) == 6
    assert get_affinage_months("SUCRE POUDRE") is None
    assert get_affinage_months("AUBERGINE") is None


def test_strip_affinage() -> None:
    assert strip_affinage("BEAUFORT 5 MOIS AFFINAGE") == "BEAUFORT"
    assert strip_affinage("BEAUFORT AFFINE 9 MOIS") == "BEAUFORT"
    assert strip_affinage("BEAUFORT AFFINÉ 9 MOIS") == "BEAUFORT"
    assert strip_affinage("COMTE AFFINAGE 12 MOIS") == "COMTE"
    # Standalone N MOIS only stripped in cheese mode
    assert strip_affinage("COMTE 18 MOIS") == "COMTE 18 MOIS"
    assert strip_affinage("COMTE 18 MOIS", cheese=True) == "COMTE"
    assert strip_affinage("BLEDINE BISCUIT 6MOIS") == "BLEDINE BISCUIT 6MOIS"
    assert strip_affinage("BLEDINE BISCUIT 6MOIS", cheese=True) == "BLEDINE BISCUIT"
    assert strip_affinage("SUCRE POUDRE") == "SUCRE POUDRE"


def test_normalize_strips_affinage() -> None:
    assert "MOIS" not in normalize_for_matching("BEAUFORT 5 MOIS AFFINAGE")
    assert "AFFINAGE" not in normalize_for_matching("BEAUFORT 5 MOIS AFFINAGE")
    assert "AFFINE" not in normalize_for_matching("BEAUFORT AFFINE 9 MOIS")
    assert normalize_for_matching("COMTE 18 MOIS") == "COMTE"


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
