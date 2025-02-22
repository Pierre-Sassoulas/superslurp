from __future__ import annotations

from typing import TypedDict

from superslurp.parse_date import parse_date
from superslurp.parse_items import Item, parse_items
from superslurp.parse_store import Store, parse_store_info


class Receipt(TypedDict):
    date: str | None
    store: Store
    items: list[Item]


def parse_text(text: str) -> Receipt:
    store_info, remainder = text.split("\nTVA  ")
    receipt_date = parse_date(remainder)
    items_text_with_tail = remainder.split("                ===========")[0]
    items_text = items_text_with_tail.split(">>>>")[1:]
    reconstructed_text = ">>>>" + ">>>>".join(items_text)
    items = parse_items(reconstructed_text)
    return {
        "store": parse_store_info(store_info),
        "items": items,
        "date": str(receipt_date) if receipt_date else None,
    }
