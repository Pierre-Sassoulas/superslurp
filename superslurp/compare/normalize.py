from __future__ import annotations

import re
import unicodedata
from typing import NamedTuple

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
        "TUB",
        "BRIQUE",
        "BOUTEILLE",
        "BOCAL",
        "BOITE",
        "CELLOPHANE",
        "ETUI",
        "VERRE",
        "PAQUET",
        "TUBE",
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
        # Baby food internal codes
        "UTP",
        "UTPB",
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
_STRIP_BABY_AGE = re.compile(r"\bDES\s+\d+(/\d+)?\s*M\b|\b\d+(/\d+)?\s*M\b")
_BABY_AGE_EXTRACT = re.compile(r"\b(?:DES\s+)?(\d+)(?:/\d+)?\s*M\b")


def get_baby_months(name: str) -> int | None:
    """Extract the minimum baby age in months from a product name.

    Matches patterns like ``6M``, ``8M``, ``4/6M``, ``15/36M``, ``DES 12M``.
    For fractional ages (4/6M) returns the first (minimum) number.
    Returns ``None`` if no baby age found.
    """
    m = _BABY_AGE_EXTRACT.search(name.upper())
    if m:
        return int(m.group(1))
    return None


# Baby food sub-brands → type-specific placeholders (applied before word stripping)
_BABY_FOOD_REPLACEMENTS: dict[str, str] = {
    "BLEDICHEF": "PLAT BEBE",
    "BLEDINER": "PLAT BEBE",
    "BLEDINE": "CEREALES BEBE",
    "BLEDILAIT": "LAIT BEBE",
    "ASSIETTE": "PLAT BEBE",
    "BOL": "PLAT BEBE",
    "BOLS": "PLAT BEBE",
    "POT": "PLAT BEBE",
    "POTS": "PLAT BEBE",
}
_BABY_FOOD_RE = re.compile(r"\b(?:" + "|".join(_BABY_FOOD_REPLACEMENTS) + r")\b")
_BABY_PLACEHOLDER_SET = frozenset(_BABY_FOOD_REPLACEMENTS.values())
# Pattern to strip baby-food keywords, brands, age, and codes from a name to get the recipe
_BABY_RECIPE_STRIP = re.compile(
    r"\b(?:"
    + "|".join(sorted(_BABY_FOOD_REPLACEMENTS.keys(), key=len, reverse=True))
    + r")\b"
    + r"|\b(?:BLEDINA|LRB)\b"
    + r"|\b(?:UTP|UTPB)\b"
    + r"|\bDES\s+\d+(?:/\d+)?\s*M\b|\b\d+(?:/\d+)?\s*M\b"
    + r"|\bBIO\b"
)
# Keywords that definitively identify baby food (vs false positives like "EPICES POT")
_BABY_DEFINITE_RE = re.compile(r"\b(?:BLEDICHEF|BLEDINER|BLEDINE|BLEDILAIT)\b")
_BABY_DOT_PREFIX = re.compile(r"^(?:BOLS?|POTS?)\.")
# Precompiled baby placeholder dedup patterns for normalize_for_matching
_BABY_PLACEHOLDER_DEDUP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"({re.escape(p)})(\s+\1)+"), p) for p in _BABY_PLACEHOLDER_SET
]


def get_baby_recipe(name: str) -> str | None:
    """Extract baby food recipe/content from a product name.

    Returns the food description after stripping baby food keywords
    (BLEDICHEF, BOL, etc.), brands (BLEDINA, LRB), age suffixes,
    internal codes, and BIO.
    Returns ``None`` if no baby food keyword found.
    """
    upper = name.upper()
    if not (_BABY_FOOD_RE.search(upper) or _BABY_DOT_PREFIX.match(upper)):
        return None
    result = _BABY_RECIPE_STRIP.sub("", upper)
    result = _BABY_DOT_PREFIX.sub("", result)
    # Clean up dots/whitespace
    result = re.sub(r"^\s*\.?\s*", "", result)
    result = re.sub(r"\s+", " ", result).strip()
    return result if result else None


def get_baby_food_type(name: str) -> str | None:
    """Return the normalized baby food type for a product name.

    Returns ``"PLAT BEBE"``, ``"CEREALES BEBE"``, or ``"LAIT BEBE"``
    based on which baby food keyword is found in *name*.
    Returns ``None`` if no keyword matches.
    """
    upper = name.upper()
    for keyword, placeholder in _BABY_FOOD_REPLACEMENTS.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", upper):
            return placeholder
    if _BABY_DOT_PREFIX.match(upper):
        return "PLAT BEBE"
    return None


