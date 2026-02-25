from __future__ import annotations

import logging
import re
from collections import defaultdict

from superslurp.compare.normalize import (
    expand_synonyms,
    extract_unit_count,
    get_affinage_months,
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
from superslurp.parse.v1.parse_categories import iter_categories_and_items
from superslurp.repr.items import repr_items
from superslurp.superslurp_typing import Category, Item, Items, Properties


class WrongNumberOfItemException(Exception): ...


# Patterns to strip from name once units have been extracted
_UNIT_PATTERN = re.compile(
    r"\s*\bX?\d+(?:=\d+)?RLX\b|\s*\bBTEX\d+\b|\s*(?<!\d)X\d+(?:\+\d+OFF)?\b|\s*\b\d+X\d+/\d+\b|\s*\b\d+TR\b|^\d+\s+"
)
# Standalone "+3OFF" left behind after _get_gram strips "7X1KG" from "7X1KG+3OFF"
_OFFERT_PATTERN = re.compile(r"\s*\+\d+OFF\b")
_OFFERT_EXTRACT = re.compile(r"\+(\d+)OFF\b")


def _get_offert(name: str) -> int | None:
    """Extract the free-item count from a '+3OFF' (offert) suffix."""
    m = _OFFERT_EXTRACT.search(name)
    return int(m.group(1)) if m else None


_NAME_CHAR = r"(?:(?!\(T\))[\w .\/%,=\-\"'€°+Éé()\*])"

items_patterns = [
    re.compile(
        rf"(?P<name>{_NAME_CHAR}*)(?P<tr>\(T\))?(\d\d)?[ \n]*"
        r"(?P<quantity>[\d kgx,.]+ €(\/kg)?)? +(?P<price>\d+[,|\.][ \d€]+) ?(?P<way_of_paying>\d{2})+ ?\n"
        r"|\s*Pourcentage:\s*(?P<pourcentage>\d+)\s*-(?P<discount>\d+[,|\.][ \d€]+)\n"
        r"|\s+[^\n]+-(?P<inline_discount>\d+[,\.]\d+ €)\s*\n"
    ),
    # Weighted items where name + way_of_paying are on line 1, weight + price on line 2
    re.compile(
        rf"(?P<name>{_NAME_CHAR}*)(?P<tr>\(T\))? +(?P<way_of_paying>\d{{2}}) ?\n"
        r"\s+(?P<quantity>[\d,]+ kg\s+x\s+[\d,]+ €/kg)\s+(?P<price>\d+[,|\.]\d+ €)\n"
    ),
]


def parse_items(
    text: str, expected_number_of_items: int, synonyms: dict[str, str] | None = None
) -> Items:
    nb_parsed = 0
    items: dict[Category, list[Item]] = defaultdict(list)
    category = Category.UNDEFINED
    for category, items_info in iter_categories_and_items(text):
        nb_parsed_category = 0
        for items_pattern in items_patterns:
            logging.debug(
                f"Parsing {category=} with {items_pattern}:\n<\n{items_info}\n>"
            )
            if not (matched_items := items_pattern.finditer(items_info)):
                logging.debug(f"Matched nothing with {items_pattern}")
                continue
            for item_info in matched_items:
                logging.debug(f"Item found in {category}: {item_info}")
                discount_str = _get_discount(item_info)
                if discount_str is not None:
                    items[category][-1]["discount"] = _get_price(discount_str)
                    continue
                item = get_item_from_item_infos(item_info, synonyms=synonyms)
                extract_bare_fat_pct(item, category)
                extract_packaging_abbrev(item, category)
                extract_standalone_affinage_months(item, category)
                expand_context_synonyms(item, category)
                nb_parsed_category += item["bought"]
                items[category].append(item)
        if nb_parsed_category == 0:
            err_msg = (
                f"No items found in {category}, that's impossible.\n"
                f"In:\n<\n{items_info}\n>\nnothing matched by {items_patterns!r}"
            )
            logging.error(err_msg)
            raise WrongNumberOfItemException(err_msg)
        nb_parsed += nb_parsed_category
    if nb_parsed != expected_number_of_items:
        err_msg = (
            f"Expected {expected_number_of_items} items not {nb_parsed} in\n{text}\n"
            f"But parsing extracted:\n{repr_items(items)}\n"
            f"Pre-parsing of categories was:\n{category}"
        )
        logging.error(err_msg)
        raise WrongNumberOfItemException(err_msg)
    return items


def get_new_category(line: str) -> Category:
    try:
        return Category(line.replace(">>>>", "").strip())
    except ValueError as e:
        raise ValueError(f"Missing value in enum '{Category!r}': {e}") from e


def _parse_name_grams_units(
    raw_name: str,
) -> tuple[str, float | None, float | None]:
    """Extract clean name, grams and units from a raw product name."""
    (
        name,
        grams,
        units,
        _fat,
        _bio,
        _milk,
        _vol,
        _brand,
        _label,
        _pkg,
        _orig,
        _aff,
        _prod,
    ) = _parse_name_attributes(raw_name)
    return name, grams, units


def _parse_name_attributes(  # pylint: disable=too-many-locals
    raw_name: str,
    synonyms: dict[str, str] | None = None,
) -> tuple[
    str,
    float | None,
    float | None,
    float | None,
    bool,
    str | None,
    float | None,
    str | None,
    str | None,
    str | None,
    str | None,
    int | None,
    str | None,
]:
    """Extract name, grams, units, fat%, bio, milk, volume, brand, label, packaging, origin, affinage, production.

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
    ) = _extract_properties(name, raw_name)
    return (
        name,
        grams,
        units,
        fat_pct,
        bio,
        milk_treatment,
        volume_ml,
        brand,
        label,
        packaging,
        origin,
        affinage_months,
        production,
    )


def _extract_properties(
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
]:
    """Detect bio/milk/production/brand/label/packaging/origin/affinage flags and strip them from *name*."""
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
        name = strip_brand(name, brand)
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
    )


def build_properties(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    bio: bool,
    milk_treatment: str | None,
    brand: str | None = None,
    label: str | None = None,
    packaging: str | None = None,
    origin: str | None = None,
    affinage_months: int | None = None,
    production: str | None = None,
) -> Properties:
    """Build a Properties dict, only including truthy values."""
    props: Properties = {}
    if bio:
        props["bio"] = True
    if milk_treatment is not None:
        props["milk_treatment"] = milk_treatment
    if production is not None:
        props["production"] = production
    if brand is not None:
        props["brand"] = brand
    if label is not None:
        props["label"] = label
    if packaging is not None:
        props["packaging"] = packaging
    if origin is not None:
        props["origin"] = origin
    if affinage_months is not None:
        props["affinage_months"] = affinage_months
    return props


def get_item_from_item_infos(  # pylint: disable=too-many-locals
    item_info: re.Match[str], synonyms: dict[str, str] | None = None
) -> Item:
    if (matched_name := item_info.group("name")) is None:
        raise ValueError(f"Nothing matched the name in {item_info}")
    raw_name = matched_name.strip()
    assert raw_name, f"Name is empty: {raw_name}"
    if len(raw_name) < 10:
        logging.warning(f"Name is really short, that suspicious: {raw_name}")
    (
        name,
        grams,
        units,
        fat_pct,
        bio,
        milk_treatment,
        volume_ml,
        brand,
        label,
        packaging,
        origin,
        affinage_months,
        production,
    ) = _parse_name_attributes(raw_name, synonyms=synonyms)
    quantity_str = item_info.group("quantity")
    if grams is None and quantity_str and "kg" in quantity_str:
        grams = _get_grams_from_quantity(quantity_str)
    if (quantity := _parse_quantity(quantity_str)) == 1:
        price = item_info.group("price")
    else:
        price = item_info.group("quantity").split("x")[1]
    tr = item_info.group("tr")
    way_of_paying = item_info.group("way_of_paying")
    item: Item = {
        "raw": item_info.group(0).strip(),
        "raw_name": raw_name,
        "name": name,
        "price": _get_price(price),
        "bought": quantity,
        "units": units,
        "grams": grams,
        "volume_ml": volume_ml,
        "fat_pct": fat_pct,
        "tr": _get_tr(tr),
        "way_of_paying": way_of_paying,
        "discount": None,
        "properties": build_properties(
            bio,
            milk_treatment,
            brand,
            label,
            packaging,
            origin,
            affinage_months,
            production,
        ),
    }
    return item


def _parse_quantity(quantity: str | None) -> int:
    if quantity is None:
        return 1
    quantity = quantity.strip()
    if " x" in quantity:
        before_x = quantity.split(" x")[0].strip()
        if "kg" in before_x:
            return 1
        return int(before_x)
    return int(quantity)


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


_VOLUME_PATTERN = re.compile(
    r"(?P<multiplier>\d+X)?(?P<vol>\d+[,]?\d*)\s*(?P<unit>LITRES?|L|CL|ML)\b",
    re.IGNORECASE,
)


_BARE_LITRE_PATTERN = re.compile(r"\bLITRES?\b", re.IGNORECASE)


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


_FAT_PCT_PATTERN = re.compile(r"\s*\d+[.,]?\d*%\s*(?:MG|MAT\.?\s*GR\.?)\b")
_BARE_FAT_PCT_RE = re.compile(r"(?<![+\-])(\d+[.,]?\d*)%(?!\s*(?:MG|MAT\.?\s*GR\.?)\b)")
_BARE_FAT_PCT_STRIP = re.compile(
    r"(?<![+\-])\s*\d+[.,]?\d*%(?!\s*(?:MG|MAT\.?\s*GR\.?)\b)"
)

DAIRY_CATEGORIES = frozenset(
    c
    for c in Category
    if any(
        kw in c.value
        for kw in ("FROMAGE", "CREMERIE", "BEURRE", "ULTRA FRAIS", "LAITS")
    )
)

CHEESE_CATEGORIES = frozenset(c for c in Category if "FROMAGE" in c.value)


_PACKAGING_ABBREV_RE = re.compile(r"\bBK\b")
_PACKAGING_ABBREV_BL_RE = re.compile(r"\bBL\b")

LIQUID_CATEGORIES = frozenset(
    c
    for c in Category
    if any(
        kw in c.value
        for kw in ("LIQUIDE", "LAIT", "CREMERIE", "BOISSON", "JUS", "SIROP")
    )
)


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


_CONTEXT_SYNONYMS: dict[str, dict[frozenset[Category], str]] = {
    "COUL": {
        DAIRY_CATEGORIES: "COULANT",
    },
}
_CONTEXT_SYNONYMS_DEFAULT: dict[str, str] = {
    "COUL": "COULISSANT",
}


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


def _get_grams_from_quantity(quantity_str: str) -> float | None:
    """Extract grams from a weighted quantity string like '0,980 kg  x  3,75 €/kg'."""
    match = re.search(r"([\d,]+)\s*kg", quantity_str)
    if match is None:
        return None
    return float(match.group(1).replace(",", ".")) * 1000


def _get_discount(item_info: re.Match[str]) -> str | None:
    for group_name in ("discount", "inline_discount"):
        try:
            value = item_info.group(group_name)
        except IndexError:
            continue
        if value is not None:
            return value
    return None


def _get_price(price: str) -> float:
    price = price.split(" €")[0].replace(",", ".")
    return float(price)


def _get_tr(tr: str) -> bool:
    return tr == "(T)"


def get_items_infos_from_line(line: str) -> list[str]:
    items_info = [word.strip() for word in line.split("  ")]
    items_info = [word for word in items_info if word]
    return items_info
