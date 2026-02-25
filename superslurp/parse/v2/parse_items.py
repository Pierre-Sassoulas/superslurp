from __future__ import annotations

import re
from collections import defaultdict

from superslurp.parse.v1.parse_items import (
    _parse_name_attributes,
    build_properties,
    extract_bare_fat_pct,
    extract_packaging_abbrev,
)
from superslurp.superslurp_typing import Category, Item, Items

ITEM_PATTERN = re.compile(r"^(.+?)\s{2,}(\(T\)\s+)?([\d,]+ €)\s+(\d{2})\s*$")
QUANTITY_PATTERN = re.compile(r"^\s+(\d+) x\s+([\d,]+) EUR\s*$")
WEIGHT_PATTERN = re.compile(r"^\s+([\d,]+) kg x\s+([\d,]+)\s+€/kg\s*$")
DISCOUNT_PATTERN = re.compile(r"^Rem\. Article (\d+)%\s+-([\d,]+) €\s*$")
PESEE_PATTERN = re.compile(r"^\s+Pesée manuelle\s*$")
CATEGORY_PATTERN = re.compile(r"^[A-Z][A-Z0-9 .()\-]+\s*$")


def parse_items_v2(  # pylint: disable=too-many-locals
    items_text: str,
    expected_number_of_items: int,
    synonyms: dict[str, str] | None = None,
) -> tuple[Items, float]:
    items: dict[Category, list[Item]] = defaultdict(list)
    total_discount = 0.0
    category = Category.UNDEFINED
    last_item: Item | None = None
    nb_parsed = 0

    lines = items_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if m := DISCOUNT_PATTERN.match(line):
            discount_price = _parse_price(m.group(2))
            total_discount -= discount_price
            if last_item is None:
                raise ValueError("Discount line found before any item")
            last_item["discount"] = discount_price  # pylint: disable=unsupported-assignment-operation
            i += 1
            continue

        if (
            PESEE_PATTERN.match(line)
            or QUANTITY_PATTERN.match(line)
            or WEIGHT_PATTERN.match(line)
        ):
            i += 1
            continue

        if m := ITEM_PATTERN.match(line):
            raw_name = m.group(1).strip()
            tr = m.group(2) is not None
            total_price = _parse_price(m.group(3).replace(" €", ""))
            way_of_paying = m.group(4)

            quantity, unit_price, grams_from_weight = _parse_detail_lines(lines, i + 1)

            (
                name,
                grams_from_name,
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
            ) = _parse_name_attributes(raw_name, synonyms=synonyms)
            grams = (
                grams_from_weight if grams_from_weight is not None else grams_from_name
            )

            if quantity > 1:
                price = unit_price if unit_price is not None else total_price
            else:
                price = total_price

            item: Item = {
                "raw": line.strip(),
                "raw_name": raw_name,
                "name": name,
                "price": price,
                "bought": quantity,
                "units": units,
                "grams": grams,
                "volume_ml": volume_ml,
                "fat_pct": fat_pct,
                "tr": tr,
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
                ),
            }
            extract_bare_fat_pct(item, category)
            extract_packaging_abbrev(item, category)
            items[category].append(item)
            last_item = item
            nb_parsed += quantity
            i += 1
            continue

        if CATEGORY_PATTERN.match(line):
            category = _parse_category(line)
        i += 1

    if nb_parsed != expected_number_of_items:
        raise ValueError(
            f"Expected {expected_number_of_items} items but parsed {nb_parsed}"
        )

    return items, total_discount


def _parse_detail_lines(
    lines: list[str], start: int
) -> tuple[int, float | None, float | None]:
    quantity = 1
    unit_price: float | None = None
    grams: float | None = None

    i = start
    while i < len(lines):
        line = lines[i]
        if PESEE_PATTERN.match(line):
            i += 1
            continue
        if m := QUANTITY_PATTERN.match(line):
            quantity = int(m.group(1))
            unit_price = _parse_price(m.group(2))
            i += 1
            break
        if m := WEIGHT_PATTERN.match(line):
            weight_kg = float(m.group(1).replace(",", "."))
            grams = weight_kg * 1000
            i += 1
            break
        break

    return quantity, unit_price, grams


def _parse_category(line: str) -> Category:
    name = line.strip()
    try:
        return Category(name)
    except ValueError as e:
        raise ValueError(
            f"Unknown V2 category: {name!r}. "
            f"Add it to the Category enum in superslurp/superslurp_typing.py"
        ) from e


def _parse_price(price_str: str) -> float:
    return float(price_str.replace(",", "."))
