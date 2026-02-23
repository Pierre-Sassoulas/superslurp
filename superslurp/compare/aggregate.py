from __future__ import annotations

import json
from datetime import datetime, timedelta
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
    """Return the store id for this receipt's store, registering it if new.

    The store id is the SIRET + NAF concatenated with an underscore.
    """
    siret = store_data.get("siret")
    naf = store_data.get("naf")
    if siret is None or naf is None:
        return None
    store_id = f"{siret}_{naf}"
    if store_id not in stores:
        stores[store_id] = {
            "id": store_id,
            "store_name": store_data.get("store_name"),
            "location": _extract_location(store_data),
            "siret": siret,
            "naf": naf,
        }
    return store_id


def _get_session_id(
    date: str | None,
    store_id: str | None,
    sessions: dict[tuple[str | None, str | None], dict[str, Any]],
) -> int:
    """Return the session id for this receipt, registering it if new."""
    key = (date, store_id)
    if key not in sessions:
        session_id = len(sessions) + 1
        sessions[key] = {
            "id": session_id,
            "date": date,
            "store_id": store_id,
        }
    return int(sessions[key]["id"])


def _build_observation(
    item: dict[str, Any],
    session_id: int,
) -> dict[str, Any]:
    price: float = item["price"]
    grams: float | None = item.get("grams")
    price_per_kg: float | None = None
    if grams is not None:
        price_per_kg = round((price / grams) * 1000, 2)
    unit_count: int | None = item.get("units")
    price_per_unit: float | None = None
    if unit_count is not None:
        price_per_unit = round(price / unit_count, 4)
    obs: dict[str, Any] = {
        "original_name": item["name"],
        "session_id": session_id,
        "price": price,
        "quantity": item.get("bought", 1),
        "grams": grams,
        "discount": item.get("discount"),
        "price_per_kg": price_per_kg,
        "unit_count": unit_count,
        "price_per_unit": price_per_unit,
        "fat_pct": item.get("fat_pct"),
    }
    if item.get("bio"):
        obs["bio"] = True
    milk = item.get("milk_treatment")
    if milk:
        obs["milk_treatment"] = milk
    return obs


def _process_receipt(
    receipt: dict[str, Any],
    matcher: FuzzyMatcher,
    products: dict[str, list[dict[str, Any]]],
    stores: dict[str, dict[str, Any]],
    sessions: dict[tuple[str | None, str | None], dict[str, Any]],
) -> None:
    date = receipt.get("date")
    store_data: dict[str, Any] = receipt.get("store", {})
    store_id = _get_store_id(store_data, stores)
    session_id = _get_session_id(date, store_id, sessions)
    items_by_category: dict[str, list[dict[str, Any]]] = receipt.get("items", {})
    for category_items in items_by_category.values():
        for item in category_items:
            key = matcher.match(item["name"])
            obs = _build_observation(item, session_id)
            products.setdefault(key, []).append(obs)


def _compute_session_totals(
    sessions: list[dict[str, Any]],
    products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute the total spent per session."""
    totals: dict[int, float] = {}
    for product in products:
        for obs in product["observations"]:
            sid = obs["session_id"]
            totals[sid] = totals.get(sid, 0) + obs["price"] * obs["quantity"]
    result = []
    for session in sessions:
        sid = session["id"]
        if sid in totals and session["date"] is not None:
            result.append(
                {
                    "session_id": sid,
                    "date": session["date"][:10],
                    "total": round(totals[sid], 2),
                }
            )
    result.sort(key=lambda e: str(e["date"]))
    return result


def _build_weekly_sums(
    points: list[tuple[datetime, float]],
) -> tuple[list[datetime], list[float]]:
    """Bucket session totals into Monday-aligned weeks."""
    week = timedelta(weeks=1)
    first_dt = points[0][0]
    min_week = first_dt - timedelta(days=first_dt.weekday())
    max_dt = points[-1][0]
    week_starts: list[datetime] = []
    week_sums: list[float] = []
    w = min_week
    while w <= max_dt + week:
        total = sum(t for dt, t in points if w <= dt < w + week)
        week_starts.append(w)
        week_sums.append(total)
        w += week
    return week_starts, week_sums


def _compute_rolling_average(
    session_totals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute a 5-week rolling average (current week +/- 2 weeks).

    Returns one data point per week. Weeks more than 4 weeks away from
    any session are skipped (data gaps).
    """
    if not session_totals:
        return []

    points = [
        (datetime.strptime(e["date"], "%Y-%m-%d"), e["total"]) for e in session_totals
    ]
    week_starts, week_sums = _build_weekly_sums(points)

    max_gap_secs = timedelta(weeks=4).total_seconds()
    result = []
    for i, w_start in enumerate(week_starts):
        nearest = min(abs((dt - w_start).total_seconds()) for dt, _ in points)
        if nearest > max_gap_secs:
            continue
        window = [
            week_sums[j] for j in range(max(0, i - 2), min(len(week_sums), i + 3))
        ]
        result.append(
            {
                "date": w_start.strftime("%Y-%m-%d"),
                "value": round(sum(window) / len(window), 2),
            }
        )
    return result


def compare_receipt_dicts(
    receipts: list[dict[str, Any]],
    threshold: float = 0.90,
) -> dict[str, Any]:
    """Aggregate items across parsed receipt dicts into a price comparison."""
    matcher = FuzzyMatcher(threshold=threshold)
    products: dict[str, list[dict[str, Any]]] = {}
    stores: dict[str, dict[str, Any]] = {}
    sessions: dict[tuple[str | None, str | None], dict[str, Any]] = {}

    for receipt in receipts:
        _process_receipt(receipt, matcher, products, stores, sessions)

    result = []
    for canonical_name, observations in products.items():
        result.append(
            {
                "canonical_name": canonical_name,
                "observations": observations,
            }
        )
    result.sort(key=lambda p: str(p["canonical_name"]))
    session_list = sorted(sessions.values(), key=lambda s: s["id"])
    session_totals = _compute_session_totals(session_list, result)
    rolling_avg = _compute_rolling_average(session_totals)
    return {
        "stores": list(stores.values()),
        "sessions": session_list,
        "session_totals": session_totals,
        "rolling_average": rolling_avg,
        "products": result,
    }


def compare_receipt_files(
    paths: list[Path],
    threshold: float = 0.90,
) -> dict[str, Any]:
    """Load JSON receipt files and aggregate items for price comparison."""
    receipts: list[dict[str, Any]] = []
    for path in paths:
        with open(path, encoding="utf8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "items" not in data:
            continue
        receipts.append(data)
    return compare_receipt_dicts(receipts, threshold=threshold)
