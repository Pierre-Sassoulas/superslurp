from __future__ import annotations

import logging
import re
from collections import defaultdict
from collections.abc import Generator

from superslurp.repr.items import repr_items
from superslurp.superslurp_typing import Category, Item, Items


class WrongNumberOfItemException(Exception): ...


category_pattern = re.compile(r">>>>(?P<category>.*)\n(?P<items>(?:(?!>>>>)[\S\s])*)")
single_undefined_category_pattern = re.compile(
    r"Ticket  \n[\w \/:]+[\n ]+(?P<items>(?:(?!==)[\S\s])*\n)[\n =]+"
)
# way_of_paying_pattern = re.compile(r"(?P<way_of_paying>\d{2} \n)+")
items_pattern = re.compile(
    r"(?P<name>[\w .\/%,=€°+Éé\*]*)(?P<tr>\(T\))?(\d\d)?[ \n]*"
    r"(?P<quantity>[\d x,]+ €)?[ ]+(?P<price>[\d]+[,|\.][ \d€]+)[ ]?(?P<way_of_paying>\d{2})+ \n"
    r"|\s*Pourcentage:\s*(?P<pourcentage>\d+)\s*-(?P<discount>[\d]+[,|\.][ \d€]+)\n"
)


def iter_categories_and_items(text: str) -> Generator[tuple[Category, str]]:
    logging.debug(f"Parsing with {category_pattern}:\n<\n{text}\n>")
    if not (category_matches := list(category_pattern.finditer(text))):
        if (
            items_without_category := single_undefined_category_pattern.search(text)
        ) is not None:
            logging.debug(
                f"Category could not be found, will continue parsing using {Category.UNDEFINED}."
            )
            yield Category.UNDEFINED, items_without_category.group("items")
            return
        err_msg = f"Using {single_undefined_category_pattern}, couldn't find any category in:\n<\n{text}\n>\n"
        print(err_msg)
        raise AssertionError(err_msg)
    for match in category_matches:
        category = Category(match.group("category").strip())
        items_info = match.group("items")
        yield category, items_info


def parse_items(text: str, expected_number_of_items: int) -> dict[Category, list[Item]]:
    items_parsed = 0
    items: dict[Category, list[Item]] = defaultdict(list)
    category = Category.UNDEFINED
    for category, items_info in iter_categories_and_items(text):
        items_parsed += _handle_items_in_category(items, category, items_info)
    if items_parsed != expected_number_of_items:
        raise WrongNumberOfItemException(
            f"Expected {expected_number_of_items} items in\n{text}\n"
            f"But parsing extracted {items_parsed}:\n{repr_items(items)}\n"
            f"Preparsing of categories was:\n{category}"
        )
    return items


def _handle_items_in_category(items: Items, category: Category, items_info: str) -> int:
    items_parsed = 0
    logging.debug(f"Parsing {category=} with {items_pattern}:\n<\n{items_info}\n>")
    for item_info in items_pattern.finditer(items_info):
        logging.debug(f"Item found in {category}: {item_info}")
        if "Pourcentage" in item_info.group(0):
            items[category].append(
                {
                    "name": items[category][-1]["name"],
                    "price": -_get_price(item_info.group("discount")),
                    "quantity": items[category][-1]["quantity"],
                    "grams": items[category][-1]["grams"],
                    "tr": items[category][-1]["tr"],
                    "way_of_paying": items[category][-1]["way_of_paying"],
                }
            )
            continue
        item = get_item_from_item_infos(item_info)
        items_parsed += item["quantity"]
        items[category].append(item)
    if items_parsed == 0:
        raise WrongNumberOfItemException(
            f"No item found in {category}, that's impossible:"
            f"In\n\n{items_info}\n\nnothing matched by {items_pattern!r}"
        )
    return items_parsed


def get_new_category(line: str) -> Category:
    try:
        return Category(line.replace(">>>>", "").strip())
    except ValueError as e:
        raise ValueError(f"Missing value in enum '{Category!r}': {e}") from e


def get_item_from_item_infos(item_info: re.Match[str]) -> Item:
    if (matched_name := item_info.group("name")) is None:
        raise ValueError(f"Nothing matched the name in {item_info}")
    name = matched_name.strip()
    if (quantity := _parse_quantity(item_info.group("quantity"))) == 1:
        price = item_info.group("price")
    else:
        price = item_info.group("quantity").split("x")[1]
    tr = item_info.group("tr")
    way_of_paying = item_info.group("way_of_paying")
    item: Item = {
        "name": name,
        "price": _get_price(price),
        "quantity": quantity,
        "grams": _get_gram(name)[1],
        "tr": _get_tr(tr),
        "way_of_paying": way_of_paying,
    }
    return item


def _parse_quantity(quantity: str | None) -> int:
    if quantity is None:
        return 1
    quantity = quantity.strip()
    if " x" in quantity:
        return int(quantity.split(" x")[0])
    return int(quantity)


def _get_gram(name: str) -> tuple[str, float | None]:
    grams = None
    search = re.search(
        r"(?P<multiplier>\d+X)?(?P<grams>\d?[\d+,]?\d+K?G(?: ENVIRON)?)", name
    )
    if search is None:
        return name, None
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
            grams *= int(multiplier[:-1])
    name = name.replace(search.group(0), "")
    return name.strip(), grams


def _get_price(price: str) -> float:
    price = price.split(" €")[0].replace(",", ".")
    return float(price)


def _get_tr(tr: str) -> bool:
    return tr == "(T)"


def get_items_infos_from_line(line: str) -> list[str]:
    items_info = [word.strip() for word in line.split("  ")]
    items_info = [word for word in items_info if word]
    return items_info
