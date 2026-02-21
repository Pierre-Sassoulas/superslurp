from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from superslurp.compare.matcher import FuzzyMatcher


def _build_observation(
    item: dict[str, Any],
    date: str | None,
    source: str | None,
    grams: float | None,
) -> dict[str, Any]:
    price: float = item["price"]
    price_per_kg: float | None = None
    if grams is not None:
        price_per_kg = round((price / grams) * 1000, 2)
    return {
        "date": date,
        "price": price,
        "quantity": item.get("quantity", 1),
        "discount": item.get("discount"),
        "price_per_kg": price_per_kg,
        "source": source,
    }


def _compute_stats(
    observations: list[dict[str, Any]], grams: float | None
) -> dict[str, Any]:
    prices = [o["price"] for o in observations]
    stats: dict[str, Any] = {
        "observation_count": len(observations),
        "min_price": round(min(prices), 2),
        "max_price": round(max(prices), 2),
        "avg_price": round(sum(prices) / len(prices), 2),
    }
    if grams is not None:
        ppk = [o["price_per_kg"] for o in observations]
        stats["min_price_per_kg"] = round(min(ppk), 2)
        stats["max_price_per_kg"] = round(max(ppk), 2)
        stats["avg_price_per_kg"] = round(sum(ppk) / len(ppk), 2)
    return stats


def _sort_key_observation(obs: dict[str, Any]) -> tuple[int, str]:
    """Sort by date ascending, nulls last."""
    if obs["date"] is None:
        return (1, "")
    return (0, obs["date"])


def compare_receipt_dicts(
    receipts: list[dict[str, Any]], threshold: float = 0.90
) -> dict[str, Any]:
    """Aggregate items across parsed receipt dicts into a price comparison.

    Each dict in the list is a serialized Receipt (as loaded from JSON)
    with an optional ``"_source"`` key for the filename.
    """
    matcher = FuzzyMatcher(threshold=threshold)
    # (canonical_name, grams) -> list of observations
    products: dict[tuple[str, float | None], list[dict[str, Any]]] = {}

    for receipt in receipts:
        date = receipt.get("date")
        source = receipt.get("_source")
        items_by_category: dict[str, list[dict[str, Any]]] = receipt.get(
            "items", {}
        )
        for category_items in items_by_category.values():
            for item in category_items:
                grams: float | None = item.get("grams")
                name: str = item["name"]
                key = matcher.match(name, grams)
                obs = _build_observation(item, date, source, grams)
                products.setdefault(key, []).append(obs)

    result = []
    for (canonical_name, grams), observations in products.items():
        observations.sort(key=_sort_key_observation)
        result.append(
            {
                "canonical_name": canonical_name,
                "grams": grams,
                "observations": observations,
                "stats": _compute_stats(observations, grams),
            }
        )
    result.sort(key=lambda p: p["canonical_name"])
    return {"products": result}


def compare_receipt_files(
    paths: list[Path], threshold: float = 0.90
) -> dict[str, Any]:
    """Load JSON receipt files and aggregate items for price comparison."""
    receipts: list[dict[str, Any]] = []
    for path in paths:
        with open(path, encoding="utf8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "items" not in data:
            continue
        data["_source"] = path.name
        receipts.append(data)
    return compare_receipt_dicts(receipts, threshold=threshold)
