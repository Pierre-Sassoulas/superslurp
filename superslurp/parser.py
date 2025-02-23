from __future__ import annotations

from typing import TypedDict

from superslurp.parse_date import parse_date
from superslurp.parse_items import parse_items
from superslurp.parse_store import Store, parse_store_info
from superslurp.parse_totals import parse_totals
from superslurp.superslurp_typing import Category, Item


class Receipt(TypedDict):
    date: str | None
    store: Store
    items: dict[Category, list[Item]]
    subtotal: float
    total_discount: float
    total: float
    number_of_items: int
    eligible_tr: float
    paid_tr: float
    # card_balance_previous: float
    # card_balance_earned: float
    # card_balance_new: float


def parse_text(text: str) -> Receipt:
    store_info, remainder = text.split("\nTVA  ")
    receipt_date = parse_date(remainder)
    items_text_with_tail = remainder.split("                ===========")[0]
    items_text = items_text_with_tail.split(">>>>")[1:]
    reconstructed_text = ">>>>" + ">>>>".join(items_text)
    items = parse_items(reconstructed_text)
    sub_total, total_discount, number_of_items, total, eligible_tr, tr_paid = (
        parse_totals(text)
    )
    return {
        "store": parse_store_info(store_info),
        "items": items,
        "date": str(receipt_date) if receipt_date else None,
        "subtotal": sub_total,
        "total_discount": total_discount,
        "number_of_items": number_of_items,
        "total": total,
        "eligible_tr": eligible_tr,
        "paid_tr": tr_paid,
    }
