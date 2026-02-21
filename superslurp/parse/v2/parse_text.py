from __future__ import annotations

from superslurp.superslurp_typing import Receipt


def parse_text_v2(text: str) -> Receipt:
    raise NotImplementedError(
        "V2 receipt format parser is not yet implemented. "
        "This format uses centered store headers and plain category names."
    )
