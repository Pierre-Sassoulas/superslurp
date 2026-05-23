from __future__ import annotations


def _change_text_to_float(float_as_str: str | None) -> float | None:
    if float_as_str is None:
        return None
    return float(float_as_str.replace(",", ".")) if float_as_str else 0.0


def parse_price(price: str) -> float:
    """Parse a French-formatted price like ``"1,45 €"`` or ``"1,45"`` to float."""
    return float(price.split(" €")[0].replace(",", "."))
