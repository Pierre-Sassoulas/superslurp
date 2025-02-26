from __future__ import annotations

from superslurp.check.calculate_total_from_items import _calculate_totals_from_items
from superslurp.exception import UnexpectedSumOfParsedItems
from superslurp.superslurp_typing import Receipt


def check_consistency(receipt: Receipt) -> None:
    (
        recalculated_sub_total,
        recalculated_total,
        recalculated_total_discount,
        recalculated_eligible_tr,
    ) = _calculate_totals_from_items(receipt)
    if recalculated_total != receipt["total"]:
        raise UnexpectedSumOfParsedItems(
            receipt,
            "total",
            "the total",
            recalculated_total,
            receipt["total"],
        )
    if receipt["subtotal"] != 0.0:
        if receipt["total_discount"] != 0.0:
            if recalculated_total != receipt["subtotal"] + receipt["total_discount"]:
                raise UnexpectedSumOfParsedItems(
                    receipt,
                    "total_discount",
                    "the sum of discounts is not equal to subtotal minus total",
                    recalculated_total,
                    receipt["subtotal"] + receipt["total_discount"],
                )
        if recalculated_sub_total != receipt["subtotal"]:
            raise UnexpectedSumOfParsedItems(
                receipt,
                "subtotal",
                "the sum of items prices",
                recalculated_sub_total,
                receipt["subtotal"],
            )

    if (
        receipt["total_discount"] != 0.0
        and recalculated_total_discount != receipt["total_discount"]
    ):
        raise UnexpectedSumOfParsedItems(
            receipt,
            "total_discount",
            "the sum of discounts",
            recalculated_total_discount,
            receipt["total_discount"],
        )
    if (
        receipt["eligible_tr"] != 0.0
        and recalculated_eligible_tr != receipt["eligible_tr"]
    ):
        raise UnexpectedSumOfParsedItems(
            "eligible_tr",
            "the sum of prices of items eligible for TR",
            recalculated_eligible_tr,
            receipt["eligible_tr"],
        )
