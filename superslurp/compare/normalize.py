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
        "ROUGE",
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
        "BRIQUE",
        "BOUTEILLE",
        "BOCAL",
        "BOITE",
        "CELLOPHANE",
        "ETUI",
        "VERRE",
        "PAQUET",
        "RECHARGE",
        # Origin (country codes, full names, regions)
        "FR",
        "FRA",
        "FRANCE",
        "IT",
        "ITALIA",
        "ES",
        "SP",
        "ESP",
        "SAVOIE",
        # Store brand
        "U",
        "USAV",
        # Certification (extracted separately as observation flag)
        "BIO",
        # Milk treatment (standalone words; LAIT PASTEURISE/LAIT CRU/LAIT UHT handled as phrases below)
        "PASTEURISE",
        "CRU",
        "THERMISE",
        "UHT",
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
        # Affinage (cheese aging)
        "AFFINAGE",
        "AFFINE",
        "MOIS",
        # Production type (cheese)
        "FERMIER",
        "LAITIER",
    }
)
# Word pairs where the second word is in _STRIP_WORDS but forms a product name
# with the first word (e.g. FROMAGE BLANC is a product, not white cheese).
_PROTECTED_COMPOUNDS: dict[str, set[str]] = {
    "FROMAGE": {"BLANC"},
    "VIN": {"BLANC", "ROSE", "NOIR"},
    "ARBRE": {"VERT"},
}
_STRIP_PHRASE = re.compile(r"\bLAIT\s+(?:PASTEURISE|CRU\s+THERMISE|CRU|UHT)\b")
_STRIP_COUNT_PATTERN = re.compile(r"\b\d+\s*TETES\b")
# Matches X12, BTEX12, X10+5OFF, 6TR, 4=12RLX/X4=12RLX, 3X1/4, leading "18 OEUFS", leading "3+1RAC"
_STRIP_UNIT_COUNT = re.compile(
    r"\bX?\d+(?:=\d+)?RLX\b|\bBTEX\d+\b|\bX\s\d+(?:\+\d+OFF)?\b"
    r"|(?<!\d)X\d+(?:\+\d+OFF)?\b|\b\d+X\d+/\d+\b|\b\d+TR\b"
)
_STRIP_VOLUME = re.compile(r"\b(?:\d+X)?\d+[,]?\d*\s*(?:LITRES?|L|CL|ML)\b|\bLITRES?\b")
_LEADING_COUNT = re.compile(r"^\d+\s+")
# Leading "3+1" (sum → 4) or "1/2" (fraction → 0.5), glued or spaced before product word
_LEADING_ARITH = re.compile(r"^(\d+)([+/])(\d+)\s*")
# Affinage patterns for normalization stripping
_STRIP_AFFINAGE_NORM = re.compile(
    r"\b\d+\s*MOIS\s+(?:D')?AFFINAGE\b"
    r"|\bAFFIN[EÉ]\s+\d+\s*MOIS\b"
    r"|\bAFFINAGE\s+\d+\s*MOIS\b"
    r"|\b\d+\s*MOIS\b"
    r"|\b\d+\s*J\.?\b"
    r"|\b\d+\s+JOURS?\b"
)

# Extract unit count: X12 → 12, BTEX6 → 6, X3+1OFF → 4, 6TR → 6, 4=12RLX → 4, 18 OEUFS → 18
_UNIT_COUNT_PATTERN = re.compile(
    r"\bX?(\d+)(?:=\d+)?RLX\b|\bBTEX(\d+)\b"
    r"|\bX\s(\d+)(?:\+(\d+)OFF)?\b|(?<!\d)X(\d+)(?:\+(\d+)OFF)?\b"
    r"|\b(\d+)X\d+/\d+\b|\b(\d+)TR\b|^(\d+)\s+"
)


def expand_synonyms(name: str, synonyms: dict[str, str]) -> str:
    """Expand abbreviations in a product name using an ordered synonym dict.

    Keys are patterns, values are replacements.  Iteration order matters:
    multi-word patterns (e.g. ``"CHOCO PATIS": "CHOCOLAT PATISSIER"``) placed
    before single-word fallbacks (``"PATIS": "PATISSERIE"``) take priority.

    Dots and spaces are both treated as word separators, so ``CHOCO.PATIS``
    and ``FROM.BLC`` match their synonym keys.  Dots are replaced by spaces
    only **after** all synonyms have been applied.
    """
    for pattern, replacement in synonyms.items():
        pat = pattern.replace(".", " ").strip()
        if not pat:
            continue
        # Build a regex where spaces in the pattern match either dot or space,
        # and word boundaries treat dots as separators (not word chars).
        escaped_words = [re.escape(w) for w in pat.split()]
        regex = (
            r"(?:(?<=[\s.])|(?<=^)|(?<=\b))"
            + r"[.\s]+".join(escaped_words)
            + r"(?=[\s.]|$|\b)"
        )
        name = re.sub(regex, replacement, name, flags=re.IGNORECASE)
    name = name.replace(".", " ")
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
    # Strip unit count patterns like X12, BTEX6, X10+5OFF, leading "18 ", "3+1", "1/2"
    name = _STRIP_UNIT_COUNT.sub("", name)
    name = _LEADING_ARITH.sub("", name)
    name = _LEADING_COUNT.sub("", name)
    # Strip affinage patterns like "5 MOIS AFFINAGE", "AFFINE 9 MOIS", "18 MOIS"
    name = _STRIP_AFFINAGE_NORM.sub("", name)
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


