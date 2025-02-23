from __future__ import annotations

import re

from superslurp.str_to_float import _change_text_to_float


def parse_totals(text: str) -> tuple[float, float, int, float, float, float]:
    # Parse the total and number of items using a regex for " TOTAL   17 Article(s)         72,87 € "
    total_and_number_of_items = re.search(
        r"TOTAL\s+(?P<number_of_items>\d+) Article\(s\)\s+(?P<total>\d+,\d+)", text
    )
    if total_and_number_of_items is None:
        raise ValueError("Couldn't find the total and number of items")
    total = total_and_number_of_items.group("total")
    number_of_items = total_and_number_of_items.group("number_of_items")
    sub_total = "0,00"
    eligible_tr = "0,00"
    tr_paid = "0,00"
    total_discount = "0,00"
    cleanup = text.split("===========")[1].split("*" * 54)[0].strip()
    try:
        sub_total = _match_sub_total(cleanup)
    except IndexError:
        print(f"Failed to find sub_total in {cleanup}")
    try:
        total_discount = _match_total_discount(cleanup)
    except IndexError:
        print(f"Failed to find total_discount in {cleanup}")

    try:  # pylint: disable=too-many-try-statements
        after_total = cleanup.split("TOTAL")[3]
        eligible_tr = _match_eligible_tr(after_total)
        tr_paid = _match_tr_paid(after_total)
    except IndexError:
        print(
            f"Failed to split after_total in {cleanup} and failed to find eligible_tr and tr_paid"
        )
    print(
        f"sub_total: {sub_total}, total_discount: {total_discount}, "
        f"number_of_items: {number_of_items}, total: {total}, "
        f"eligible_tr: {eligible_tr}, tr_paid: {tr_paid}"
    )
    return (
        _change_text_to_float(sub_total),
        _change_text_to_float(total_discount),
        int(number_of_items),
        _change_text_to_float(total),
        _change_text_to_float(eligible_tr),
        _change_text_to_float(tr_paid),
    )


def _match_tr_paid(after_total: str) -> str:
    return after_total.split("Payé en TITRES RESTAURANT")[1].split("€")[0].strip()


def _match_eligible_tr(after_total: str) -> str:
    return after_total.split("Dont articles éligibles TR")[1].split("€")[0].strip()


def _match_total_discount(cleanup: str) -> str:
    return cleanup.split("REMISE TOTALE")[1].split("€")[0].strip()


def _match_sub_total(cleanup: str) -> str:
    return cleanup.split("SOUS TOTAL")[1].split("€")[0].strip()
