from __future__ import annotations


def _change_text_to_float(float_as_str: str) -> float:
    return float(float_as_str.replace(",", ".")) if float_as_str else 0.0
