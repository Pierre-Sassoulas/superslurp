from __future__ import annotations

import re
from collections import defaultdict

from superslurp.str_to_float import _change_text_to_float
from superslurp.superslurp_typing import Category, Item


def parse_items(text: str) -> dict[Category, list[Item]]:
    current_category: Category = Category.UNDEFINED
    items: dict[Category, list[Item]] = defaultdict(list)
    previous_line = None
    for line in text.split("\n"):
        if not line.strip():
            continue
        if ">>>>" in line:
            current_category = get_new_category(line)
            previous_line = None
            continue
        if "COUPON N°" in line:
            # This is a reduction we don't care about
            continue
        # pylint: disable-next=unsupported-membership-test
        if "Pourcentage: 30" in line:
            # This is a discount on the previous item
            previous_item = items[current_category][-1]
            discount = line.split("Pourcentage: 30")[1].split("€")[0].strip()
            item: Item = {
                "name": previous_item["name"],
                "price": _change_text_to_float(discount),
                "quantity": previous_item["quantity"],
                "grams": previous_item["grams"],
                "tr": previous_item["tr"],
            }
            print(f"Discount on {previous_item['name']} : {item}")
            items[Category.DISCOUNT].append(item)
            previous_line = None
        if previous_line is not None:
            new_line = f"{previous_line}{line}"
            # print(f"Couldn't handle {previous_line!r}, trying with:\n{new_line}")
            items_info = get_items_infos_from_line(new_line)
            # print("Items info:", items_info)
            if (possible_item := get_item_from_item_infos_multiple(items_info)) is None:
                print(f"Couldn't handle {new_line}, skipping.")
                continue
            assert possible_item is not None  # mypy
            item = possible_item
            previous_line = None
        else:
            items_info = get_items_infos_from_line(line)
            if len(items_info) < 3:
                print(f"Can't handle {items_info} alone, merging with next line.")
                previous_line = line
                continue
            item = get_item_from_item_infos(items_info)
        # print(f"New item : {item}")
        items[current_category].append(item)
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


def get_item_from_item_infos(items_info: list[str]) -> Item:
    name, price, tr, quantity = "", "0,00 €", "", 1
    if len(items_info) > 4:
        # Sometimes there's two spaces by mistake in a name
        # But this could be something else, it's suspicious
        print(f"Too many elements in {items_info}")
        *temp_name, tr, price, _ = items_info
        name = " ".join(temp_name)
    elif len(items_info) == 4:
        # Item that can be paid with TR
        name, tr, price, _ = items_info
    elif len(items_info) == 3:
        # An item that can't be paid with TR
        name, price, _ = items_info
    final_name, grams = _get_gram(name)
    item: Item = {
        "name": final_name,
        "price": _get_price(price),
        "quantity": quantity,
        "grams": grams,
        "tr": _get_tr(tr),
    }
    return item


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
