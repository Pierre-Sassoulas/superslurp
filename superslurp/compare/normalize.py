from __future__ import annotations

import re
import unicodedata

# Words stripped for matching: variety, color, packaging, origin, brand, qualifiers
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
        "BTE",
        # Origin (country codes)
        "FR",
        "IT",
        "ES",
        "SP",
        # Store brand
        "U",
        # Certification (extracted separately as observation flag)
        "BIO",
        # Farming / quality qualifiers
        "PA",
        "LR",
        "CAL",
        "MIXTE",
        "MOYEN",
        "SOL",
        "FRAIS",
        "PLEIN",
        "AIR",
        "LABEL",
        "DATE",
        "COURTE",
        "PAROLE",
        "ELEVEURS",
        "LOUE",
        "CALIBRE",
        "T",
        "DE",
        "CHEZ",
        "NOUS",
        "D'ELEVEURS",
    }
)
_STRIP_COUNT_PATTERN = re.compile(r"\b\d+\s*TETES\b")
# Matches X12, BTEX12, X10+5OFF, and leading counts like "18 OEUFS"
_STRIP_UNIT_COUNT = re.compile(r"\bBTEX\d+\b|\bX\d+(?:\+\d+OFF)?\b")
_LEADING_COUNT = re.compile(r"^\d+\s+")

# Extract unit count: X12 → 12, BTEX6 → 6, X10+5OFF → 15, 18 OEUFS → 18
_UNIT_COUNT_PATTERN = re.compile(r"\bBTEX(\d+)\b|\bX(\d+)(?:\+(\d+)OFF)?\b|^(\d+)\s+")


def expand_synonyms(name: str, synonyms: dict[str, str]) -> str:
    """Expand abbreviations in a product name using an ordered synonym dict.

    Keys are patterns, values are replacements.  Iteration order matters:
    multi-word patterns (e.g. ``"CHOCO PATIS": "CHOCOLAT PATISSIER"``) placed
    before single-word fallbacks (``"PATIS": "PATISSERIE"``) take priority.

    Dots are normalized to spaces in both the name and the patterns so that
    ``CHOCO.PATIS`` and ``FROM.BLC`` are split before matching.
    """
    name = name.replace(".", " ")
    for pattern, replacement in synonyms.items():
        pat = pattern.replace(".", " ")
        name = re.sub(
            r"\b" + re.escape(pat) + r"\b", replacement, name, flags=re.IGNORECASE
        )
    return re.sub(r"\s+", " ", name).strip()


def normalize_for_matching(name: str, synonyms: dict[str, str] | None = None) -> str:
    """Normalize a product name for fuzzy matching.

    Uppercase, strip accents, collapse whitespace, remove common qualifiers
    (color, packaging, origin, brand, BIO).
    """
    name = name.upper().strip()
    # Strip accents via NFD decomposition + removing combining chars
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    # Expand synonyms (also normalizes dots to spaces)
    if synonyms:
        name = expand_synonyms(name, synonyms)
    # Normalize dots to spaces (in case no synonyms)
    name = name.replace(".", " ")
    # Strip count patterns like "3 TETES"
    name = _STRIP_COUNT_PATTERN.sub("", name)
    # Strip unit count patterns like X12, BTEX6, X10+5OFF, leading "18 "
    name = _STRIP_UNIT_COUNT.sub("", name)
    name = _LEADING_COUNT.sub("", name)
    # Strip known qualifier words
    words = name.split()
    words = [w for w in words if w not in _STRIP_WORDS]
    name = " ".join(words)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    # Normalize common singular/plural
    name = re.sub(r"\bOEUF\b", "OEUFS", name)
    return name


def extract_unit_count(name: str) -> int | None:
    """Extract the number of units from a product name.

    Examples: X12 → 12, BTEX6 → 6, X10+5OFF → 15, "18 OEUFS" → 18.
    Returns None if no count found.
    """
    name = name.upper().replace(".", " ")
    m = _UNIT_COUNT_PATTERN.search(name)
    if m is None:
        return None
    if m.group(1):  # BTEX(\d+)
        return int(m.group(1))
    if m.group(2):  # X(\d+)(+(\d+)OFF)?
        count = int(m.group(2))
        if m.group(3):
            count += int(m.group(3))
        return count
    if m.group(4):  # ^(\d+)\s+
        return int(m.group(4))
    return None


def is_bio(name: str) -> bool:
    """Check if a product name contains BIO as a standalone word."""
    return bool(re.search(r"\bBIO\b", name.upper()))
