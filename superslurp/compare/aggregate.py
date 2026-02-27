from __future__ import annotations

import dataclasses
import json
from bisect import bisect_left
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from superslurp.compare.matcher import FuzzyMatcher

_CATEGORY_GROUPS: dict[str, str] = {
    # Fruits & Legumes
    "FRUITS ET LEGUMES": "Fruits & Legumes",
    "FRUITS": "Fruits & Legumes",
    "LEGUMES": "Fruits & Legumes",
    # Fromage
    "FROMAGE A LA COUPE": "Fromage",
    "FROMAGE COUPE": "Fromage",
    "FROMAGE COUPE EMBALLE": "Fromage",
    "FROMAGE LS": "Fromage",
    # Cremerie
    "CREMERIE L.S.": "Cremerie",
    "LAITS ET DERIVES": "Cremerie",
    "BEURRE": "Cremerie",
    "MARGARINES ET COMPOSES": "Cremerie",
    "OEUFS": "Cremerie",
    "ULTRA FRAIS": "Cremerie",
    "DESSERTS TOUT PRETS": "Cremerie",
    # Viande & Charcuterie
    "BOUCH.LS.INDUST.": "Viande & Charcuterie",
    "BOUCH.VOL.ATELIER": "Viande & Charcuterie",
    "BOUCHERIE FRAICHE PREEMB": "Viande & Charcuterie",
    "BOUCH.LS (UVCI)": "Viande & Charcuterie",
    "VOL.LS INDUST.": "Viande & Charcuterie",
    "VOL.LS STANDARD": "Viande & Charcuterie",
    "CHARC.TRAIT.SAUC.SECS L": "Viande & Charcuterie",
    "CHARCT.LS UVCI": "Viande & Charcuterie",
    "CHARCT.TRAIT.TRADT.": "Viande & Charcuterie",
    "CHARCUTERIE FRAICH EMBAL": "Viande & Charcuterie",
    "TRAITEUR FRAIS EMBALLE": "Viande & Charcuterie",
    "TRAITEUR LS UVCI": "Viande & Charcuterie",
    # Poisson
    "POISSON LS UVCI": "Poisson",
    "POISSON TRADITIONNEL": "Poisson",
    "POISSONNERIE": "Poisson",
    "VENTE DIVERSE POISSON AR": "Poisson",
    "CONSERVES DE POISSON": "Poisson",
    # Boulangerie
    "BOULANGERIE": "Boulangerie",
    "BVP": "Boulangerie",
    "VIENNOISERIE": "Boulangerie",
    "VIENNOISERIE INDUSTRIELLE": "Boulangerie",
    "PATISSERIE": "Boulangerie",
    "PATIS.INDUSTRIELLE": "Boulangerie",
    "PAT INDUSTRIELLE": "Boulangerie",
    "PAIN DE MIE (LS)": "Boulangerie",
    "AIDE PATISSERIE": "Boulangerie",
    # Epicerie
    "EPICERIE": "Epicerie",
    "PATES": "Epicerie",
    "FARINES ET FECULENTS": "Epicerie",
    "COUSCOUS PUREE LEG SECS BLE": "Epicerie",
    "CONSERVES DE LEGUMES": "Epicerie",
    "CONSERVES DE VIANDES": "Epicerie",
    "CEREALES ET POUDRES CHOCOLAT": "Epicerie",
    "CONFITURES MIEL P.A.TARTINER": "Epicerie",
    "HUILES": "Epicerie",
    "SEL": "Epicerie",
    "SUCRES": "Epicerie",
    "VINAIGRES ET VINAIGRETTES": "Epicerie",
    "CONDIMENTS-SAUCES FROIDE": "Epicerie",
    "SAUCES CHAUDES": "Epicerie",
    "PRODUITS ETRANGERS": "Epicerie",
    # Sucre
    "BISCUITS SUCRES": "Sucre",
    "CHOCOLATS TABLETTES": "Sucre",
    "CONFISERIE CAISSE": "Sucre",
    # Boissons
    "LIQUIDES": "Boissons",
    "BOISSONS SANS ALCOOL": "Boissons",
    "JUS DE FRUITS FRAIS": "Boissons",
    "JUS ET NECTARS": "Boissons",
    "SIROPS": "Boissons",
    "THES ET INFUSIONS": "Boissons",
    # Surgeles
    "SURGELES": "Surgeles",
    "SURGELE SALE": "Surgeles",
    "SURGELE SUCRE": "Surgeles",
    # Bebe
    "ALIMENTS POUR ENFANTS": "Bebe",
    # Hygiene
    "BEAUTE SANTE": "Hygiene",
    "HYGIENE FEMININE": "Hygiene",
    "PARFUMERIE": "Hygiene",
    "PETITE PARAPHARMACIE": "Hygiene",
    "COTON": "Hygiene",
    # Entretien
    "ENTRETIEN": "Entretien",
    "ENTRETIEN DU LINGE": "Entretien",
    "PRODUITS VAISSELLE": "Entretien",
    "EMBALLAGE MENAGER": "Entretien",
    "PAPIER TOILETTE": "Entretien",
    # Maison
    "EQUIPEMENT DE LA MAISON": "Maison",
    "BRICOLAGE": "Maison",
    "BRICOLAGE JARDINAGE AUT": "Maison",
    "BAZAR A SERVICE": "Maison",
    "LA CUISINE": "Maison",
    "LINGE DE MAISON": "Maison",
    "CULTURE": "Maison",
    "LOISIRS": "Maison",
    "JOUETS": "Maison",
    "PAPETERIE ECRITURE": "Maison",
    "CHIEN-CHAT": "Maison",
    # Textile
    "VETEMENT": "Textile",
    "VETEMENT FEMME": "Textile",
    "CHAUSSURE": "Textile",
    "COLLANT-CHAUSSETTES": "Textile",
    "EQUIPEMENT": "Textile",
    "SOUS-VETEMENT": "Textile",
    "S.VETEMENT LAYETTE": "Textile",
}


