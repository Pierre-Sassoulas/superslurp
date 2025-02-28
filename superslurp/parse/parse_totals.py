from __future__ import annotations


def _match_tr_paid(after_total: str) -> str | None:
    try:
        return after_total.split("Payé en TITRES RESTAURANT")[1].split("€")[0].strip()
    except IndexError:
        return None


def _match_eligible_tr(after_total: str) -> str | None:
    try:
        return after_total.split("Dont articles éligibles TR")[1].split("€")[0].strip()
    except IndexError:
        return None


def _match_total_discount(cleanup: str) -> str | None:
    try:
        return cleanup.split("REMISE TOTALE")[1].split("€")[0].strip()
    except IndexError:
        return None


def _match_sub_total(cleanup: str) -> str | None:
    try:
        return cleanup.split("SOUS TOTAL")[1].split("€")[0].strip()
    except IndexError:
        return None
