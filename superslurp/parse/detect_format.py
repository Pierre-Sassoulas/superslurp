from __future__ import annotations


def detect_format(text: str) -> str:
    if "Telephone :" in text:
        return "v1"
    if "Téléphone" in text:
        return "v2"
    raise ValueError(
        "Cannot detect receipt format: neither 'Telephone :' nor 'Téléphone' found in text"
    )
