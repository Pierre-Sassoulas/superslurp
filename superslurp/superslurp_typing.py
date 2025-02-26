from __future__ import annotations

import enum
from typing import TypedDict

from superslurp.parse_store import Store


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
    FROMAGE_A_LA_COUPE = "FROMAGE A LA COUPE"
    BEAUTE_SANTE = "BEAUTE SANTE"
    CREMERIE_LS = "CREMERIE L.S."
    VOL_LS_INDUST = "VOL.LS INDUST."
    ENTRETIEN = "ENTRETIEN"
    LIQUIDES = "LIQUIDES"
    BOUCHERIE_LS_INDUST = "BOUCH.LS.INDUST."
    CHARC_TRAIT_TRADT = "CHARCT.TRAIT.TRADT."
    BOUCH_VOL_ATELIER = "BOUCH.VOL.ATELIER"
    CHARC_TRAIT_SAUC_SECS = "CHARC.TRAIT.SAUC.SECS L"
    BVP = "BVP"
    POISSONNERIE = "POISSONNERIE"
    VETEMENT = "VETEMENT"
    EQUIPEMENT_DE_LA_MAISON = "EQUIPEMENT DE LA MAISON"
    BRICOLAGE_JARDINAGE_AUT = "BRICOLAGE JARDINAGE AUT"
    BAZAR_A_SERVICE = "BAZAR A SERVICE"
    SURGELES = "SURGELES"
    LOISIRS = "LOISIRS"
    CHAUSSURE = "CHAUSSURE"
    COLLANT_CHAUSSETTES = "COLLANT-CHAUSSETTES"
    EQUIPEMENT = "EQUIPEMENT"
    SOUS_VETEMENT = "SOUS-VETEMENT"

    DISCOUNT = "DISCOUNT"
    UNDEFINED = ""


Items = dict[Category, list[Item]]


class Receipt(TypedDict):
    date: str | None
    store: Store
    items: Items
    subtotal: float
    total_discount: float
    total: float
    number_of_items: int
    eligible_tr: float
    paid_tr: float
    # card_balance_previous: float
    # card_balance_earned: float
    # card_balance_new: float
