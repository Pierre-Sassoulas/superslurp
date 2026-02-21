from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from superslurp.compare.matcher import FuzzyMatcher


def _extract_location(store: dict[str, Any]) -> str | None:
    """Extract city/location from a store's address lines."""
    address = store.get("address")
    if not address:
        return None
    lines = [line.strip() for line in address.strip().split("\n") if line.strip()]
    # V1: line 0 = street, line 1 = city, line 2 = postal code
    # V2: line 0 = partial street (used as fallback)
    if len(lines) >= 2:
        return str(lines[1])
    if lines:
        return str(lines[0])
    return None


def _build_observation(
    item: dict[str, Any],
    date: str | None,
    store_name: str | None,
    location: str | None,
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
        "store": store_name,
        "location": location,
    }


def _sort_key_observation(obs: dict[str, Any]) -> tuple[int, str]:
    """Sort by date ascending, nulls last."""
    if obs["date"] is None:
        return (1, "")
    return (0, obs["date"])


def _process_receipt(
    receipt: dict[str, Any],
    matcher: FuzzyMatcher,
    products: dict[tuple[str, float | None], list[dict[str, Any]]],
) -> None:
    date = receipt.get("date")
    store_data: dict[str, Any] = receipt.get("store", {})
    store_name = store_data.get("store_name")
    location = _extract_location(store_data)
    items_by_category: dict[str, list[dict[str, Any]]] = receipt.get("items", {})
    for category_items in items_by_category.values():
        for item in category_items:
            grams: float | None = item.get("grams")
            key = matcher.match(item["name"], grams)
            obs = _build_observation(item, date, store_name, location, grams)
            products.setdefault(key, []).append(obs)


def compare_receipt_dicts(
    receipts: list[dict[str, Any]], threshold: float = 0.90
) -> dict[str, Any]:
    """Aggregate items across parsed receipt dicts into a price comparison."""
    matcher = FuzzyMatcher(threshold=threshold)
    # (canonical_name, grams) -> list of observations
    products: dict[tuple[str, float | None], list[dict[str, Any]]] = {}

    for receipt in receipts:
        _process_receipt(receipt, matcher, products)

    result = []
    for (canonical_name, grams), observations in products.items():
        observations.sort(key=_sort_key_observation)
        result.append(
            {
                "canonical_name": canonical_name,
                "grams": grams,
                "observations": observations,
            }
        )
    result.sort(key=lambda p: str(p["canonical_name"]))
    return {"products": result}


def compare_receipt_files(paths: list[Path], threshold: float = 0.90) -> dict[str, Any]:
    """Load JSON receipt files and aggregate items for price comparison."""
    receipts: list[dict[str, Any]] = []
    for path in paths:
        with open(path, encoding="utf8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "items" not in data:
            continue
        receipts.append(data)
    return compare_receipt_dicts(receipts, threshold=threshold)
