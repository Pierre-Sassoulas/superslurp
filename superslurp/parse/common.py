from __future__ import annotations

import dataclasses
import re

from superslurp.compare.normalize import (
    _BABY_DEFINITE_RE,
    expand_synonyms,
    extract_unit_count,
    get_affinage_months,
    get_baby_food_type,
    get_baby_months,
    get_baby_recipe,
    get_brand,
    get_milk_treatment,
    get_origin,
    get_packaging,
    get_production,
    get_quality_label,
    is_bio,
    strip_affinage,
    strip_brand,
    strip_origin,
    strip_packaging,
    strip_quality_label,
)
from superslurp.superslurp_typing import Category, Item, Properties

# ---------------------------------------------------------------------------
# Patterns to strip from name once units have been extracted
# ---------------------------------------------------------------------------
_UNIT_PATTERN = re.compile(
    r"\s*\bX?\d+(?:=\d+)?RLX\b|\s*\bBTEX\d+\b|\s*(?<!\d)X\d+(?:\+\d+OFF)?\b|\s*\b\d+X\d+/\d+\b|\s*\b\d+TR\b|^\d+\s+"
)
# Standalone "+3OFF" left behind after _get_gram strips "7X1KG" from "7X1KG+3OFF"
_OFFERT_PATTERN = re.compile(r"\s*\+\d+OFF\b")
_OFFERT_EXTRACT = re.compile(r"\+(\d+)OFF\b")

_VOLUME_PATTERN = re.compile(
    r"(?P<multiplier>\d+X)?(?P<vol>\d+[,]?\d*)\s*(?P<unit>LITRES?|L|CL|ML)\b",
    re.IGNORECASE,
)
_BARE_LITRE_PATTERN = re.compile(r"\bLITRES?\b", re.IGNORECASE)

_FAT_PCT_PATTERN = re.compile(r"\s*\d+[.,]?\d*%\s*(?:MG|MAT\.?\s*GR\.?)\b")
_BARE_FAT_PCT_RE = re.compile(r"(?<![+\-])(\d+[.,]?\d*)%(?!\s*(?:MG|MAT\.?\s*GR\.?)\b)")
_BARE_FAT_PCT_STRIP = re.compile(
    r"(?<![+\-])\s*\d+[.,]?\d*%(?!\s*(?:MG|MAT\.?\s*GR\.?)\b)"
)

_PACKAGING_ABBREV_RE = re.compile(r"\bBK\b")
_PACKAGING_ABBREV_BL_RE = re.compile(r"\bBL\b")

# ---------------------------------------------------------------------------
# Category sets
# ---------------------------------------------------------------------------
DAIRY_CATEGORIES = frozenset(
    c
    for c in Category
    if any(
        kw in c.value
        for kw in ("FROMAGE", "CREMERIE", "BEURRE", "ULTRA FRAIS", "LAITS")
    )
)

CHEESE_CATEGORIES = frozenset(c for c in Category if "FROMAGE" in c.value)

LIQUID_CATEGORIES = frozenset(
    c
    for c in Category
    if any(
        kw in c.value
        for kw in ("LIQUIDE", "LAIT", "CREMERIE", "BOISSON", "JUS", "SIROP")
    )
)

# ---------------------------------------------------------------------------
# Context synonyms
# ---------------------------------------------------------------------------
_CONTEXT_SYNONYMS: dict[str, dict[frozenset[Category], str]] = {
    "COUL": {
        DAIRY_CATEGORIES: "COULANT",
    },
}
_CONTEXT_SYNONYMS_DEFAULT: dict[str, str] = {
    "COUL": "COULISSANT",
}


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------
def _get_offert(name: str) -> int | None:
    """Extract the free-item count from a '+3OFF' (offert) suffix."""
    m = _OFFERT_EXTRACT.search(name)
    return int(m.group(1)) if m else None


