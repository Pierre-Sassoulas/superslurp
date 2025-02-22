from __future__ import annotations

import json

import pytest

# pylint: disable-next=import-private-name
from superslurp.parse_items import _get_gram
from superslurp.parser import parse_text


def test_parse_text() -> None:
    with open("tests/fixtures/sample.txt", encoding="utf8") as file:
        parse_text(file.read())


def get_parameters() -> list[tuple[str, tuple[str, int | None]]]:
    with open("tests/fixtures/sample.json", encoding="utf8") as file:
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
