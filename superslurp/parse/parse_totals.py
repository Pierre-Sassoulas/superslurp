from __future__ import annotations

import re

from superslurp.parse.str_to_float import _change_text_to_float

total_and_number_of_items_pattern = re.compile(
    r"TOTAL\s+(?P<number_of_items>\d+) Article\(s\)\s+(?P<total>\d+(,|.)\d+)"
)


def parse_totals(text: str) -> tuple[float, float, float, float]:
    # Parse the total and number of items using a regex for " TOTAL   17 Article(s)         72,87 € "
    sub_total = "0,00"
    eligible_tr = "0,00"
    tr_paid = "0,00"
    total_discount = "0,00"
    return (
        _change_text_to_float(sub_total),
        _change_text_to_float(total_discount),
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


def get_total_and_number_of_items(text: str) -> tuple[float, int]:
    if (re_match := total_and_number_of_items_pattern.search(text)) is None:
        raise ValueError(f"Couldn't find the total and number of items in {text}")
    total_str = re_match.group("total")
    total_as_float = _change_text_to_float(total_str)
    return total_as_float, int(re_match.group("number_of_items"))