def _extract_location(store: dict[str, Any]) -> str | None:
    """Extract city/location from a store's address lines."""
    if not (address := store.get("address")):
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
    if (store_id := f"{siret}_{naf}") not in stores:
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
    if (key := (date, store_id)) not in sessions:
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
    if props := item.get("properties"):
        # Iterate the (small) props dict rather than always checking 10 keys
        obs.update({k: v for k, v in props.items() if v and k in _OBS_PROP_KEYS})
    return obs


@dataclasses.dataclass
class _AggregateState:
    """Mutable accumulators shared across receipt processing."""

    matcher: FuzzyMatcher
    products: dict[str, list[dict[str, Any]]] = dataclasses.field(default_factory=dict)
    stores: dict[str, dict[str, Any]] = dataclasses.field(default_factory=dict)
    sessions: dict[tuple[str | None, str | None], dict[str, Any]] = dataclasses.field(
        default_factory=dict
    )
    session_totals: dict[int, float] = dataclasses.field(default_factory=dict)
    session_cat_totals: dict[int, dict[str, float]] = dataclasses.field(
        default_factory=dict
    )


def _process_receipt(
    receipt: dict[str, Any],
    state: _AggregateState,
) -> None:
    date = receipt.get("date")
    store_id = _get_store_id(receipt.get("store", {}), state.stores)
    session_id = _get_session_id(date, store_id, state.sessions)
    items_by_category: dict[str, list[dict[str, Any]]] = receipt.get("items", {})
    session_total = 0.0
    for category, category_items in items_by_category.items():
        group = _CATEGORY_GROUPS.get(category, "Autre")
        for item in category_items:
            key = state.matcher.match(item["name"])
            obs = _build_observation(item, session_id)
            state.products.setdefault(key, []).append(obs)
            spent = obs["price"] * obs["quantity"]
            session_total += spent
            cat_acc = state.session_cat_totals.setdefault(session_id, {})
            cat_acc[group] = cat_acc.get(group, 0) + spent
    state.session_totals[session_id] = (
        state.session_totals.get(session_id, 0) + session_total
    )


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


