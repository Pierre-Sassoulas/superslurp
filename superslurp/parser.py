from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from superslurp.parse_store import Store, parse_store_info


class Item(TypedDict):
    category: str
    name: str
    price: float
    quantity: int


def parse_items(text: str) -> list[Item]:
    items: list[Item] = []
    return items


class Receipt(TypedDict):
    date: str
    store: Store
    items: list[Item]


def parse_date(text: str) -> datetime:
    return datetime.now()


def parse_text(text: str) -> Receipt:
    store_info, remainder = text.split("\nTVA  ")
    return {
        "store": parse_store_info(store_info),
        "items": parse_items(remainder),
        "date": str(parse_date(remainder)),
    }
