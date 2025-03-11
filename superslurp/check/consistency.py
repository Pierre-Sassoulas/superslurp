from __future__ import annotations

import math

from superslurp.check.calculate_total_from_items import _calculate_totals_from_items
from superslurp.exception import UnexpectedSumOfParsedItems
from superslurp.superslurp_typing import Receipt


def check_consistency(receipt: Receipt) -> None:
    (  # pylint: disable=unused-variable
        recalculated_sub_total,
        recalculated_total,
        recalculated_total_discount,
        recalculated_eligible_tr,
    ) = _calculate_totals_from_items(receipt)
    if not math.isclose(recalculated_total, receipt["total"], abs_tol=0.01):
        raise UnexpectedSumOfParsedItems(
            receipt=receipt,
            total="total",
            description="the total",
            actual_value=recalculated_total,
            expected_value=receipt["total"],
        )

    # total_discount = receipt["total_discount"]
    # subtotal = receipt["subtotal"]
    # if subtotal is not None and not math.isclose(subtotal, 0.0):
    #     if total_discount is not None and not math.isclose(total_discount, 0.0):
    #         if not math.isclose(recalculated_total, subtotal + total_discount):
    #             raise UnexpectedSumOfParsedItems(
    #                 receipt=receipt,
    #                 total="total_discount",
    #                 description="the sum of discounts is not equal to subtotal minus total",
    #                 actual_value=recalculated_total,
    #                 expected_value=subtotal + total_discount,
    #             )
    #     if not math.isclose(recalculated_sub_total, subtotal):
    #         raise UnexpectedSumOfParsedItems(
    #             receipt=receipt,
    #             total="subtotal",
    #             description="the sum of items prices",
    #             actual_value=recalculated_sub_total,
    #             expected_value=subtotal,
    #         )
    # if (
    #     total_discount is not None
    #     and not math.isclose(total_discount, 0.0)
    #     and not math.isclose(
    #         recalculated_total_discount,
    #         total_discount,
    #     )
    # ):
    #     raise UnexpectedSumOfParsedItems(
    #         receipt=receipt,
    #         total="total_discount",
    #         description="the sum of discounts",
    #         actual_value=recalculated_total_discount,
    #         expected_value=total_discount,
    #     )
    eligible_tr = receipt["eligible_tr"]
    if (
        eligible_tr is not None
        and not math.isclose(eligible_tr, 0.0)
        and not math.isclose(recalculated_eligible_tr, eligible_tr)
    ):
        raise UnexpectedSumOfParsedItems(
            receipt=receipt,
            total="eligible_tr",
            description="the sum of prices of items eligible for TR",
            actual_value=recalculated_eligible_tr,
            expected_value=eligible_tr,
        )