_LEADING_COUNT = re.compile(r"^\d+\s+")
# Precompiled accent-stripping pattern (matches combining marks after NFD decomposition)
_COMBINING_MARKS = re.compile(r"[\u0300-\u036f]+")
# Precompiled whitespace collapse
_MULTI_SPACE = re.compile(r"\s+")
# Precompiled OEUFS normalization
_OEUFS_NORM = re.compile(r"\bOEUF\b")
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
# Combined stripping regex: merges _STRIP_PHRASE, _STRIP_COUNT_PATTERN, _STRIP_VOLUME,
# _STRIP_UNIT_COUNT, _LEADING_ARITH, _LEADING_COUNT, _STRIP_BABY_AGE,
# _STRIP_AFFINAGE_NORM into a single pass (7 regex subs → 1).
_STRIP_ALL = re.compile(
    # Leading arithmetic like "3+1 " or "1/2 " (must be before _LEADING_COUNT)
    r"^\d+[+/]\d+\s*"
    # Leading count like "18 "
    r"|^\d+\s+"
    # Milk treatment phrases
    r"|\bLAIT\s+(?:PASTEURISE|CRU\s+THERMISE|CRU|UHT)\b"
    # Count patterns like "3 TETES"
    r"|\b\d+\s*TETES\b"
    # Volume patterns like 1L, 75CL, 250ML, 6X1L
    r"|\b(?:\d+X)?\d+,?\d*\s*(?:LITRES?|L|CL|ML)\b|\bLITRES?\b"
    # Unit count patterns like X12, BTEX12, X10+5OFF, 6TR, 4=12RLX
    r"|\bX?\d+(?:=\d+)?RLX\b|\bBTEX\d+\b|\bX\s\d+(?:\+\d+OFF)?\b"
    r"|(?<!\d)X\d+(?:\+\d+OFF)?\b|\b\d+X\d+/\d+\b|\b\d+TR\b"
    # Baby-food age suffixes like 6M, 8M, 4/6M, DES 12M
    r"|\bDES\s+\d+(?:/\d+)?\s*M\b|\b\d+(?:/\d+)?\s*M\b"
    # Affinage patterns
    r"|\b\d+\s*MOIS\s+(?:D')?AFFINAGE\b"
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


class CompiledSynonyms(NamedTuple):
    """Pre-compiled synonym patterns split into multi-word (sequential) and
    single-word (single alternation regex with dict callback) for performance.
    """

    multi_word: list[tuple[re.Pattern[str], str]]
    single_word_re: re.Pattern[str] | None
    single_word_map: dict[str, str]


def compile_synonyms(
    synonyms: dict[str, str],
) -> CompiledSynonyms:
    """Pre-compile synonym dict into a structure optimised for fast expansion.

    Single-word synonyms are collapsed into one alternation regex with a
    dict callback, reducing per-item cost from O(N) regex subs to O(1).
    Multi-word synonyms are kept as sequential patterns (order matters).

    Call once per synonym dict, then pass the result to :func:`expand_synonyms`.
    """
    multi_word: list[tuple[re.Pattern[str], str]] = []
    single_word_map: dict[str, str] = {}

    for pattern, replacement in synonyms.items():
        pat = pattern.replace(".", " ").strip()
        if not pat:
            continue
        words = pat.split()
        if len(words) > 1:
            escaped_words = [re.escape(w) for w in words]
            regex = (
                r"(?:(?<=[\s.])|(?<=^)|(?<=\b))"
                + r"[.\s]+".join(escaped_words)
                + r"(?=[\s.\d]|$|\b)"
            )
            multi_word.append((re.compile(regex, re.IGNORECASE), replacement))
        else:
            single_word_map[pat.upper()] = replacement

    # Build one alternation regex for all single-word synonyms (longest first
    # so that e.g. "BLEDIN" matches before "BLED" at the regex level).
    single_word_re: re.Pattern[str] | None = None
    if single_word_map:
        alts = sorted(single_word_map, key=len, reverse=True)
        alt_pattern = "|".join(re.escape(a) for a in alts)
        single_word_re = re.compile(
            r"(?:(?<=[\s.])|(?<=^)|(?<=\b))"
            + rf"({alt_pattern})"
            + r"(?=[\s.\d]|$|\b)",
            re.IGNORECASE,
        )

    return CompiledSynonyms(multi_word, single_word_re, single_word_map)


def expand_synonyms(
    name: str,
    synonyms: dict[str, str] | CompiledSynonyms,
) -> str:
    """Expand abbreviations in a product name using an ordered synonym dict.

    Keys are patterns, values are replacements.  Iteration order matters:
    multi-word patterns (e.g. ``"CHOCO PATIS": "CHOCOLAT PATISSIER"``) placed
    before single-word fallbacks (``"PATIS": "PATISSERIE"``) take priority.

    Dots and spaces are both treated as word separators, so ``CHOCO.PATIS``
    and ``FROM.BLC`` match their synonym keys.  Dots are replaced by spaces
    only **after** all synonyms have been applied.

    *synonyms* can be either a raw ``dict[str, str]`` (compiled on the fly)
    or a pre-compiled :class:`CompiledSynonyms` from :func:`compile_synonyms`
    (much faster when called repeatedly).
    """
    if isinstance(synonyms, dict):
        compiled = compile_synonyms(synonyms)
    else:
        compiled = synonyms
    # Multi-word patterns first (order matters: they take priority)
    for pattern, replacement in compiled.multi_word:
        name = pattern.sub(replacement, name)
    # Single-word patterns in one pass via alternation regex
    if compiled.single_word_re is not None:
        lookup = compiled.single_word_map
        name = compiled.single_word_re.sub(lambda m: lookup[m.group(1).upper()], name)
    name = name.replace(".", " ")
    return _MULTI_SPACE.sub(" ", name).strip()


def normalize_for_matching(
    name: str,
    synonyms: dict[str, str] | CompiledSynonyms | None = None,
) -> str:
    """Normalize a product name for fuzzy matching.

    Uppercase, strip accents, collapse whitespace, remove common qualifiers
    (color, packaging, origin, brand, BIO).
    """
    name = name.upper().strip()
    # Strip accents via NFD decomposition + removing combining marks
    name = _COMBINING_MARKS.sub("", unicodedata.normalize("NFD", name))
    # Expand synonyms (also normalizes dots to spaces)
    if synonyms:
        name = expand_synonyms(name, synonyms)
    # Normalize dots to spaces (in case no synonyms)
    name = name.replace(".", " ")
    # Strip all quantitative/qualifier patterns in a single regex pass:
    # milk phrases, TETES, volumes, unit counts, leading arith/count,
    # baby-food ages, affinage durations.
    name = _STRIP_ALL.sub("", name)
    # Replace baby-food sub-brands with type-specific placeholders
    name = _BABY_FOOD_RE.sub(lambda m: _BABY_FOOD_REPLACEMENTS[m.group()], name)
    # Collapse duplicate placeholders (e.g. "BLEDICHEF ASSIETTE" → "PLAT BEBE PLAT BEBE")
    for pattern, placeholder in _BABY_PLACEHOLDER_DEDUP:
        name = pattern.sub(placeholder, name)
    # Strip content after baby-food placeholder — group all PLAT BEBE together
    for placeholder in _BABY_PLACEHOLDER_SET:
        if placeholder in name:
            name = name[: name.index(placeholder) + len(placeholder)]
            break
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
    name = _MULTI_SPACE.sub(" ", name).strip()
    # Normalize common singular/plural
    name = _OEUFS_NORM.sub("OEUFS", name)
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
        "ALSA",
        "ANDROS",
        "ARBRE VERT",
        "BELCHARD",
        "BLEDINA",
        "BN",
        "BONNE MAMAN",
        "BOSCH",
        "BOUNTY",
        "BRETS",
        "CAMBRAS",
        "CASA AZZURRA",
        "CELEBRATION",
        "CHAMPOMY",
        "CORSICA",
        "DANETTE",
        "DAUCY",
        "ERMITAGE",
        "EUROFOOD",
        "EXTREME",
        "FERRERO",
        "FINDUS",
        "FOL EPI",
        "FRANCINE",
        "FREEDENT",
        "GALBANI",
        "HIPP",
        "INNOCENT",
        "JACQUET",
        "JORDAN",
        "KAMBLY",
        "KIKKOMAN",
        "KINDER",
        "KIRI",
        "LACTEL",
        "LE RUSTIQUE",
        "LORINA",
        "LOTUS",
        "LU",
        "LUCOTTE",
        "MAGGI",
        "MAGNUM",
        "MARS",
        "MEDICAID",
        "MERCUROCHROME",
        "MOULIN DE VALDONNE",
        "NANA",
        "NESTLE",
        "NUII",
        "NUTELLA",
        "OASIS",
        "OISHIYA",
        "PANZANI",
        "PASQUIER",
        "PHILIPS",
        "PIRULO",
        "POKEMON",
        "PRESIDENT",
        "PRIX MINI",
        "QUAKER",
        "RICOLA",
        "RICHESMONTS",
        "ROITELET",
        "SAINT MICHEL",
        "SALINOR",
        "SAMIA",
        "SAUPIQUET",
        "SCB",
        "SCHLEICH",
        "SNICKERS",
        "SODEBO",
        "SOIGNON",
        "SUN",
        "SUZI-WAN",
        "TEFAL",
        "TIGEX",
        "TRAMIER",
        "U",
        "UHU",
        "USAVEURS",
        "VAHINE",
        "VANHOUTEN",
        "VANIA",
        "WHISKAS",
        "YOPLAIT",
    }
)


