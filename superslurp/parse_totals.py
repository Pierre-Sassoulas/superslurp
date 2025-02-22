from __future__ import annotations

from superslurp.str_to_float import _change_text_to_float


def parse_totals(text: str) -> tuple[float, float, int, float, float, float]:
    cleanup = text.split("===========")[1].split("*" * 54)[0].strip()
    sub_total = cleanup.split("SOUS TOTAL")[1].split("€")[0].strip()
    total_discount = cleanup.split("REMISE TOTALE")[1].split("€")[0].strip()
    after_total = cleanup.split("TOTAL")[3]
    split_with_articles = after_total.split("Article(s)")
    number_of_items = split_with_articles[0].strip()
    total = split_with_articles[1].split("€")[0].strip()
    eligible_tr = (
        after_total.split("Dont articles éligibles TR")[1].split("€")[0].strip()
    )
    tr_paid = after_total.split("Payé en TITRES RESTAURANT")[1].split("€")[0].strip()
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
