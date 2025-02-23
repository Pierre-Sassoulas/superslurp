from __future__ import annotations

import enum
from typing import TypedDict


class Item(TypedDict):
    name: str
    price: float
    quantity: int | None
    grams: float | None
    tr: bool


class Category(enum.Enum):
    FRUITS_ET_LEGUMES = "FRUITS ET LEGUMES"
    PAT_INDUSTRIELLE = "PAT INDUSTRIELLE"
    EPICERIE = "EPICERIE"
    BRICOLAGE_JARDINAGE_AUT = "BRICOLAGE JARDINAGE AUT"
    FROMAGE_A_LA_COUPE = "FROMAGE A LA COUPE"
    BEAUTE_SANTE = "BEAUTE SANTE"
    CREMERIE_LS = "CREMERIE L.S."
    VOL_LS_INDUST = "VOL.LS INDUST."
    ENTRETIEN = "ENTRETIEN"
    LIQUIDES = "LIQUIDES"

    DISCOUNT = "DISCOUNT"
    UNDEFINED = "AUTRE"