def extract_unit_count(name: str) -> float | None:  # pylint: disable=too-many-return-statements
    """Extract the number of units from a product name.

    Examples: X12 → 12, BTEX6 → 6, X3+1OFF → 4, 6TR → 6, 12RLX → 12,
    "18 OEUFS" → 18, "3+1RAC" → 4, "1/2 REBLOCH" → 0.5.
    Returns None if no count found.
    """
    name = name.upper().replace(".", " ")
    # Leading N+M or N/M (e.g. "3+1RAC" → 4, "1/2 REBLOCH" → 0.5)
    lm = _LEADING_ARITH.match(name)
    if lm:
        a, op, b = int(lm.group(1)), lm.group(2), int(lm.group(3))
        return a + b if op == "+" else a / b
    m = _UNIT_COUNT_PATTERN.search(name)
    if m is None:
        return None
    if m.group(1):  # (\d+)RLX
        return int(m.group(1))
    if m.group(2):  # BTEX(\d+)
        return int(m.group(2))
    # X\s(\d+) spaced or X(\d+) glued, with optional +OFF
    x_count = m.group(3) or m.group(5)
    if x_count:
        count = int(x_count)
        x_off = m.group(4) or m.group(6)
        if x_off:
            count += int(x_off)
        return count
    if m.group(7):  # (\d+)X\d+/\d+ multipack
        return int(m.group(7))
    if m.group(8):  # (\d+)TR
        return int(m.group(8))
    if m.group(9):  # ^(\d+)\s+
        return int(m.group(9))
    return None


def is_bio(name: str) -> bool:
    """Check if a product name contains BIO as a standalone word."""
    return bool(re.search(r"\bBIO\b", name.upper()))


def get_milk_treatment(name: str) -> str | None:
    """Detect milk treatment from a product name.

    Returns ``"cru thermise"``, ``"pasteurise"``, ``"cru"``, ``"UHT"``,
    or ``None``.
    """
    name = name.upper()
    if re.search(r"\bCRU\s+THERMISE", name):
        return "cru thermise"
    if re.search(r"\bCRU\b", name):
        return "cru"
    if re.search(r"\bPASTEURISE", name):
        return "pasteurise"
    if re.search(r"\bUHT\b", name):
        return "UHT"
    return None


def get_production(name: str) -> str | None:
    """Detect cheese production type from a product name.

    Returns ``"fermier"`` or ``"laitier"`` or ``None``.
    """
    upper = name.upper()
    if re.search(r"\bFERMIER\b", upper):
        return "fermier"
    if re.search(r"\bLAITIER\b", upper):
        return "laitier"
    return None


