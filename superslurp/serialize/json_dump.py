from __future__ import annotations

from typing import Any

from superslurp.superslurp_typing import Receipt


def make_json_serializable(
    receipt: Receipt,
) -> dict[str, dict[str, Any]]:
    serializable_result: dict[str, Any] = {"items": {}}
    for key, value in receipt.items():
        if key == "items":
            for category, items in receipt["items"].items():
                serializable_result["items"][category.value] = items
            continue
        serializable_result[key] = value

    return serializable_result
