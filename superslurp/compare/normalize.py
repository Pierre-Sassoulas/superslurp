from __future__ import annotations

import re
import unicodedata


def normalize_for_matching(name: str) -> str:
    """Normalize a product name for fuzzy matching.

    Uppercase, strip, collapse whitespace, strip accents.
    """
    name = name.upper().strip()
    # Strip accents via NFD decomposition + removing combining chars
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name)
    return name
