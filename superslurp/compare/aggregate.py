from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from superslurp.compare.matcher import FuzzyMatcher
from superslurp.compare.normalize import is_bio


def _extract_location(store: dict[str, Any]) -> str | None:
    """Extract city/location from a store's address lines."""
    address = store.get("address")
    if not address:
        return None
    lines = [line.strip() for line in address.strip().split("\n") if line.strip()]
    # V1: line 0 = street, line 1 = city, line 2 = postal code
    # V2: line 0 = street, line 1 = city, line 2 = postal code
    if len(lines) >= 2:
        return str(lines[1])
    if lines:
        return str(lines[0])
    return None


def _get_store_id(
    store_data: dict[str, Any],
    stores: dict[str, dict[str, Any]],
) -> str | None:
    """Return the store id for this receipt's store, registering it if new."""
    store_name = store_data.get("store_name")
    location = _extract_location(store_data)
    if store_name is None and location is None:
        return None
    # Use (store_name, location) as natural key
    store_id = f"{store_name or ''} - {location or ''}"
    if store_id not in stores:
        stores[store_id] = {
            "id": store_id,
            "store_name": store_name,
            "location": location,
        }
    return store_id


def _build_observation(
    item: dict[str, Any],
    date: str | None,
    store_id: str | None,
) -> dict[str, Any]:
    price: float = item["price"]
    grams: float | None = item.get("grams")
    price_per_kg: float | None = None
    if grams is not None:
        price_per_kg = round((price / grams) * 1000, 2)
    obs: dict[str, Any] = {
        "date": date,
        "price": price,
        "quantity": item.get("quantity", 1),
        "grams": grams,
        "discount": item.get("discount"),
        "price_per_kg": price_per_kg,
        "store_id": store_id,
    }
    if is_bio(item["name"]):
        obs["bio"] = True
    return obs


def _sort_key_observation(obs: dict[str, Any]) -> tuple[int, str]:
    """Sort by date ascending, nulls last."""
    if obs["date"] is None:
        return (1, "")
    return (0, obs["date"])


def _process_receipt(
    receipt: dict[str, Any],
    matcher: FuzzyMatcher,
    products: dict[str, list[dict[str, Any]]],
    stores: dict[str, dict[str, Any]],
) -> None:
    date = receipt.get("date")
    store_data: dict[str, Any] = receipt.get("store", {})
    store_id = _get_store_id(store_data, stores)
    items_by_category: dict[str, list[dict[str, Any]]] = receipt.get("items", {})
    for category_items in items_by_category.values():
        for item in category_items:
            key = matcher.match(item["name"])
            obs = _build_observation(item, date, store_id)
            products.setdefault(key, []).append(obs)


def compare_receipt_dicts(
    receipts: list[dict[str, Any]], threshold: float = 0.90
) -> dict[str, Any]:
    """Aggregate items across parsed receipt dicts into a price comparison."""
    matcher = FuzzyMatcher(threshold=threshold)
    products: dict[str, list[dict[str, Any]]] = {}
    stores: dict[str, dict[str, Any]] = {}

    for receipt in receipts:
        _process_receipt(receipt, matcher, products, stores)

    result = []
    for canonical_name, observations in products.items():
        observations.sort(key=_sort_key_observation)
        result.append(
            {
                "canonical_name": canonical_name,
                "observations": observations,
            }
        )
    result.sort(key=lambda p: str(p["canonical_name"]))
    return {
        "stores": list(stores.values()),
        "products": result,
    }


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
