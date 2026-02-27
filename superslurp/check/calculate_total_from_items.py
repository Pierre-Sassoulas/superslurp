from __future__ import annotations

from typing import NamedTuple

from superslurp.exception import ConsistencyError, UndetectedAttributeError
from superslurp.superslurp_typing import Category, Receipt


class RecalculatedTotals(NamedTuple):
    sub_total: float
    total: float
    total_discount: float
    eligible_tr: float


def _calculate_totals_from_items(receipt: Receipt) -> RecalculatedTotals:
    recalculated_sub_total = 0.0
    recalculated_total = 0.0
    recalculated_total_discount = 0.0
    recalculated_eligible_tr = 0.0
    for category, items in receipt["items"].items():
        for item in items:
            price = item["price"]
            quantity = item["bought"]
            if price is None:
                raise UndetectedAttributeError(
                    receipt=receipt, item=item, attribute="price"
                )
            if quantity is None:
                raise UndetectedAttributeError(
                    receipt=receipt, item=item, attribute="bought"
                )
            actual_price = price * quantity
            discount = item.get("discount") or 0.0
            actual_price -= discount
            recalculated_total_discount -= discount
            if item["tr"]:
                recalculated_eligible_tr += actual_price
            if category is Category.DISCOUNT:
                print(f"Checking discount: {category} {actual_price}")
                if actual_price > 0:
                    raise ConsistencyError(
                        receipt=receipt,
                        msg=f"discounts should be negative, got {actual_price} for {item}",
                    )
            recalculated_sub_total += actual_price
            recalculated_total += actual_price
            print(f"Added {actual_price} to total {recalculated_total}")
    return RecalculatedTotals(
        sub_total=recalculated_sub_total,
        total=recalculated_total,
        total_discount=recalculated_total_discount,
        eligible_tr=recalculated_eligible_tr,
    )
