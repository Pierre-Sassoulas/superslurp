from __future__ import annotations

from typing import Any

from superslurp.parse.v1.parse_items import _parse_name_attributes
from superslurp.superslurp_typing import Receipt


def _serialize_item(
    item: dict[str, Any],
    include_raw: bool,
    synonyms: dict[str, str] | None,
) -> dict[str, Any]:
    entry = dict(item)
    if synonyms:
        name, grams, units, fat_pct = _parse_name_attributes(
            str(entry["raw_name"]), synonyms=synonyms
        )
        entry["name"] = name
        if grams is not None:
            entry["grams"] = grams
        if units is not None:
            entry["units"] = units
        entry["fat_pct"] = fat_pct
    if not include_raw:
        entry.pop("raw", None)
    entry.pop("raw_name", None)
    return entry


def make_json_serializable(
    receipt: Receipt,
    include_raw: bool = True,
    synonyms: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    serializable_result: dict[str, Any] = {"items": {}}
    for key, value in receipt.items():
        if key == "items":
            for category, items in receipt["items"].items():
                serializable_result["items"][category.value] = [
                    _serialize_item(dict(item), include_raw, synonyms) for item in items
                ]
            continue
        serializable_result[key] = value

    return serializable_result
