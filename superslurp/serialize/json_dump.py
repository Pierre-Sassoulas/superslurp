from __future__ import annotations

from typing import Any

from superslurp.superslurp_typing import Receipt


def _serialize_item(
    item: dict[str, Any],
    include_raw: bool,
) -> dict[str, Any]:
    entry = dict(item)
    if not include_raw:
        entry.pop("raw", None)
    entry.pop("raw_name", None)
    return entry


def make_json_serializable(
    receipt: Receipt,
    include_raw: bool = True,
) -> dict[str, dict[str, Any]]:
    serializable_result: dict[str, Any] = {"items": {}}
    for key, value in receipt.items():
        if key == "items":
            for category, items in receipt["items"].items():
                serializable_result["items"][category.value] = [
                    _serialize_item(dict(item), include_raw) for item in items
                ]
            continue
        serializable_result[key] = value

    return serializable_result
