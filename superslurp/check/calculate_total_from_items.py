from __future__ import annotations

from superslurp.exception import ConsistencyError, UndetectedAttributeError
from superslurp.superslurp_typing import Category, Receipt


def _calculate_totals_from_items(receipt: Receipt) -> tuple[float, float, float, float]:
    recalculated_sub_total = 0.0
    recalculated_total = 0.0
    recalculated_total_discount = 0.0
    recalculated_eligible_tr = 0.0
    for category, items in receipt["items"].items():
        for item in items:
            price = item["price"]
            quantity = item["quantity"]
            if price is None:
                raise UndetectedAttributeError(
                    receipt=receipt, item=item, attribute="price"
                )
            if quantity is None:
                raise UndetectedAttributeError(
                    receipt=receipt, item=item, attribute="quantity"
                )
            actual_price = price * quantity
            if item["tr"]:
                recalculated_eligible_tr += actual_price
            if category is Category.DISCOUNT:
                print(f"Checking discount: {category} {actual_price}")
                if actual_price > 0:
                    raise ConsistencyError(
                        receipt=receipt,
                        msg=f"discounts should be negative, got {actual_price} for {item}",
                    )
                recalculated_total_discount += actual_price
            else:
                recalculated_sub_total += actual_price
            recalculated_total += actual_price
            print(f"Added {actual_price} to total {recalculated_total}")
    return (
        recalculated_sub_total,
        recalculated_total,
        recalculated_total_discount,
        recalculated_eligible_tr,
    )
