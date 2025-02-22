from __future__ import annotations

from typing import TypedDict

from superslurp.safe_search import safe_search


class Store(TypedDict):
    store_name: str | None
    address: str | None
    phone: str | None
    siret: str | None
    naf: str | None


def parse_store_info(store_info: str) -> Store:
    address = safe_search(r"\n(.+\n.+\n.+)\nTelephone ", store_info)
    return {
        "store_name": safe_search(r"(.+)\n", store_info),
        "address": address.replace("\n", ", ") if address else None,
        "phone": safe_search(r"Telephone :  (.+)\n", store_info),
        "siret": safe_search(r"SIRET (.+) -", store_info),
        "naf": safe_search(r"- NAF (.+)", store_info),
    }
