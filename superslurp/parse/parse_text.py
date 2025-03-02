from __future__ import annotations

import re

from superslurp.parse.parse_date import parse_date
from superslurp.parse.parse_items import parse_items
from superslurp.parse.parse_totals import (
    _match_eligible_tr,
    _match_sub_total,
    _match_total_discount,
    _match_tr_paid,
)
from superslurp.parse.str_to_float import _change_text_to_float
from superslurp.superslurp_typing import Receipt

everything_pattern = re.compile(
    r"(?P<address>([\S ]*\n){3,4})"
    r"Telephone :\s+(?P<telephone>.*)\n"
    r"SIRET (?P<siret>\d+).+NAF (?P<naf>\S+)\n"
    r"(?P<tva>TVA  \S+)\s*"
    r"(?P<items_text>Opérateur[\s\S]*)"
    r"TOTAL\s+(?P<number_of_items>\d+) Article\(s\)\s+(?P<total>\d+(,|.)\d+) €[\s\S]*"
    r"VOTRE SOLDE € CARTE U PRECEDENT[ :]+(?P<previous_u>\d+(,|.)\d+) €\n"
    r"(VOS € CARTE U GAGNES[ :]+(?P<u_won>\d+(,|.)\d+) €\n){0,1}"
    r"(VOS € CARTE U UTILISES[ :]+(?P<u_used>\d+(,|.)\d+) €\n){0,1}"
    r"VOTRE NOUVEAU SOLDE € CARTE U[ :]+(?P<new_u>\d+(,|.)\d+) €"
)


def parse_text(text: str) -> Receipt:
    if (matches := everything_pattern.search(text)) is None:
        raise ValueError(
            f"Couldn't match the receipt using the current regex for {text}"
        )
    total_as_float = _change_text_to_float(matches.group("total"))
    assert isinstance(total_as_float, float)  # total must match or we raise ValueError
    number_of_items = int(matches.group("number_of_items"))
    items_text = matches.group("items_text")
    receipt_date = parse_date(items_text)
    items = parse_items(items_text, expected_number_of_items=number_of_items)
    paid_tr = _change_text_to_float(_match_tr_paid(text))
    eligible_tr = _change_text_to_float(_match_eligible_tr(text))
    total_discount = _change_text_to_float(_match_total_discount(text))
    subtotal = _change_text_to_float(_match_sub_total(text))
    card_balance_previous = _change_text_to_float(matches.group("previous_u"))
    card_balance_earned = (
        _change_text_to_float(matches.group("u_won")) if matches.group("u_won") else 0.0
    )
    card_balance_used = (
        _change_text_to_float(matches.group("u_used"))
        if matches.group("u_used")
        else 0.0
    )
    card_balance_new = _change_text_to_float(matches.group("new_u"))
    assert card_balance_previous is not None
    assert card_balance_earned is not None
    assert card_balance_used is not None
    assert card_balance_new is not None
    return {
        "store": {
            "address": matches.group("address"),
            "phone": matches.group("telephone"),
            "siret": matches.group("siret"),
            "naf": matches.group("naf"),
        },
        "items": items,
        "date": str(receipt_date) if receipt_date else None,
        "subtotal": subtotal,
        "total_discount": total_discount,
        "number_of_items": number_of_items,
        "total": total_as_float,
        "eligible_tr": eligible_tr,
        "paid_tr": paid_tr,
        "card": {
            "balance_previous": card_balance_previous,
            "balance_earned": card_balance_earned,
            "balance_used": card_balance_used,
            "balance_new": card_balance_new,
        },
    }