def _get_gram(name: str) -> tuple[str, float | None, int | None]:
    grams = None
    units: int | None = None
    search = re.search(
        r"(?P<multiplier>\d+X)?(?P<grams>\d?[\d+,]?\d+K?GR?(?: ENVIRON)?)"
        r"(?:\+(?P<bonus>\d+)%)?",
        name,
    )
    if search is None:
        return name, None, None
    if (grams_as_str := search.group("grams")) is not None:
        grams_as_str = grams_as_str.replace(" ENVIRON", "")
        multiplier = search.group("multiplier")
        weight_unit_multiplier = 1
        weight_unit = "GR" if "GR" in grams_as_str and "KG" not in grams_as_str else "G"
        if "KG" in grams_as_str:
            weight_unit_multiplier = 1000
            weight_unit = "KG"
        grams_as_str = grams_as_str.replace(weight_unit, "")
        grams = float(grams_as_str.replace(",", ".")) * weight_unit_multiplier
        if multiplier is not None:
            units = int(multiplier[:-1])
            grams *= units
        bonus = search.group("bonus")
        if bonus is not None:
            grams = round(grams * (1 + int(bonus) / 100))
    name = name.replace(search.group(0), "")
    return name.strip(), grams, units


def _get_volume(name: str) -> tuple[str, float | None, int | None]:
    """Extract volume in mL from a product name (e.g. 1L, 75CL, 250ML, 6X1L)."""
    m = _VOLUME_PATTERN.search(name)
    if m is None:
        # Standalone "LITRE" without a number implies 1 litre.
        m_bare = _BARE_LITRE_PATTERN.search(name)
        if m_bare is None:
            return name, None, None
        name = name[: m_bare.start()] + name[m_bare.end() :]
        return re.sub(r"\s+", " ", name).strip(), 1000.0, None
    vol_str = m.group("vol").replace(",", ".")
    vol = float(vol_str)
    unit = m.group("unit").upper()
    if unit in {"L", "LITRE", "LITRES"}:
        vol *= 1000
    elif unit == "CL":
        vol *= 10
    # ML: vol stays as-is
    units: int | None = None
    multiplier = m.group("multiplier")
    if multiplier is not None:
        units = int(multiplier[:-1])
        vol *= units
    name = name.replace(m.group(0), "").strip()
    return name, vol, units


def _get_fat_pct(name: str) -> float | None:
    """Extract fat percentage (%MG or %MAT.GR) from a product name."""
    m = re.search(r"(\d+[.,]?\d*)%\s*(?:MG|MAT\.?\s*GR\.?)\b", name)
    if m is None:
        return None
    return float(m.group(1).replace(",", "."))


def _infer_milk_fat_pct(name: str) -> float | None:
    """Infer fat percentage from milk type descriptors.

    * *Lait entier* → 3.6 %
    * *Lait 1/2 écrémé* / *demi-écrémé* → 1.5 %
    * *Lait écrémé* → 0.5 %
    """
    upper = name.upper()
    if not re.search(r"\bLAIT\b", upper):
        return None
    # Demi-écrémé / 1/2 écrémé — check before plain écrémé
    if re.search(r"\bDEMI[\s-]?ECREM|1/2\s*ECREM", upper):
        return 1.5
    if re.search(r"\bECREM", upper):
        return 0.5
    if re.search(r"\bENTIER\b", upper):
        return 3.6
    return None


@dataclasses.dataclass(slots=True)
class ParsedAttributes:  # pylint: disable=too-many-instance-attributes
    """All attributes extracted from a raw product name."""

    name: str
    grams: float | None
    units: float | None
    fat_pct: float | None
    bio: bool
    milk_treatment: str | None
    volume_ml: float | None
    brand: str | None
    label: str | None
    packaging: str | None
    origin: str | None
    affinage_months: int | None
    production: str | None
    baby_months: int | None
    baby_recipe: str | None

    @property
    def properties(self) -> Properties:  # pylint: disable=too-complex
        """Build a Properties dict, only including truthy values."""
        props: Properties = {}
        if self.bio:
            props["bio"] = True
        if self.milk_treatment is not None:
            props["milk_treatment"] = self.milk_treatment
        if self.production is not None:
            props["production"] = self.production
        if self.brand is not None:
            props["brand"] = self.brand
        if self.label is not None:
            props["label"] = self.label
        if self.packaging is not None:
            props["packaging"] = self.packaging
        if self.origin is not None:
            props["origin"] = self.origin
        if self.affinage_months is not None:
            props["affinage_months"] = self.affinage_months
        if self.baby_months is not None:
            props["baby_months"] = self.baby_months
        if self.baby_recipe is not None:
            props["baby_recipe"] = self.baby_recipe
        return props


