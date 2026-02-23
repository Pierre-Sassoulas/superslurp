from __future__ import annotations

import logging
import re
from collections import defaultdict

from superslurp.compare.normalize import (
    expand_synonyms,
    extract_unit_count,
    get_milk_treatment,
    is_bio,
)
from superslurp.parse.v1.parse_categories import iter_categories_and_items
from superslurp.repr.items import repr_items
from superslurp.superslurp_typing import Category, Item, Items


class WrongNumberOfItemException(Exception): ...


# Patterns to strip from name once units have been extracted
_UNIT_PATTERN = re.compile(
    r"\s*\bX?\d+(?:=\d+)?RLX\b|\s*\bBTEX\d+\b|\s*\bX\d+(?:\+\d+OFF)?\b|\s*\b\d+TR\b|^\d+\s+"
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
) -> tuple[str, float | None, int | None]:
    """Extract clean name, grams and units from a raw product name."""
    name, grams, units, _fat_pct, _bio, _milk = _parse_name_attributes(raw_name)
    return name, grams, units


def _parse_name_attributes(
    raw_name: str,
    synonyms: dict[str, str] | None = None,
) -> tuple[str, float | None, int | None, float | None, bool, str | None]:
    """Extract clean name, grams, units, fat %, bio and milk treatment.

    When *synonyms* is provided, abbreviations are expanded **before**
    any attribute extraction so that patterns like ``%MG LP`` →
    ``%MG LAIT PASTEURISE`` fire before ``%MG`` is stripped.
    """
    if synonyms:
        raw_name = expand_synonyms(raw_name, synonyms)
    name, grams, units = _get_gram(raw_name)
    offert = _get_offert(name)
    name = _OFFERT_PATTERN.sub("", name).strip()
    if offert and units is not None and grams is not None:
        per_unit = grams / units
        units += offert
        grams = per_unit * units
    if units is None:
        units = extract_unit_count(raw_name)
        if units is not None:
            name = _UNIT_PATTERN.sub("", name).strip()
    fat_pct = _get_fat_pct(name)
    if fat_pct is not None:
        name = _FAT_PCT_PATTERN.sub("", name).strip()
    bio = is_bio(raw_name)
    milk_treatment = get_milk_treatment(raw_name)
    return name, grams, units, fat_pct, bio, milk_treatment


def get_item_from_item_infos(  # pylint: disable=too-many-locals
    item_info: re.Match[str], synonyms: dict[str, str] | None = None
) -> Item:
    if (matched_name := item_info.group("name")) is None:
        raise ValueError(f"Nothing matched the name in {item_info}")
    raw_name = matched_name.strip()
    assert raw_name, f"Name is empty: {raw_name}"
    if len(raw_name) < 10:
        logging.warning(f"Name is really short, that suspicious: {raw_name}")
    name, grams, units, fat_pct, bio, milk_treatment = _parse_name_attributes(
        raw_name, synonyms=synonyms
    )
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
        "fat_pct": fat_pct,
        "tr": _get_tr(tr),
        "way_of_paying": way_of_paying,
        "discount": None,
        "bio": bio,
        "milk_treatment": milk_treatment,
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
        r"(?P<multiplier>\d+X)?(?P<grams>\d?[\d+,]?\d+K?G(?: ENVIRON)?)", name
    )
    if search is None:
        return name, None, None
    if (grams_as_str := search.group("grams")) is not None:
        grams_as_str = grams_as_str.replace(" ENVIRON", "")
        multiplier = search.group("multiplier")
        weight_unit_multiplier = 1
        weight_unit = "G"
        if "KG" in grams_as_str:
            weight_unit_multiplier = 1000
            weight_unit = "KG"
        grams_as_str = grams_as_str.replace(weight_unit, "")
        grams = float(grams_as_str.replace(",", ".")) * weight_unit_multiplier
        if multiplier is not None:
            units = int(multiplier[:-1])
            grams *= units
    name = name.replace(search.group(0), "")
    return name.strip(), grams, units


_FAT_PCT_PATTERN = re.compile(r"\s*\d+[.,]?\d*%\s*MG\b")


def _get_fat_pct(name: str) -> float | None:
    """Extract fat percentage (%MG) from a product name."""
    m = re.search(r"(\d+[.,]?\d*)%\s*MG\b", name)
    if m is None:
        return None
    return float(m.group(1).replace(",", "."))


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
