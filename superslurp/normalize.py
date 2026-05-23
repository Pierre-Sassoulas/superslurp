"""Match-string normalization. Strips quantitative/qualifier tokens from a
product name and returns a canonical form used by :class:`FuzzyMatcher`.

Compare-side only. Property extraction and shared vocabulary live in
``superslurp.attributes``."""

# `_STRIP_WORDS` below repeats packaging words from `attributes._KNOWN_PACKAGING`
# by design — strip set is a superset (also FILET / SACHET / VRAC / BTE) matched
# as plain tokens, not via the alias-aware extractor regex.
# pylint: disable=duplicate-code

from __future__ import annotations

import re
import unicodedata

from superslurp.attributes import (
    _BABY_FOOD_RE,
    _BABY_FOOD_REPLACEMENTS,
    _MULTI_SPACE,
    CompiledSynonyms,
    expand_synonyms,
)

__all__ = ["normalize_for_matching"]

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

# Precompiled accent-stripping pattern (matches combining marks after NFD decomposition)
_COMBINING_MARKS = re.compile(r"[̀-ͯ]+")
# Precompiled OEUFS normalization
_OEUFS_NORM = re.compile(r"\bOEUF\b")

# Combined stripping regex: merges milk phrases, TETES, volumes, unit counts,
# leading arith/count, baby-food ages, affinage durations into a single pass
# (7 regex subs → 1).
_STRIP_ALL = re.compile(
    # Leading arithmetic like "3+1 " or "1/2 " (must be before the count below)
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

# Set of baby-food placeholders used to truncate names after the placeholder.
_BABY_PLACEHOLDER_SET = frozenset(_BABY_FOOD_REPLACEMENTS.values())
# Precompiled baby placeholder dedup patterns for normalize_for_matching
_BABY_PLACEHOLDER_DEDUP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"({re.escape(p)})(\s+\1)+"), p) for p in _BABY_PLACEHOLDER_SET
]


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
