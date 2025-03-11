from __future__ import annotations

from superslurp.check.calculate_total_from_items import _calculate_totals_from_items
from superslurp.superslurp_typing import Receipt


def check_consistency(receipt: Receipt) -> None:
    (  # pylint: disable=unused-variable
        recalculated_sub_total,
        recalculated_total,
        recalculated_total_discount,
        recalculated_eligible_tr,
    ) = _calculate_totals_from_items(receipt)
    # if not math.isclose(recalculated_total, receipt["total"], abs_tol=0.01):
    #     print(f"recalculated_total: {recalculated_total} {receipt['total']}")
    #     raise UnexpectedSumOfParsedItems(
    #         receipt=receipt,
    #         total="total",
    #         description="the total",
    #         actual_value=recalculated_total,
    #         expected_value=receipt["total"],
    #     )

    # if not math.isclose(receipt["subtotal"], 0.0):
    #     if not math.isclose(receipt["total_discount"], 0.0):
    #         if not math.isclose(
    #             recalculated_total, receipt["subtotal"] + receipt["total_discount"]
    #         ):
    #             raise UnexpectedSumOfParsedItems(
    #                 receipt,
    #                 "total_discount",
    #                 "the sum of discounts is not equal to subtotal minus total",
    #                 recalculated_total,
    #                 receipt["subtotal"] + receipt["total_discount"],
    #             )
    #     if not math.isclose(recalculated_sub_total, receipt["subtotal"]):
    #         raise UnexpectedSumOfParsedItems(
    #             receipt,
    #             "subtotal",
    #             "the sum of items prices",
    #             recalculated_sub_total,
    #             receipt["subtotal"],
    #         )
    # if not math.isclose(receipt["total_discount"], 0.0) and not math.isclose(
    #     recalculated_total_discount,
    #     receipt["total_discount"],
    # ):
    #     raise UnexpectedSumOfParsedItems(
    #         receipt,
    #         "total_discount",
    #         "the sum of discounts",
    #         recalculated_total_discount,
    #         receipt["total_discount"],
    #     )
    # if not math.isclose(receipt["eligible_tr"], 0.0) and not math.isclose(
    #     recalculated_eligible_tr, receipt["eligible_tr"]
    # ):
    #     raise UnexpectedSumOfParsedItems(
    #         "eligible_tr",
    #         "the sum of prices of items eligible for TR",
    #         recalculated_eligible_tr,
    #         receipt["eligible_tr"],
    #     )
