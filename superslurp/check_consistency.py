from __future__ import annotations

from superslurp.parser import Receipt


def check_consistency(receipt: Receipt) -> None:
    err_msg = "Something must be wrong with the parsing because"
    recalculated_sum = 0.0
    for item in receipt["items"]:
        price = item["price"]
        quantity_ = item["quantity"]
        assert price is not None, f"{err_msg} price is None in item: {item}"
        assert quantity_ is not None, f"{err_msg} quantity is None in item: {item}"
        recalculated_sum += price * quantity_
    bad_sum_msg = (
        f"{err_msg} the sum of items prices:"
        f" {recalculated_sum} != total: {receipt['total']}"
    )
    assert recalculated_sum == receipt["total"], bad_sum_msg
    bad_subtotal_discount = (
        f"{err_msg} the sum of items prices:"
        f" {recalculated_sum} != subtotal + total_discount: {receipt['subtotal']} + {receipt['total_discount']}"
    )
    assert recalculated_sum == receipt["subtotal"] + receipt["total_discount"], (
        bad_subtotal_discount
    )
