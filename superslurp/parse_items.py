from __future__ import annotations

import enum
import re
from typing import TypedDict


class Category(enum.Enum):
    FRUITS_ET_LEGUMES = "FRUITS ET LEGUMES"
    PAT_INDUSTRIELLE = "PAT INDUSTRIELLE"
    EPICERIE = "EPICERIE"
    BRICOLAGE_JARDINAGE_AUT = "BRICOLAGE JARDINAGE AUT"
    FROMAGE_A_LA_COUPE = "FROMAGE A LA COUPE"
    BEAUTE_SANTE = "BEAUTE SANTE"
    CREMERIE_LS = "CREMERIE L.S."
    VOL_LS_INDUST = "VOL.LS INDUST."
    ENTRETIEN = "ENTRETIEN"
    LIQUIDES = "LIQUIDES"

    UNDEFINED = "AUTRE"


class Item(TypedDict):
    category: str
    name: str
    price: float
    quantity: int | None
    grams: float | None
    tr: bool


def parse_items(text: str) -> list[Item]:
    current_category: Category = Category.UNDEFINED
    items: list[Item] = []
    previous_line = None
    for line in text.split("\n"):
        if not line.strip():
            continue
        if ">>>>" in line:
            new_category = Category(line.replace(">>>>", "").strip())
            # print(f"Changed category from {current_category} to {new_category.value}")
            current_category = new_category
            continue
        if "COUPON N°" in line:
            # This is a reduction we don't care about
            break
        if previous_line is not None:
            if "Pourcentage: 30" in previous_line:
                # This is a reduction on the previous item
                items[-1]["price"] = items[-1]["price"] * 0.7
                print(
                    f"Reducing the price of {items[-1]['name']} by 30%, new item: {items[-1]}"
                )
                previous_line = None
                continue
            new_line = f"{previous_line}{line}"
            print(f"Couldn't handle {previous_line!r}, trying with:\n{new_line}")
            items_info = get_items_infos_from_line(new_line)
            # print("Items info:", items_info)
            if (
                item := get_item_from_item_infos_multiple(current_category, items_info)
            ) is None:
                print(f"Couldn't handle {new_line}, skipping.")
                continue
            previous_line = None
        else:
            items_info = get_items_infos_from_line(line)
            if len(items_info) < 3:
                print(f"Can't handle {items_info} alone, merging with next line.")
                previous_line = line
                continue
            item = get_item_from_item_infos(current_category, items_info)
        print(f"New item : {item}")
        items.append(item)
    return items


def get_item_from_item_infos_multiple(
    current_category: Category, items_info: list[str]
) -> Item | None:
    if len(items_info) != 6:
        # Can't deal with this line
        return None
    name, tr, quantity, unit_price, *_ = items_info
    quantity = quantity.split(" x")[0]
    return {
        "category": current_category.value,
        "name": name,
        "price": _get_price(unit_price),
        "quantity": int(quantity),
        "grams": _get_gram(name)[1],
        "tr": _get_tr(tr),
    }


def get_item_from_item_infos(current_category: Category, items_info: list[str]) -> Item:
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
        "category": current_category.value,
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
