from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name

from superslurp.__main__ import parse_superu_receipt_raw
from superslurp.parse import parse_text

# pylint: disable-next=import-private-name
from superslurp.parse.parse_items import _get_gram
from superslurp.serialize.json_dump import make_json_serializable
from superslurp.superslurp_typing import Category, Items

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"
PATH_FIXTURES = [
    p for p in FIXTURES.iterdir() if "Ticket" in p.name and p.name.endswith(".pdf")
]


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
    name, grams = _get_gram(name)
    expected_name, expected_gram = expected
    assert name == expected_name, (
        f"Wrong name for {name}, expected {expected_name} got {name}"
    )
    assert grams == expected_gram, (
        f"Wrong grams for {name}, expected {expected_gram} got {grams}"
    )


def test_parse_items(sample_txt: str, expected_parsed_items: Items) -> None:
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


@pytest.mark.parametrize("path", PATH_FIXTURES, ids=(p.name for p in PATH_FIXTURES))
def test_multiple_examples(path: Path, caplog: LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    result = make_json_serializable(parse_superu_receipt_raw(path))
    expected_result_path = Path(path.parent / f".{path.name}.json")
    if not expected_result_path.exists():
        with open(expected_result_path, "w", encoding="utf8") as file:
            json.dump(result, file, indent=4)
        pytest.fail(f"Created {expected_result_path}")
    with open(expected_result_path, encoding="utf8") as f:
        expected_result = json.load(f)
    if result != expected_result:
        with open(expected_result_path, "w", encoding="utf8") as file:
            json.dump(result, file, indent=4)
        pytest.fail(f"Expected {expected_result} but got {result}, had to upgrade")