def _compute_category_rolling_averages(  # pylint: disable=too-many-locals
    session_cat_totals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute 5-week rolling averages per macro category.

    Returns one data point per week, each with per-category averaged values.
    Weeks more than 4 weeks away from any session are skipped (data gaps).
    """
    if not session_cat_totals:
        return []

    # Parse all session dates and collect category names
    all_cats: set[str] = set()
    session_points: list[tuple[datetime, dict[str, float]]] = []
    for entry in session_cat_totals:
        dt = datetime.strptime(entry["date"], "%Y-%m-%d")
        session_points.append((dt, entry["categories"]))
        all_cats.update(entry["categories"])

    session_points.sort(key=lambda p: p[0])

    # Monday-aligned week grid
    first_dt = session_points[0][0]
    min_week = first_dt - timedelta(days=first_dt.weekday())
    max_dt = session_points[-1][0]
    num_weeks = (max_dt - min_week).days // 7 + 2

    # Bucket spending per category per week
    cat_week_sums: dict[str, list[float]] = {cat: [0.0] * num_weeks for cat in all_cats}
    for dt, categories in session_points:
        idx = (dt - min_week).days // 7
        for cat, val in categories.items():
            cat_week_sums[cat][idx] += val

    # Gap detection via bisect (skip weeks >4 weeks from any session)
    max_gap_secs = timedelta(weeks=4).total_seconds()
    sorted_dts = sorted(dt for dt, _ in session_points)

    result = []
    for i in range(num_weeks):
        w_start = min_week + timedelta(weeks=i)
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

        lo = max(0, i - 2)
        hi = min(num_weeks, i + 3)
        window_len = hi - lo
        cats: dict[str, float] = {}
        for cat in all_cats:
            if (avg := sum(cat_week_sums[cat][lo:hi]) / window_len) > 0:
                cats[cat] = round(avg, 2)

        if cats:
            result.append(
                {
                    "date": w_start.strftime("%Y-%m-%d"),
                    "categories": cats,
                }
            )
    return result


def _compute_session_category_totals(
    sessions: list[dict[str, Any]],
    cat_totals: dict[int, dict[str, float]],
) -> list[dict[str, Any]]:
    """Format per-category session totals into sorted output list."""
    result = []
    for session in sessions:
        sid = session["id"]
        if sid in cat_totals and session["date"] is not None:
            result.append(
                {
                    "date": session["date"][:10],
                    "session_id": sid,
                    "categories": {k: round(v, 2) for k, v in cat_totals[sid].items()},
                }
            )
    result.sort(key=lambda e: str(e["date"]))
    return result


def compare_receipt_dicts(
    receipts: list[dict[str, Any]],
    threshold: float = 0.90,
) -> dict[str, Any]:
    """Aggregate items across parsed receipt dicts into a price comparison."""
    state = _AggregateState(matcher=FuzzyMatcher(threshold=threshold))

    for receipt in receipts:
        _process_receipt(receipt, state)

    result = [
        {"canonical_name": name, "observations": obs}
        for name, obs in state.products.items()
    ]
    result.sort(key=lambda p: str(p["canonical_name"]))
    session_list = sorted(state.sessions.values(), key=lambda s: s["id"])
    session_totals = _compute_session_totals(session_list, state.session_totals)
    session_cat_totals = _compute_session_category_totals(
        session_list, state.session_cat_totals
    )
    cat_rolling = _compute_category_rolling_averages(session_cat_totals)
    return {
        "stores": list(state.stores.values()),
        "sessions": session_list,
        "session_totals": session_totals,
        "session_category_totals": session_cat_totals,
        "category_rolling_averages": cat_rolling,
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
