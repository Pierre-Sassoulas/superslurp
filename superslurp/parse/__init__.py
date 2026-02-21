from __future__ import annotations

__all__ = ["parse_text"]

from superslurp.parse.detect_format import detect_format
from superslurp.parse.v1 import parse_text_v1
from superslurp.parse.v2 import parse_text_v2
from superslurp.superslurp_typing import Receipt


def parse_text(text: str) -> Receipt:
    if (fmt := detect_format(text)) == "v1":
        return parse_text_v1(text)
    if fmt == "v2":
        return parse_text_v2(text)
    raise ValueError(f"Unknown receipt format: {fmt!r}")
