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
    return {
        "store_name": safe_search(r"(.+)\n", store_info),
        "address": safe_search(r"\n(.+\n.+\n.+)\nTelephone ", store_info),
        "phone": safe_search(r"Telephone :  (.+)\n", store_info),
        "siret": safe_search(r"SIRET (.+) -", store_info),
        "naf": safe_search(r"NAF (.+)\n", store_info),
    }
