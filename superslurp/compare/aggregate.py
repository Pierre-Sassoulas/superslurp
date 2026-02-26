from __future__ import annotations

import json
from bisect import bisect_left
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


_OBS_PROP_KEYS = frozenset(
    {
        "bio",
        "milk_treatment",
        "production",
        "brand",
        "label",
        "packaging",
        "origin",
        "affinage_months",
        "baby_months",
        "baby_recipe",
    }
)


def _build_observation(
    item: dict[str, Any],
    session_id: int,
) -> dict[str, Any]:
    price: float = item["price"]
    grams: float | None = item.get("grams")
    volume_ml: float | None = item.get("volume_ml")
    obs: dict[str, Any] = {
        "original_name": item["name"],
        "session_id": session_id,
        "price": price,
        "quantity": item.get("bought", 1),
        "grams": grams,
        "discount": item.get("discount"),
        "price_per_kg": round(price / grams * 1000, 2) if grams else None,
        "volume_ml": volume_ml,
        "price_per_liter": round(price / volume_ml * 1000, 2) if volume_ml else None,
        "unit_count": item.get("units") or 1,
        "fat_pct": item.get("fat_pct"),
    }
    props = item.get("properties")
    if props:
        # Iterate the (small) props dict rather than always checking 10 keys
        obs.update({k: v for k, v in props.items() if v and k in _OBS_PROP_KEYS})
    return obs


def _process_receipt(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    receipt: dict[str, Any],
    matcher: FuzzyMatcher,
    products: dict[str, list[dict[str, Any]]],
    stores: dict[str, dict[str, Any]],
    sessions: dict[tuple[str | None, str | None], dict[str, Any]],
    session_totals: dict[int, float],
) -> None:
    date = receipt.get("date")
    store_data: dict[str, Any] = receipt.get("store", {})
    store_id = _get_store_id(store_data, stores)
    session_id = _get_session_id(date, store_id, sessions)
    items_by_category: dict[str, list[dict[str, Any]]] = receipt.get("items", {})
    session_total = 0.0
    for category_items in items_by_category.values():
        for item in category_items:
            key = matcher.match(item["name"])
            obs = _build_observation(item, session_id)
            products.setdefault(key, []).append(obs)
            session_total += obs["price"] * obs["quantity"]
    session_totals[session_id] = session_totals.get(session_id, 0) + session_total


def _compute_session_totals(
    sessions: list[dict[str, Any]],
    totals: dict[int, float],
) -> list[dict[str, Any]]:
    """Format pre-computed session totals into sorted output list."""
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
    first_dt = points[0][0]
    min_week = first_dt - timedelta(days=first_dt.weekday())
    max_dt = points[-1][0]
    # Bucket points by week offset in O(P)
    buckets: dict[int, float] = {}
    for dt, total in points:
        idx = (dt - min_week).days // 7
        buckets[idx] = buckets.get(idx, 0) + total
    # Build contiguous week list in O(W)
    num_weeks = (max_dt - min_week).days // 7 + 2
    week_starts: list[datetime] = []
    week_sums: list[float] = []
    for i in range(num_weeks):
        week_starts.append(min_week + timedelta(weeks=i))
        week_sums.append(buckets.get(i, 0))
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
    # Pre-sort session datetimes for O(log P) nearest-point lookup via bisect
    sorted_dts = sorted(dt for dt, _ in points)
    result = []
    for i, w_start in enumerate(week_starts):
        j = bisect_left(sorted_dts, w_start)
        nearest = min(
            (
                abs((sorted_dts[k] - w_start).total_seconds())
                for k in (j - 1, j)
                if 0 <= k < len(sorted_dts)
            ),
        )
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
    session_totals_acc: dict[int, float] = {}

    for receipt in receipts:
        _process_receipt(
            receipt, matcher, products, stores, sessions, session_totals_acc
        )

    result = [
        {"canonical_name": name, "observations": obs} for name, obs in products.items()
    ]
    result.sort(key=lambda p: str(p["canonical_name"]))
    session_list = sorted(sessions.values(), key=lambda s: s["id"])
    session_totals = _compute_session_totals(session_list, session_totals_acc)
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