_KNOWN_BRANDS = frozenset(
    {
        "U",
        "USAVEURS",
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
        "SCB",
        "NUII",
        "QUAKER",
        "NESTLE",
        "SAMIA",
        "SOIGNON",
        "EUROFOOD",
        "SAUPIQUET",
        "BELCHARD",
        "LU",
        "WHISKAS",
        "MOULIN DE VALDONNE",
        "NUTELLA",
        "FERRERO",
        "FINDUS",
        "PRESIDENT",
        "KIRI",
        "YOPLAIT",
        "BN",
        "LOTUS",
        "MERCUROCHROME",
        "PRIX MINI",
        "LUCOTTE",
        "LE RUSTIQUE",
        "BONNE MAMAN",
        "JACQUET",
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
    (re.compile(r"\bLABEL\b"), "Label Rouge"),
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


_KNOWN_PACKAGING = frozenset(
    {
        "BRIQUE",
        "BOUTEILLE",
        "BOCAL",
        "BOITE",
        "CELLOPHANE",
        "ETUI",
        "VERRE",
        "BARQUETTE",
        "PAQUET",
        "RECHARGE",
    }
)


def get_packaging(name: str) -> str | None:
    """Detect a known packaging type in a product name.

    Only matches full words BRIQUE / BOUTEILLE.  Abbreviations (BK, BL)
    are handled by synonym expansion before this function is called.
    """
    upper = name.upper()
    for pkg in _KNOWN_PACKAGING:
        if re.search(r"\b" + re.escape(pkg) + r"\b", upper):
            return pkg
    return None


def strip_packaging(name: str, packaging: str) -> str:
    """Remove a packaging word from *name* (case-insensitive, whole word)."""
    return re.sub(
        r"\b" + re.escape(packaging) + r"\b", "", name, flags=re.IGNORECASE
    ).strip()


_KNOWN_ORIGINS: dict[str, str] = {
    "FR": "FRANCE",
    "FRA": "FRANCE",
    "FRANCE": "FRANCE",
    "IT": "ITALIE",
    "ITALIA": "ITALIE",
    "ES": "ESPAGNE",
    "SP": "ESPAGNE",
    "ESP": "ESPAGNE",
    "DE SAVOIE": "SAVOIE",
    "SAVOIE": "SAVOIE",
}


def get_origin(name: str) -> tuple[str, str] | None:
    """Detect a known origin in a product name.

    Returns ``(normalized_country, matched_word)`` or ``None``.
    """
    upper = name.upper()
    for word, country in _KNOWN_ORIGINS.items():
        if re.search(r"\b" + re.escape(word) + r"\b", upper):
            return country, word
    return None


def strip_origin(name: str, origin_word: str) -> str:
    """Remove an origin word from *name* (case-insensitive, whole word)."""
    return re.sub(
        r"\b" + re.escape(origin_word) + r"\b", "", name, flags=re.IGNORECASE
    ).strip()


# --- Affinage (cheese aging) ---

_AFFINAGE_MONTHS_PATTERNS: list[re.Pattern[str]] = [
    # "5 MOIS D'AFFINAGE" / "5 MOIS AFFINAGE" / "5MOIS AFFINAGE"
    re.compile(r"\b(\d+)\s*MOIS\s+(?:D')?AFFINAGE\b"),
    # "AFFINE 9 MOIS" / "AFFINÉ 9MOIS"
    re.compile(r"\bAFFIN[EÉ]\s+(\d+)\s*MOIS\b"),
    # "AFFINAGE 12 MOIS" / "AFFINAGE 12MOIS"
    re.compile(r"\bAFFINAGE\s+(\d+)\s*MOIS\b"),
]

# Day-based aging: "50J", "50J.", "50 JOURS"
_AFFINAGE_DAYS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(\d+)\s*J\.?\b"),
    re.compile(r"\b(\d+)\s+JOURS?\b"),
]

_STRIP_AFFINAGE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b\d+\s*MOIS\s+(?:D')?AFFINAGE\b"),
    re.compile(r"\bAFFIN[EÉ]\s+\d+\s*MOIS\b"),
    re.compile(r"\bAFFINAGE\s+\d+\s*MOIS\b"),
    re.compile(r"\b\d+\s*J\.?\b"),
    re.compile(r"\b\d+\s+JOURS?\b"),
]
_STRIP_STANDALONE_MOIS_RE = re.compile(r"\b\d+\s*MOIS\b")


_STANDALONE_MOIS_RE = re.compile(r"\b(\d+)\s*MOIS\b")


def get_affinage_months(name: str, *, cheese: bool = False) -> int | None:
    """Extract cheese aging duration from a product name, in months.

    Matches patterns like ``5 MOIS AFFINAGE``, ``AFFINÉ 9 MOIS``,
    ``AFFINAGE 12 MOIS``, or day-based ``50J`` / ``50 JOURS``
    (converted to months by dividing by 30).
    When *cheese* is ``True``, also matches standalone ``18 MOIS``
    (without an affinage keyword).
    Returns the number of months (rounded) or ``None``.
    """
    upper = name.upper()
    for pattern in _AFFINAGE_MONTHS_PATTERNS:
        m = pattern.search(upper)
        if m:
            return int(m.group(1))
    if cheese:
        m = _STANDALONE_MOIS_RE.search(upper)
        if m:
            return int(m.group(1))
    for pattern in _AFFINAGE_DAYS_PATTERNS:
        m = pattern.search(upper)
        if m:
            return round(int(m.group(1)) / 30)
    return None


def strip_affinage(name: str, *, cheese: bool = False) -> str:
    """Remove affinage patterns from *name*.

    When *cheese* is ``True``, also strips standalone ``N MOIS``.
    """
    for pattern in _STRIP_AFFINAGE_PATTERNS:
        name = pattern.sub("", name)
    if cheese:
        name = _STRIP_STANDALONE_MOIS_RE.sub("", name)
        name = re.sub(r"\bMOIS\b", "", name)
    # Also strip standalone AFFINAGE / AFFINE / AFFINÉ words left behind
    name = re.sub(r"\bAFFINAGE\b", "", name)
    name = re.sub(r"\bAFFIN[EÉ]\b", "", name)
    return re.sub(r"\s+", " ", name).strip()
