from __future__ import annotations

from superslurp.parse.parse_date import parse_date
from superslurp.parse.parse_items import parse_items
from superslurp.parse.parse_store import parse_store_info
from superslurp.parse.parse_totals import get_total_and_number_of_items, parse_totals
from superslurp.superslurp_typing import Receipt


def parse_text(text: str) -> Receipt:
    store_info, remainder = text.split("\nTVA  ")
    receipt_date = parse_date(remainder)
    total, number_of_items = get_total_and_number_of_items(text)
    items_text_with_tail = remainder.split("                ===========")[0]
    items_text = items_text_with_tail.split(">>>>")[1:]
    reconstructed_text = ">>>>" + ">>>>".join(items_text)
    items = parse_items(reconstructed_text, expected_number_of_items=number_of_items)
    sub_total, total_discount, eligible_tr, tr_paid = parse_totals(text)
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
