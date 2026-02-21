from __future__ import annotations

from superslurp.parse.safe_search import safe_search
from superslurp.superslurp_typing import Store


def parse_store_info(store_info: str) -> Store:
    address = safe_search(r"\n(.+\n.+\n.+)\nTelephone ", store_info)
    return {
        "store_name": safe_search(r"(.+)\n", store_info),
        "address": address.replace("\n", ", ") if address else None,
        "phone": safe_search(r"Telephone :  (.+)\n", store_info),
        "siret": safe_search(r"SIRET (.+) -", store_info),
        "naf": safe_search(r"- NAF (.+)", store_info),
    }
