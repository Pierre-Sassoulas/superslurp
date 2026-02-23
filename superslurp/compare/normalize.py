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
        # Milk treatment (standalone words; LAIT PASTEURISE/LAIT CRU handled as phrases below)
        "PASTEURISE",
        "CRU",
        # Quality labels (extracted separately as observation flag)
        "AOP",
        "IGP",
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
# Word pairs where the second word is in _STRIP_WORDS but forms a product name
# with the first word (e.g. FROMAGE BLANC is a product, not white cheese).
_PROTECTED_COMPOUNDS: dict[str, set[str]] = {
    "FROMAGE": {"BLANC"},
    "VIN": {"BLANC", "ROSE", "NOIR"},
}
_STRIP_PHRASE = re.compile(r"\bLAIT\s+(?:PASTEURISE|CRU)\b")
_STRIP_COUNT_PATTERN = re.compile(r"\b\d+\s*TETES\b")
# Matches X12, BTEX12, X10+5OFF, 6TR, 4=12RLX/X4=12RLX, and leading counts like "18 OEUFS"
_STRIP_UNIT_COUNT = re.compile(
    r"\bX?\d+(?:=\d+)?RLX\b|\bBTEX\d+\b|\bX\d+(?:\+\d+OFF)?\b|\b\d+TR\b"
)
_STRIP_VOLUME = re.compile(r"\b(?:\d+X)?\d+[,]?\d*\s*(?:L|CL|ML)\b")
_LEADING_COUNT = re.compile(r"^\d+\s+")

# Extract unit count: X12 → 12, BTEX6 → 6, X3+1OFF → 4, 6TR → 6, 4=12RLX → 4, 18 OEUFS → 18
_UNIT_COUNT_PATTERN = re.compile(
    r"\bX?(\d+)(?:=\d+)?RLX\b|\bBTEX(\d+)\b|\bX(\d+)(?:\+(\d+)OFF)?\b|\b(\d+)TR\b|^(\d+)\s+"
)


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
        pat = pattern.replace(".", " ").strip()
        if not pat:
            continue
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
    # Strip multi-word qualifiers (e.g. "LAIT PASTEURISE" as milk treatment)
    name = _STRIP_PHRASE.sub("", name)
    # Strip count patterns like "3 TETES"
    name = _STRIP_COUNT_PATTERN.sub("", name)
    # Strip volume patterns like 1L, 75CL, 250ML, 6X1L
    name = _STRIP_VOLUME.sub("", name)
    # Strip unit count patterns like X12, BTEX6, X10+5OFF, leading "18 "
    name = _STRIP_UNIT_COUNT.sub("", name)
    name = _LEADING_COUNT.sub("", name)
    # Strip known qualifier words, but keep protected compounds
    words = name.split()
    filtered: list[str] = []
    for w in words:
        if w in _STRIP_WORDS:
            prev = filtered[-1] if filtered else None
            if (
                prev
                and prev in _PROTECTED_COMPOUNDS
                and w in _PROTECTED_COMPOUNDS[prev]
            ):
                filtered.append(w)
                continue
            continue
        filtered.append(w)
    words = filtered
    name = " ".join(words)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    # Normalize common singular/plural
    name = re.sub(r"\bOEUF\b", "OEUFS", name)
    return name


def extract_unit_count(name: str) -> int | None:  # pylint: disable=too-many-return-statements
    """Extract the number of units from a product name.

    Examples: X12 → 12, BTEX6 → 6, X3+1OFF → 4, 6TR → 6, 12RLX → 12,
    "18 OEUFS" → 18.
    Returns None if no count found.
    """
    name = name.upper().replace(".", " ")
    m = _UNIT_COUNT_PATTERN.search(name)
    if m is None:
        return None
    if m.group(1):  # (\d+)RLX
        return int(m.group(1))
    if m.group(2):  # BTEX(\d+)
        return int(m.group(2))
    if m.group(3):  # X(\d+)(+(\d+)OFF)?
        count = int(m.group(3))
        if m.group(4):
            count += int(m.group(4))
        return count
    if m.group(5):  # (\d+)TR
        return int(m.group(5))
    if m.group(6):  # ^(\d+)\s+
        return int(m.group(6))
    return None


def is_bio(name: str) -> bool:
    """Check if a product name contains BIO as a standalone word."""
    return bool(re.search(r"\bBIO\b", name.upper()))


def get_milk_treatment(name: str) -> str | None:
    """Detect milk treatment (pasteurise / cru) from a product name.

    Returns ``"pasteurise"``, ``"cru"``, or ``None``.
    """
    name = name.upper()
    if re.search(r"\bCRU\b", name):
        return "cru"
    if re.search(r"\bPASTEURISE\b", name):
        return "pasteurise"
    return None


_KNOWN_BRANDS = frozenset(
    {
        "U",
        "PASQUIER",
        "PANZANI",
        "SODEBO",
        "DAUCY",
        "BRETS",
        "LACTEL",
        "DANETTE",
        "BLEDINA",
        "HIPP",
        "MAGGI",
        "VAHINE",
        "FRANCINE",
        "TRAMIER",
        "OISHIYA",
        "ROITELET",
        "RICHESMONTS",
    }
)


def get_brand(name: str) -> str | None:
    """Detect a known brand in a product name.

    Returns the brand string or ``None``.
    """
    upper = name.upper()
    for brand in _KNOWN_BRANDS:
        if re.search(r"\b" + re.escape(brand) + r"\b", upper):
            return brand
    return None


def strip_brand(name: str, brand: str) -> str:
    """Remove a brand word from *name* (case-insensitive, whole word)."""
    return re.sub(
        r"\b" + re.escape(brand) + r"\b", "", name, flags=re.IGNORECASE
    ).strip()


_QUALITY_LABEL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bLABEL ROUGE\b"), "Label Rouge"),
    (re.compile(r"\bAOP\b"), "AOP"),
    (re.compile(r"\bIGP\b"), "IGP"),
    (re.compile(r"\bLR\b"), "Label Rouge"),
]


def get_quality_label(name: str) -> str | None:
    """Detect a quality label (AOP, IGP, Label Rouge) in a product name.

    Returns the label string or ``None``.
    """
    upper = name.upper()
    for pattern, label in _QUALITY_LABEL_PATTERNS:
        if pattern.search(upper):
            return label
    return None


def strip_quality_label(name: str) -> str:
    """Remove quality label tokens (LABEL ROUGE, AOP, IGP, LR) from *name*."""
    for pattern, _ in _QUALITY_LABEL_PATTERNS:
        name = pattern.sub("", name)
    return re.sub(r"\s+", " ", name).strip()
