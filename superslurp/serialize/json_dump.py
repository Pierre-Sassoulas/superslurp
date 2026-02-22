from __future__ import annotations

from typing import Any

from superslurp.superslurp_typing import Receipt


def make_json_serializable(
    receipt: Receipt,
    include_raw: bool = True,
) -> dict[str, dict[str, Any]]:
    serializable_result: dict[str, Any] = {"items": {}}
    for key, value in receipt.items():
        if key == "items":
            for category, items in receipt["items"].items():
                if include_raw:
                    serializable_result["items"][category.value] = items
                else:
                    serializable_result["items"][category.value] = [
                        {k: v for k, v in item.items() if k != "raw"} for item in items
                    ]
            continue
        serializable_result[key] = value

    return serializable_result
