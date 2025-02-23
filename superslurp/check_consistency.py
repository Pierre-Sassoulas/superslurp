from __future__ import annotations

from superslurp.parser import Receipt
from superslurp.superslurp_typing import Category, Item


class ConsistencyError(Exception):
    def __init__(self, msg: str):
        super().__init__(f"Something must be wrong with the parsing because {msg}")


class UndetectedAttributeError(ConsistencyError):
    def __init__(self, item: Item, attribute: str):
        super().__init__(f"{attribute!r} in {item} is not set")


class UnexpectedSumOfParsedItems(ConsistencyError):
    def __init__(
        self, total: str, description: str, expected_value: float, actual_value: float
    ):
        super().__init__(
            f"{description} does not match the {total!r} attribute"
            f" ({expected_value} != {actual_value})."
        )


def check_consistency(receipt: Receipt) -> None:
    (
        recalculated_sub_total,
        recalculated_total,
        recalculated_total_discount,
        recalculated_eligible_tr,
    ) = _calculate_totals_from_items(receipt)
    if recalculated_sub_total != receipt["subtotal"]:
        raise UnexpectedSumOfParsedItems(
            "subtotal",
            "the sum of items prices",
            recalculated_sub_total,
            receipt["subtotal"],
        )
    if recalculated_total != receipt["total"]:
        raise UnexpectedSumOfParsedItems(
            "total",
            "the total",
            recalculated_total,
            receipt["total"],
        )
    if recalculated_total_discount != receipt["total_discount"]:
        raise UnexpectedSumOfParsedItems(
            "total_discount",
            "the sum of discounts",
            recalculated_total_discount,
            receipt["total_discount"],
        )
    if recalculated_eligible_tr != receipt["eligible_tr"]:
        raise UnexpectedSumOfParsedItems(
            "eligible_tr",
            "the sum of prices of items eligible for TR",
            recalculated_eligible_tr,
            receipt["eligible_tr"],
        )
    if recalculated_total != receipt["subtotal"] + receipt["total_discount"]:
        raise UnexpectedSumOfParsedItems(
            "total_discount",
            "the sum of discounts is not equal to subtotal minus total",
            recalculated_total,
            receipt["subtotal"] + receipt["total_discount"],
        )


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
                raise UndetectedAttributeError(item, "price")
            if quantity is None:
                raise UndetectedAttributeError(item, "quantity")
            actual_price = price * quantity
            if item["tr"]:
                recalculated_eligible_tr += actual_price
            if category is Category.DISCOUNT:
                print(f"Checking discount: {category} {actual_price}")
                if actual_price > 0:
                    raise ConsistencyError(
                        f"discounts should be negative, got {actual_price} for {item}"
                    )
                recalculated_total_discount += actual_price
            else:
                recalculated_sub_total += actual_price
            # print(f"Adding {actual_price} to total")
            recalculated_total += actual_price
    return (
        recalculated_sub_total,
        recalculated_total,
        recalculated_total_discount,
        recalculated_eligible_tr,
    )
