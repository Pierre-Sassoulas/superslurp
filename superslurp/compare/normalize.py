from __future__ import annotations

import re
import unicodedata

# Words stripped for matching: variety, color, packaging, origin, brand
_STRIP_WORDS = frozenset(
    {
        # Colors / varieties
        "BLANC",
        "BLC",
        "VIOLET",
        "ROGUE",
        "RGE",
        "JAUNE",
        "JNE",
        "VERT",
        "NOIR",
        "NOIRE",
        "ROSE",
        # Packaging
        "FILET",
        "SACHET",
        "BARQUETTE",
        "VRAC",
        # Origin (country codes)
        "FR",
        "IT",
        "ES",
        "SP",
        # Store brand
        "U",
        # Certification (extracted separately as observation flag)
        "BIO",
    }
)
_STRIP_COUNT_PATTERN = re.compile(r"\b\d+\s*TETES\b")


def normalize_for_matching(name: str) -> str:
    """Normalize a product name for fuzzy matching.

    Uppercase, strip accents, collapse whitespace, remove common qualifiers
    (color, packaging, origin, brand, BIO).
    """
    name = name.upper().strip()
    # Strip accents via NFD decomposition + removing combining chars
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    # Normalize dots to spaces so abbreviations match (e.g. CHOCO.PATIS → CHOCO PATIS)
    name = name.replace(".", " ")
    # Strip count patterns like "3 TETES"
    name = _STRIP_COUNT_PATTERN.sub("", name)
    # Strip known qualifier words
    words = name.split()
    words = [w for w in words if w not in _STRIP_WORDS]
    name = " ".join(words)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


def is_bio(name: str) -> bool:
    """Check if a product name contains BIO as a standalone word."""
    return bool(re.search(r"\bBIO\b", name.upper()))
