from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name

from superslurp.__main__ import parse_superu_receipt
from superslurp.parse import parse_text

# pylint: disable-next=import-private-name
from superslurp.parse.v1.parse_items import _get_gram
from superslurp.superslurp_typing import Category, Items

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"
PATH_FIXTURES = [
    p for p in FIXTURES.iterdir() if "Ticket" in p.name and p.name.endswith(".pdf")
]


def _is_v1_fixture(path: Path) -> bool:
    txt_path = path.parent / f".{path.name}.txt"
    if txt_path.exists():
        return "Telephone :" in txt_path.read_text(encoding="utf8")
    return True


V1_FIXTURES = [p for p in PATH_FIXTURES if _is_v1_fixture(p)]
V2_FIXTURES = [p for p in PATH_FIXTURES if not _is_v1_fixture(p)]


def _assert_date_matches_filename(result: dict[str, Any], path: Path) -> None:
    date = str(result["date"])
    assert date != "None", f"date is null for {path.name}"
    parsed = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    # Filename format: Ticket de caisse_DDMMYYYY-HHMMSS.pdf
    filename_date = datetime.strptime(path.stem.split("_")[1], "%d%m%Y-%H%M%S")
    assert parsed.date() == filename_date.date(), (
        f"date mismatch for {path.name}: "
        f"parsed {parsed.date()}, filename {filename_date.date()}"
    )
    diff_minutes = abs((parsed - filename_date).total_seconds()) / 60
    # Allow up to 2h offset (UTC vs CEST in 2024 receipts) + 10min transaction time
    assert diff_minutes < 130, (
        f"time mismatch for {path.name}: "
        f"parsed {parsed.strftime('%H:%M')}, "
        f"filename {filename_date.strftime('%H:%M')}, "
        f"diff {diff_minutes:.0f}min"
    )


@pytest.fixture
def sample_txt() -> str:
    with open(FIXTURES / "sample.txt", encoding="utf8") as file:
        return file.read()


@pytest.fixture()
def expected_parsed_items() -> dict[Category, int]:
    with open(FIXTURES / "sample_expected_parsed_items.json", encoding="utf8") as file:
        expected = json.load(file)
    result = {}
    for key, value in expected.items():
        result[Category(key)] = value
    return result


def get_parameters() -> list[tuple[str, tuple[str, int | None]]]:
    with open(FIXTURES / "sample_expected_items.json", encoding="utf8") as file:
        content = json.load(file)
    return content  # type: ignore


@pytest.mark.parametrize("name, expected", get_parameters())
def test_quantity(name: str, expected: tuple[str, int | None]) -> None:
    name, grams, _units = _get_gram(name)
    expected_name, expected_gram = expected
    assert name == expected_name, (
        f"Wrong name for {name}, expected {expected_name} got {name}"
    )
    assert grams == expected_gram, (
        f"Wrong grams for {name}, expected {expected_gram} got {grams}"
    )


def test_parse_items(
    sample_txt: str, expected_parsed_items: Items, caplog: LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    receipt = parse_text(sample_txt)

    assert isinstance(receipt, dict)
    assert isinstance(receipt["store"], dict)

    items_by_categories = receipt["items"]
    assert isinstance(items_by_categories, dict)
    for items in items_by_categories.values():
        for item in items:
            assert item["name"] is not None
            assert item["price"] is not None
            assert item["tr"] is not None
    for category in Category:
        if category not in expected_parsed_items:
            continue
        assert len(items_by_categories[category]) == len(
            expected_parsed_items[category]
        )
        for i, item_and_expected_item in enumerate(
            zip(
                items_by_categories[category],
                expected_parsed_items[category],
                strict=True,
            )
        ):
            item, expected_item = item_and_expected_item
            assert item == expected_item, (
                f"Item {i} in category {category} is different"
            )


def _assert_store_has_siret_naf(result: dict[str, Any], path: Path) -> None:
    store = result.get("store", {})
    siret = store.get("siret")
    naf = store.get("naf")
    assert siret, f"siret missing or empty for {path.name}"
    assert siret.isdigit(), f"siret not numeric for {path.name}: {siret!r}"
    assert naf, f"naf missing or empty for {path.name}"


def _load_synonyms() -> dict[str, str]:
    synonyms_path = FIXTURES / "synonyms.json"
    with open(synonyms_path, encoding="utf8") as f:
        raw = json.load(f)
    return {k.upper(): v.upper() for k, v in raw.items()}


@pytest.mark.parametrize("path", V1_FIXTURES, ids=(p.name for p in V1_FIXTURES))
def test_multiple_examples(path: Path, caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    synonyms = _load_synonyms()
    result = parse_superu_receipt(path, debug=True, synonyms=synonyms)
    expected_result_path = Path(path.parent / f".{path.name}.json")
    if not expected_result_path.exists():
        with open(expected_result_path, "w", encoding="utf8") as file:
            json.dump(result, file, indent=4, ensure_ascii=False)
        pytest.fail(f"Created {expected_result_path}")
    with open(expected_result_path, encoding="utf8") as f:
        expected_result = json.load(f)
    if result != expected_result:
        with open(expected_result_path, "w", encoding="utf8") as file:
            json.dump(result, file, indent=4, ensure_ascii=False)
        pytest.fail(f"Expected {expected_result} but got {result}, had to upgrade")
    _assert_date_matches_filename(result, path)
    _assert_store_has_siret_naf(result, path)


@pytest.mark.parametrize("path", V2_FIXTURES, ids=(p.name for p in V2_FIXTURES))
def test_multiple_examples_v2(path: Path, caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    synonyms = _load_synonyms()
    result = parse_superu_receipt(path, debug=True, synonyms=synonyms)
    expected_result_path = Path(path.parent / f".{path.name}.json")
    if not expected_result_path.exists():
        with open(expected_result_path, "w", encoding="utf8") as file:
            json.dump(result, file, indent=4, ensure_ascii=False)
        pytest.fail(f"Created {expected_result_path}")
    with open(expected_result_path, encoding="utf8") as f:
        expected_result = json.load(f)
    if result != expected_result:
        with open(expected_result_path, "w", encoding="utf8") as file:
            json.dump(result, file, indent=4, ensure_ascii=False)
        pytest.fail(f"Expected {expected_result} but got {result}, had to upgrade")
    _assert_date_matches_filename(result, path)
    _assert_store_has_siret_naf(result, path)
