from __future__ import annotations

import json
from pathlib import Path

import pytest

from superslurp.__main__ import parse_superu_receipt

# pylint: disable-next=import-private-name
from superslurp.parse_items import _get_gram
from superslurp.parser import parse_text
from superslurp.superslurp_typing import Category, Item

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


def test_parse_items(
    sample_txt: str, expected_parsed_items: dict[Category, list[Item]]
) -> None:
    receipt = parse_text(sample_txt)

    assert isinstance(receipt, dict)
    assert isinstance(receipt["store"], dict)

    items_by_categories = receipt["items"]
    assert isinstance(items_by_categories, dict)
    for items in items_by_categories.values():
        for item in items:
            assert item["name"] is not None
            assert item["price"] is not None
            assert item["quantity"] is not None or item["grams"] is not None
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
def test_multiple_examples(path: Path) -> None:
    parse_superu_receipt(path)