def _parse_name_attributes(  # pylint: disable=too-many-locals
    raw_name: str,
    synonyms: dict[str, str] | list[tuple[re.Pattern[str], str]] | None = None,
) -> ParsedAttributes:
    """Extract name, grams, units, fat%, bio, milk, volume, brand, label,
    packaging, origin, affinage, production, baby_months, baby_recipe.

    When *synonyms* is provided, abbreviations are expanded **before**
    any attribute extraction so that patterns like ``%MG LP`` →
    ``%MG LAIT PASTEURISE`` fire before ``%MG`` is stripped.
    """
    if synonyms:
        raw_name = expand_synonyms(raw_name, synonyms)
    name, grams, units_int = _get_gram(raw_name)
    units: float | None = units_int
    offert = _get_offert(name)
    name = _OFFERT_PATTERN.sub("", name).strip()
    if offert and units is not None and grams is not None:
        per_unit = grams / units
        units += offert
        grams = per_unit * units
    # Volume extraction — only when grams not already found
    volume_ml: float | None = None
    if grams is None:
        name, volume_ml, units_from_vol = _get_volume(name)
        if units_from_vol is not None and units is None:
            units = units_from_vol
    if units is None:
        units = extract_unit_count(raw_name)
        if units is not None:
            name = _UNIT_PATTERN.sub("", name).strip()
            name = re.sub(r"^\d+[+/]\d+\s*", "", name).strip()
    fat_pct = _get_fat_pct(name)
    if fat_pct is not None:
        name = _FAT_PCT_PATTERN.sub("", name).strip()
    if fat_pct is None:
        fat_pct = _infer_milk_fat_pct(raw_name)
    (
        name,
        bio,
        milk_treatment,
        production,
        brand,
        label,
        packaging,
        origin,
        affinage_months,
        baby_months,
        baby_recipe,
    ) = _extract_properties(name, raw_name)
    return ParsedAttributes(
        name=name,
        grams=grams,
        units=units,
        fat_pct=fat_pct,
        bio=bio,
        milk_treatment=milk_treatment,
        volume_ml=volume_ml,
        brand=brand,
        label=label,
        packaging=packaging,
        origin=origin,
        affinage_months=affinage_months,
        production=production,
        baby_months=baby_months,
        baby_recipe=baby_recipe,
    )


def _extract_properties(  # pylint: disable=too-many-locals,too-complex,too-many-branches
    name: str, raw_name: str
) -> tuple[
    str,
    bool,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    int | None,
    int | None,
    str | None,
]:
    """Detect bio/milk/production/brand/label/packaging/origin/affinage/baby-age/recipe flags."""
    baby_months = get_baby_months(raw_name) or get_baby_months(name)
    baby_recipe = get_baby_recipe(name) or get_baby_recipe(raw_name)
    bio = is_bio(raw_name)
    if bio:
        name = re.sub(r"\bBIO\b", "", name).strip()
    milk_treatment = get_milk_treatment(raw_name)
    if milk_treatment is not None:
        m = re.search(r"\bLAIT\s+(?:PASTEURISE|CRU\s+THERMISE|CRU|UHT)", name)
        if m and m.start() == 0:
            # LAIT is the product (liquid) — keep it, only strip treatment word
            name = name[: m.start()] + "LAIT" + name[m.end() :]
        elif m:
            # LAIT is a qualifier (cheese, etc.) — strip entirely
            name = name[: m.start()] + name[m.end() :]
        name = re.sub(r"\bTHERMISE\w*", "", name).strip()
        name = re.sub(r"\bPASTEURISE\w*", "", name).strip()
        name = re.sub(r"\b(?:CRU|UHT)\b", "", name).strip()
    production = get_production(raw_name)
    if production is not None:
        name = re.sub(r"\bFERMIER\b", "", name, flags=re.IGNORECASE).strip()
        name = re.sub(r"\bLAITIER\b", "", name, flags=re.IGNORECASE).strip()
    brand = get_brand(raw_name) or get_brand(name)
    if brand is not None:
        stripped = strip_brand(name, brand)
        if stripped:
            name = stripped
    label = get_quality_label(raw_name)
    if label is not None:
        name = strip_quality_label(name)
    packaging = get_packaging(name)
    if packaging is not None:
        name = strip_packaging(name, packaging)
    origin_result = get_origin(name)
    origin: str | None = None
    if origin_result is not None:
        origin, origin_word = origin_result
        name = strip_origin(name, origin_word)
    affinage_months = get_affinage_months(name)
    name = strip_affinage(name)
    # Replace baby food name with normalized type (PLAT BEBE, CEREALES BEBE, LAIT BEBE)
    # Guard against false positives (e.g. "MELANGE EPICES POT" where POT is not baby food)
    if baby_recipe is not None:
        is_baby = baby_months is not None or bool(
            _BABY_DEFINITE_RE.search(raw_name.upper())
        )
        if is_baby:
            baby_type = get_baby_food_type(raw_name) or get_baby_food_type(name)
            if baby_type is not None:
                name = baby_type
    name = re.sub(r"\s+", " ", name).strip()
    return (
        name,
        bio,
        milk_treatment,
        production,
        brand,
        label,
        packaging,
        origin,
        affinage_months,
        baby_months,
        baby_recipe,
    )


