from __future__ import annotations

import re

from superslurp.parse.common import CompiledSynonyms, resolve_synonyms
from superslurp.parse.safe_search import safe_search
from superslurp.parse.str_to_float import _change_text_to_float
from superslurp.parse.v1.parse_date import parse_date
from superslurp.parse.v1.parse_items import parse_items
from superslurp.superslurp_typing import Card, Receipt

everything_pattern = re.compile(
    r"(?P<store_name>[\S ]*)\n"
    r"(?P<address>([\S ]*\n){2,3})"
    r"Telephone :\s+(?P<telephone>.*)\n"
    r"SIRET (?P<siret>\d+).+NAF (?P<naf>\S+)\n"
    r"(?P<tva>TVA {2}\S+)\s*"
    r"(?P<items_text>Opérateur[\s\S]*)"
    r"TOTAL\s+(?P<number_of_items>\d+) Article\(s\)\s+(?P<total>\d+(,|.)\d+) €[\s\S]*"
    r"VOTRE SOLDE € CARTE U PRECEDENT[ :]+(?P<previous_u>\d+(,|.)\d+) €\n"
    r"(VOS € CARTE U GAGNES[ :]+(?P<u_won>\d+(,|.)\d+) €\n)?"
    r"(VOS € CARTE U UTILISES[ :]+(?P<u_used>\d+(,|.)\d+) €\n)?"
    r"(VOS € CARTE U GAGNES[ :]+(?P<u_won_when_used>\d+(,|.)\d+) €\n)?"
    r"VOTRE NOUVEAU SOLDE € CARTE U[ :]+(?P<new_u>\d+(,|.)\d+) €"
)


def parse_text_v1(
    text: str,
    synonyms: dict[str, str] | None = None,
    compiled_synonyms: CompiledSynonyms | None = None,
) -> Receipt:
    if (matches := everything_pattern.search(text)) is None:
        raise ValueError(
            f"Couldn't match the receipt using the current regex for {text}"
        )
    total_as_float = _change_text_to_float(matches.group("total"))
    assert isinstance(total_as_float, float)  # total must match or we raise ValueError
    number_of_items = int(matches.group("number_of_items"))
    items_text = matches.group("items_text")
    receipt_date = parse_date(items_text)
    items = parse_items(
        items_text,
        expected_number_of_items=number_of_items,
        synonyms=resolve_synonyms(synonyms, compiled_synonyms),
    )
    paid_tr = _change_text_to_float(
        safe_search(r"Payé en TITRES RESTAURANT(.+?)€", text)
    )
    eligible_tr = _change_text_to_float(
        safe_search(r"Dont articles éligibles TR(.+?)€", text)
    )
    total_discount = _change_text_to_float(safe_search(r"REMISE TOTALE(.+?)€", text))
    subtotal = _change_text_to_float(safe_search(r"SOUS TOTAL(.+?)€", text))
    return {
        "store": {
            "store_name": matches.group("store_name"),
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
        "card": _parse_card(matches),
    }


def _parse_card(matches: re.Match[str]) -> Card:
    previous = _change_text_to_float(matches.group("previous_u"))
    new = _change_text_to_float(matches.group("new_u"))
    used = _change_text_to_float(matches.group("u_used"))
    earned = _change_text_to_float(
        matches.group("u_won") or matches.group("u_won_when_used")
    )
    assert previous is not None, "Card balance previous not found"
    assert new is not None, "Card balance new not found"
    return {
        "balance_previous": previous,
        "balance_earned": earned if earned is not None else 0.0,
        "balance_used": used if used is not None else 0.0,
        "balance_new": new,
    }
