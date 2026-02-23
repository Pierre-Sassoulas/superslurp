from __future__ import annotations

import math
import re

from superslurp.parse.safe_search import safe_search
from superslurp.parse.str_to_float import _change_text_to_float
from superslurp.parse.v2.parse_items import parse_items_v2
from superslurp.superslurp_typing import Card, Items, Receipt, Store


def parse_text_v2(text: str, synonyms: dict[str, str] | None = None) -> Receipt:
    store = _parse_store(text)
    date = _parse_date(text)
    items_text = _extract_items_text(text)
    total, number_of_items = _parse_total(text)
    items, total_discount = parse_items_v2(
        items_text, number_of_items, synonyms=synonyms
    )
    card = _parse_card(text)
    subtotal = _parse_subtotal(text)
    eligible_tr = _parse_eligible_tr(text)
    paid_tr = _parse_paid_tr(text)
    eligible_tr = _infer_tr_flags(items, eligible_tr, total)
    return {
        "date": date,
        "store": store,
        "card": card,
        "items": items,
        "subtotal": subtotal,
        "total_discount": total_discount if total_discount != 0.0 else None,
        "total": total,
        "number_of_items": number_of_items,
        "eligible_tr": eligible_tr,
        "paid_tr": paid_tr,
    }


def _infer_tr_flags(
    items: Items, eligible_tr: float | None, total: float
) -> float | None:
    """Infer TR flags when (T) markers are absent from all items.

    Returns the eligible_tr value to use on the receipt (may be set to None
    when per-item TR eligibility cannot be determined).
    """
    any_tr = any(item["tr"] for cat_items in items.values() for item in cat_items)
    if any_tr:
        return eligible_tr

    # No (T) flags found. If eligible_tr equals total, all items are TR-eligible.
    if eligible_tr is not None and math.isclose(eligible_tr, total, abs_tol=0.01):
        for cat_items in items.values():
            for item in cat_items:
                item["tr"] = True
        return eligible_tr

    # Cannot determine per-item TR eligibility without (T) flags.
    return None


def _parse_store(text: str) -> Store:
    phone = safe_search(r"Téléphone\s+(\d+)", text)
    siret = safe_search(r"SIRET\s+(\d+)", text)
    naf = safe_search(r"NAF\s+(\S+)", text)
    # Store name is on the line before SIRET
    store_name = safe_search(r"(\S.*\S)\s*\n\s*SIRET\s+\d+", text, default=None)
    # Address: street line + postal code + city line
    address = _parse_address(text)
    return {
        "store_name": store_name,
        "address": address,
        "phone": phone,
        "siret": siret,
        "naf": naf,
    }


def _parse_address(text: str) -> str | None:
    m = re.search(
        r"(?:Rue|Avenue|Boulevard|Place|Chemin|Allée)\s+(.*?)\n"
        r"\s+(\d{5})\s+(.*?)\n",
        text,
    )
    if m is None:
        return None
    street = m.group(0).split("\n")[0].strip()
    city = m.group(3).strip()
    postal = m.group(2).strip()
    return f"{street}\n{city}\n{postal}\n"


def _parse_date(text: str) -> str | None:
    m = re.search(r"Date\s+Heure.*\n\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})", text)
    if m is None:
        return None
    date_str = m.group(1)
    time_str = m.group(2)
    day, month, year = date_str.split("/")
    return f"20{year}-{month}-{day} {time_str}"


def _extract_items_text(text: str) -> str:
    m = re.search(
        r"\*\*\* VENTE \*\*\*\s*\n(.*?)(?=\nNombre de lignes d'article)",
        text,
        re.DOTALL,
    )
    if m is None:
        raise ValueError("Could not find items section in V2 receipt")
    return m.group(1)


def _parse_total(text: str) -> tuple[float, int]:
    m = re.search(r"TOTAL\s+\[(\d+)\]\s+Articles\s+([\d,]+)\s*€", text)
    if m is None:
        raise ValueError("Could not find TOTAL line in V2 receipt")
    number_of_items = int(m.group(1))
    total = float(m.group(2).replace(",", "."))
    return total, number_of_items


def _parse_card(text: str) -> Card:
    previous_str = safe_search(
        r"VOTRE SOLDE\s+€ CARTE U PRECEDENT\s*:\s*([\d,]+)\s*€", text
    )
    earned_str = safe_search(r"VOS € CARTE U GAGNES\s*:\s*([\d,]+)\s*€", text)
    used_str = safe_search(r"VOS € CARTE U UTILISES\s*:\s*([\d,]+)\s*€", text)
    new_str = safe_search(r"VOTRE NOUVEAU SOLDE € CARTE U\s*:\s*([\d,]+)\s*€", text)
    previous = _change_text_to_float(previous_str)
    earned = _change_text_to_float(earned_str)
    used = _change_text_to_float(used_str)
    new = _change_text_to_float(new_str)
    assert previous is not None, "Card balance previous not found"
    assert new is not None, "Card balance new not found"
    return {
        "balance_previous": previous,
        "balance_earned": earned if earned is not None else 0.0,
        "balance_used": used if used is not None else 0.0,
        "balance_new": new,
    }


def _parse_subtotal(text: str) -> float | None:
    return _change_text_to_float(safe_search(r"SOUS-TOTAL\s+([\d,]+)\s*€", text))


def _parse_eligible_tr(text: str) -> float | None:
    return _change_text_to_float(
        safe_search(r"Dont articles éligibles TR\s+([\d,]+)\s*€", text)
    )


def _parse_paid_tr(text: str) -> float | None:
    return _change_text_to_float(
        safe_search(r"Payé en TITRES RESTAURANT\s+([\d,]+)\s*€", text)
    )