# ---------------------------------------------------------------------------
# Post-processing steps (category-aware)
# ---------------------------------------------------------------------------
def extract_bare_fat_pct(item: Item, category: Category) -> None:
    """Extract bare fat % (without MG suffix) for dairy-category items."""
    if category not in DAIRY_CATEGORIES or item["fat_pct"] is not None:
        return
    m = _BARE_FAT_PCT_RE.search(item["name"])
    if m is None:
        return
    item["fat_pct"] = float(m.group(1).replace(",", "."))
    name = _BARE_FAT_PCT_STRIP.sub(" ", item["name"])
    item["name"] = re.sub(r"\s+", " ", name).strip()


def extract_packaging_abbrev(item: Item, category: Category) -> None:
    """Detect BK (brique) / BL (bouteille) abbreviations for liquid-category items with volume."""
    if category not in LIQUID_CATEGORIES:
        return
    if item["volume_ml"] is None:
        return
    if item["properties"].get("packaging") is not None:
        return
    name = item["name"]
    if _PACKAGING_ABBREV_RE.search(name):
        item["properties"]["packaging"] = "BRIQUE"
        item["name"] = _PACKAGING_ABBREV_RE.sub("", name).strip()
        item["name"] = re.sub(r"\s+", " ", item["name"])
    elif _PACKAGING_ABBREV_BL_RE.search(name):
        item["properties"]["packaging"] = "BOUTEILLE"
        item["name"] = _PACKAGING_ABBREV_BL_RE.sub("", name).strip()
        item["name"] = re.sub(r"\s+", " ", item["name"])


def extract_standalone_affinage_months(item: Item, category: Category) -> None:
    """Detect standalone N MOIS as affinage for cheese-category items.

    Also strips the standalone N MOIS from the item name.
    """
    if category not in CHEESE_CATEGORIES:
        return
    if item["properties"].get("affinage_months") is not None:
        return
    months = get_affinage_months(item["raw"], cheese=True)
    if months is not None:
        item["properties"]["affinage_months"] = months
    item["name"] = strip_affinage(item["name"], cheese=True)


def expand_context_synonyms(item: Item, category: Category) -> None:
    """Expand abbreviations whose meaning depends on the receipt category."""
    name = item["name"]
    for abbrev, cat_map in _CONTEXT_SYNONYMS.items():
        if not re.search(r"\b" + re.escape(abbrev) + r"\b", name):
            continue
        replacement = None
        for cats, repl in cat_map.items():
            if category in cats:
                replacement = repl
                break
        if replacement is None:
            replacement = _CONTEXT_SYNONYMS_DEFAULT.get(abbrev)
        if replacement is not None:
            name = re.sub(r"\b" + re.escape(abbrev) + r"\b", replacement, name)
    if name != item["name"]:
        item["name"] = re.sub(r"\s+", " ", name).strip()


# ---------------------------------------------------------------------------
# Item construction & post-processing convenience
# ---------------------------------------------------------------------------
def build_item(  # pylint: disable=too-many-arguments
    *,
    raw: str,
    raw_name: str,
    name: str,
    price: float,
    bought: int,
    units: float | None,
    grams: float | None,
    volume_ml: float | None,
    fat_pct: float | None,
    tr: bool,
    way_of_paying: str | None,
    properties: Properties,
) -> Item:
    """Construct an Item dict."""
    return {
        "raw": raw,
        "raw_name": raw_name,
        "name": name,
        "price": price,
        "bought": bought,
        "units": units,
        "grams": grams,
        "volume_ml": volume_ml,
        "fat_pct": fat_pct,
        "tr": tr,
        "way_of_paying": way_of_paying,
        "discount": None,
        "properties": properties,
    }


def post_process_item(item: Item, category: Category) -> None:
    """Run the 4 category-aware post-processing steps on an item."""
    extract_bare_fat_pct(item, category)
    extract_packaging_abbrev(item, category)
    extract_standalone_affinage_months(item, category)
    expand_context_synonyms(item, category)