_KNOWN_BRANDS_RE = re.compile(
    r"\b(?:"
    + "|".join(re.escape(b) for b in sorted(_KNOWN_BRANDS, key=len, reverse=True))
    + r")\b"
)


def get_brand(name: str) -> str | None:
    """Detect a known brand in a product name.

    When multiple brands match (e.g. ``MARS`` + ``U`` in a laundry product),
    the **rightmost** match is returned — in receipt names the actual product
    brand appears after the description, before the quantity info.
    """
    matches = list(_KNOWN_BRANDS_RE.finditer(name.upper()))
    if not matches:
        return None
    return matches[-1].group(0)


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
    return _MULTI_SPACE.sub(" ", name).strip()


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
        "TUB",
        "TUBE",
        "RECHARGE",
    }
)

# Map abbreviations to canonical packaging name for get_packaging()
_PACKAGING_ALIASES: dict[str, str] = {
    "TUB": "TUBE",
}

# Build a single alternation regex for packaging detection.  Aliases first
# (sorted longest-first), then canonical names (sorted longest-first).
_PACKAGING_ALL_WORDS = sorted(
    list(_PACKAGING_ALIASES) + list(_KNOWN_PACKAGING), key=len, reverse=True
)
_PACKAGING_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _PACKAGING_ALL_WORDS) + r")\b"
)
# Lookup: word → canonical name (aliases map to their canonical, rest map to self)
_PACKAGING_LOOKUP: dict[str, str] = {pkg: pkg for pkg in _KNOWN_PACKAGING}
_PACKAGING_LOOKUP.update(_PACKAGING_ALIASES)


