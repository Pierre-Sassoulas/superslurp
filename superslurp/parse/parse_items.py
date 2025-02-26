from __future__ import annotations

import re
from collections import defaultdict

from superslurp.repr.items import repr_items
from superslurp.superslurp_typing import Category, Item


class WrongNumberOfItemException(Exception): ...


category_pattern = re.compile(r">>>>(?P<category>.*)\n(?P<items>(?:(?!>>>>)[\S\s])*)")
# way_of_paying_pattern = re.compile(r"(?P<way_of_paying>\d{2} \n)+")
items_pattern = re.compile(
    r"(?P<name>[\w .\/%,=€°+É]*)(?P<tr>\(T\))?(\d\d)?[ \n]*"
    r"(?P<quantity>[\d x,]+ €)?[ ]+(?P<price>[\d]+,[ \d€]+)[ ]?(?P<way_of_paying>\d{2})+ \n"
)


def parse_items(text: str, expected_number_of_items: int) -> dict[Category, list[Item]]:
    i = 0
    items: dict[Category, list[Item]] = defaultdict(list)
    category_matches: str = []
    for match in category_pattern.finditer(text):
        category_matches.append(match)
        i_cat = i
        category = Category(match.group("category").strip())
        items_info = match.group("items")
        for item_info in items_pattern.finditer(items_info):
            print(f"Item found in {category}: {item_info}")
            item = get_item_from_item_infos(item_info)
            i += item["quantity"]
            items[category].append(item)
        # if i == i_cat:
        #     raise WrongNumberOfItemException(
        #         f"No item found in {category}, that's impossible:"
        #         f"In\n{text}\n\n, more precisely in\n{items_info}\n"
        #         f"nothing matched by {items_pattern}"
        #     )
    if i != expected_number_of_items:
        raise WrongNumberOfItemException(
            f"Expected {expected_number_of_items} items in\n{text}\n"
            f"But parsing extracted {i}:\n{repr_items(items)}\n"
            f"Preparsing of categories was:\n{category_matches}"
        )
    return items


def get_new_category(line: str) -> Category:
    try:
        return Category(line.replace(">>>>", "").strip())
    except ValueError as e:
        raise ValueError(f"Missing value in enum '{Category!r}': {e}") from e


def get_item_from_item_infos_multiple(items_info: list[str]) -> Item | None:
    if len(items_info) != 6:
        # Can't deal with this line
        return None
    name, tr, quantity, unit_price, *_ = items_info
    quantity = quantity.split(" x")[0]
    return {
        "name": name,
        "price": _get_price(unit_price),
        "quantity": int(quantity),
        "grams": _get_gram(name)[1],
        "tr": _get_tr(tr),
    }


def get_item_from_item_infos(item_info: re.Match[str]) -> Item:
    name = item_info.group("name").strip()
    quantity = _parse_quantity(item_info.group("quantity"))
    if quantity == 1:
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
    }
    return item


def _parse_quantity(quantity: str) -> int:
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
