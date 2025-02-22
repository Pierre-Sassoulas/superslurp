from __future__ import annotations

from superslurp.parser import parse_text


def test_parse_text() -> None:
    with open("tests/fixtures/sample.txt", encoding="utf8") as file:
        parse_text(file.read())
