from __future__ import annotations

import json

import pytest

# pylint: disable-next=import-private-name
from superslurp.parse_items import Category, _get_gram
from superslurp.parser import parse_text


@pytest.fixture
def sample_txt() -> str:
    with open("tests/fixtures/sample.txt", encoding="utf8") as file:
        return file.read()


@pytest.fixture()
def expected_parsed_items() -> dict[Category, int]:
    with open(
        "tests/fixtures/sample_expected_parsed_items.json", encoding="utf8"
    ) as file:
        expected_len = json.load(file)
    result = {}
    for key, value in expected_len.items():
        result[Category(key)] = value
    return result


def get_parameters() -> list[tuple[str, tuple[str, int | None]]]:
    with open("tests/fixtures/sample_expected_items.json", encoding="utf8") as file:
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
    sample_txt: str, expected_parsed_items: dict[Category, int]
) -> None:
    receipt = parse_text(sample_txt)

    assert isinstance(receipt, dict)
    assert isinstance(receipt["store"], dict)

    items_by_categories = receipt["items"]
    assert isinstance(items_by_categories, dict)
    for category in Category:
        assert len(items_by_categories[category]) == expected_parsed_items[category]
    for items in items_by_categories.values():
        for item in items:
            assert item["name"] is not None
            assert item["price"] is not None
            assert item["quantity"] is not None or item["grams"] is not None
            assert item["tr"] is not None