def get_packaging(name: str) -> str | None:
    """Detect a known packaging type in a product name.

    Only matches full words BRIQUE / BOUTEILLE.  Abbreviations (BK, BL)
    are handled by synonym expansion before this function is called.
    Aliases like TUB → TUBE are resolved to the canonical name.
    """
    m = _PACKAGING_RE.search(name.upper())
    if m is None:
        return None
    return _PACKAGING_LOOKUP[m.group(1)]


def strip_packaging(name: str, packaging: str) -> str:
    """Remove a packaging word from *name* (case-insensitive, whole word).

    Also strips any alias that maps to *packaging* (e.g. TUB for TUBE).
    """
    name = re.sub(r"\b" + re.escape(packaging) + r"\b", "", name, flags=re.IGNORECASE)
    for alias, canonical in _PACKAGING_ALIASES.items():
        if canonical == packaging:
            name = re.sub(
                r"\b" + re.escape(alias) + r"\b", "", name, flags=re.IGNORECASE
            )
    return name.strip()


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


_ORIGIN_RE = re.compile(
    r"\b("
    + "|".join(re.escape(w) for w in sorted(_KNOWN_ORIGINS, key=len, reverse=True))
    + r")\b"
)


def get_origin(name: str) -> tuple[str, str] | None:
    """Detect a known origin in a product name.

    Returns ``(normalized_country, matched_word)`` or ``None``.
    """
    m = _ORIGIN_RE.search(name.upper())
    if m is None:
        return None
    word = m.group(1)
    return _KNOWN_ORIGINS[word], word


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
