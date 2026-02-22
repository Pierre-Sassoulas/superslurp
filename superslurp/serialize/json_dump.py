from __future__ import annotations

from typing import Any

from superslurp.compare.normalize import expand_synonyms
from superslurp.superslurp_typing import Receipt


def make_json_serializable(
    receipt: Receipt,
    include_raw: bool = True,
    synonyms: dict[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    serializable_result: dict[str, Any] = {"items": {}}
    for key, value in receipt.items():
        if key == "items":
            for category, items in receipt["items"].items():
                serialized: list[dict[str, Any]] = []
                for item in items:
                    entry = dict(item)
                    if synonyms:
                        entry["name"] = expand_synonyms(str(entry["name"]), synonyms)
                    if not include_raw:
                        entry.pop("raw", None)
                    serialized.append(entry)
                serializable_result["items"][category.value] = serialized
            continue
        serializable_result[key] = value

    return serializable_result
