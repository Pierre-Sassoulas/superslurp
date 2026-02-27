from __future__ import annotations

import json
from pathlib import Path

from superslurp.compare.normalize import (
    compile_synonyms,
    expand_synonyms,
    extract_unit_count,
    get_affinage_months,
    get_baby_food_type,
    get_baby_recipe,
    get_brand,
    get_milk_treatment,
    get_packaging,
    get_production,
    get_quality_label,
    is_bio,
    normalize_for_matching,
    strip_affinage,
)
from superslurp.parse.common import (
    _get_volume,
    _infer_milk_fat_pct,
    _parse_name_attributes,
)

FIXTURES = Path(__file__).parent / "fixtures"


# --- normalize ---


def test_normalize_basic() -> None:
    assert normalize_for_matching("  brioche tressee  ") == "BRIOCHE TRESSEE"


def test_normalize_accents() -> None:
    assert normalize_for_matching("crème brûlée") == "CREME BRULEE"


def test_normalize_collapse_whitespace() -> None:
    assert normalize_for_matching("a   b\t c") == "A B C"


def test_normalize_strips_colors() -> None:
    assert normalize_for_matching("AIL BLANC") == "AIL"
    assert normalize_for_matching("AIL VIOLET") == "AIL"


def test_normalize_strips_packaging() -> None:
    assert normalize_for_matching("AIL BLC U BIO FILET") == "AIL"


def test_normalize_strips_count_pattern() -> None:
    assert normalize_for_matching("AIL BLANC 3 TETES") == "AIL"


def test_normalize_strips_origin() -> None:
    assert normalize_for_matching("NECTARINE JAUNE FR") == "NECTARINE"


# --- bio ---


def test_is_bio() -> None:
    assert is_bio("AIL BLC U BIO FILET") is True
    assert is_bio("AUBERGINE") is False
    assert is_bio("ABRICOT BIO") is True


# --- milk fat ---


def test_infer_milk_fat_pct_entier() -> None:
    assert _infer_milk_fat_pct("LAIT UHT ENTIER U BK 1 LITRE") == 3.6
    assert _infer_milk_fat_pct("LAIT UHT ENTIER U BRIQUE 6X1L") == 3.6
    assert _infer_milk_fat_pct("1L BK LAIT ENTIER UHT U") == 3.6


def test_infer_milk_fat_pct_demi_ecreme() -> None:
    assert _infer_milk_fat_pct("LAIT UHT 1/2 ECREM U BK 1L") == 1.5
    assert _infer_milk_fat_pct("LAIT DEMI-ECREME U 1L") == 1.5
    assert _infer_milk_fat_pct("LAIT DEMI ECREME LACTEL 6X1L") == 1.5


def test_infer_milk_fat_pct_ecreme() -> None:
    assert _infer_milk_fat_pct("LAIT ECREME U BK 1L") == 0.5


def test_infer_milk_fat_pct_no_match() -> None:
    assert _infer_milk_fat_pct("CREME UHT ENTIERE 35% U BK 1L") is None
    assert _infer_milk_fat_pct("CHOCOLAT LAIT/NOISET") is None
    assert _infer_milk_fat_pct("PAIN AU LAIT PASQUIER X10 350G") is None
    assert _infer_milk_fat_pct("BLEDILAIT CROISSANCE+ 12M 900G") is None
    assert _infer_milk_fat_pct("LAITUE ICEBERG") is None
    assert _infer_milk_fat_pct("SUCRE POUDRE 1KG") is None


# --- milk treatment ---


def test_get_milk_treatment() -> None:
    assert get_milk_treatment("FROMAGE BLANC NATURE LAIT PASTEURISE U") == "pasteurise"
    assert get_milk_treatment("BRIE PASTEURISE ROITELET") == "pasteurise"
    assert get_milk_treatment("BEAUFORT AOP LAIT CRU") == "cru"
    assert get_milk_treatment("REBLOCHON SAVOIE AOP LAIT CRU") == "cru"
    assert get_milk_treatment("TOMME AIL OURS LT PASTEURISE") == "pasteurise"
    assert get_milk_treatment("AUBERGINE") is None
    assert get_milk_treatment("BAGUETTE TRADITION") is None


# --- unit count ---


def test_extract_unit_count_x_pattern() -> None:
    assert extract_unit_count("OEUFS PA CAL.MIXTE U X12") == 12
    assert extract_unit_count("OEUFS LABEL X6") == 6
    assert extract_unit_count("SAUCISSE STRASBOURG HOT DOGX10") == 10


def test_extract_unit_count_btex_pattern() -> None:
    assert extract_unit_count("OEUFS PA LR CAL.MIXTE U BTEX12") == 12


def test_extract_unit_count_with_off() -> None:
    assert extract_unit_count("OEUF.PA.MOYEN LR LOUE X10+5OFF") == 15


def test_extract_unit_count_leading() -> None:
    assert extract_unit_count("18 OEUFS FRAIS") == 18


def test_extract_unit_count_leading_plus() -> None:
    assert extract_unit_count("3+1RAC TRUF ETE") == 4
    assert extract_unit_count("3+1RACL MOUTARDE") == 4


def test_extract_unit_count_leading_fraction() -> None:
    assert extract_unit_count("1/2 REBLOCH USAV") == 0.5


def test_extract_unit_count_none() -> None:
    assert extract_unit_count("OEUFS DATE COURTE") is None
    assert extract_unit_count("SUCRE POUDRE") is None


def test_normalize_strips_unit_count() -> None:
    assert normalize_for_matching("OEUFS PA CAL.MIXTE U X12") == "OEUFS"
    assert normalize_for_matching("18 OEUFS FRAIS") == "OEUFS"


# --- synonyms ---


def test_normalize_with_synonyms() -> None:
    synonyms = {"BLED": "BLEDINA", "CRST": "CROISSANT"}
    # BOL → PLAT BEBE, content stripped, 8M stripped (baby age)
    assert (
        normalize_for_matching("BLED BOL CAR/RZ/JAMB 8M", synonyms)
        == "BLEDINA PLAT BEBE"
    )
    assert normalize_for_matching("CRST CHOCO", synonyms) == "CROISSANT CHOCO"


def test_normalize_synonyms_after_dot_expansion() -> None:
    synonyms = {"BLED": "BLEDINA"}
    assert "BLEDINA" in normalize_for_matching("BLED.BOL", synonyms)


def test_normalize_synonyms_none_unchanged() -> None:
    # BOL → PLAT BEBE, content stripped; BLED stays without synonym expansion
    assert normalize_for_matching("BLED BOL") == "BLED PLAT BEBE"


def test_normalize_multiword_synonym_priority() -> None:
    """Multi-word patterns fire before single-word fallbacks."""
    synonyms = {
        "CHOCO PATIS": "CHOCOLAT PATISSIER",
        "CHOCO": "CHOCOLAT",
        "PATIS": "PATISSERIE",
    }
    # Multi-word match: CHOCO PATIS → CHOCOLAT PATISSIER
    result = normalize_for_matching("CHOCO.PATIS.NOIR 52%", synonyms)
    assert result == "CHOCOLAT PATISSIER 52%"
    # Single-word fallback: standalone PATIS → PATISSERIE
    result = normalize_for_matching("PATIS FRAMB", synonyms)
    assert result == "PATISSERIE FRAMB"
    # Single-word fallback: standalone CHOCO → CHOCOLAT
    result = normalize_for_matching("CHOCO NOIR", synonyms)
    assert result == "CHOCOLAT"


def test_normalize_dot_pattern_synonym() -> None:
    """Patterns with dots are normalized to spaces before matching."""
    synonyms = {"FROM.BLC": "FROMAGE BLANC", "FROM": "FROMAGE"}
    # BLANC is kept because FROMAGE BLANC is a protected compound
    result = normalize_for_matching("FROM.BLC NAT", synonyms)
    assert result == "FROMAGE BLANC NAT"
    # Standalone FROM fallback
    result = normalize_for_matching("FROM.RAPE", synonyms)
    assert result == "FROMAGE RAPE"


def test_synonyms_fixture_loads_and_expands() -> None:
    """Load synonyms.json fixture and verify real-world abbreviation expansion."""
    synonyms_path = FIXTURES / "synonyms.json"
    with open(synonyms_path, encoding="utf8") as f:
        synonyms: dict[str, str] = json.load(f)

    # TABS LAVE VAISS.STANDARD U → TABLETTES LAVE VAISSELLE STANDARD
    result = normalize_for_matching("TABS LAVE VAISS.STANDARD U", synonyms)
    assert result == "TABLETTES LAVE VAISSELLE STANDARD"

    # CHOCO.PATIS → CHOCOLAT PATISSIER (multi-word match, NOIR stripped as color)
    result = normalize_for_matching("CHOCO.PATIS.NOIR 52%", synonyms)
    assert result == "CHOCOLAT PATISSIER 52%"

    # FROM.BLC → FROMAGE BLANC (BLANC kept: protected compound), NAT expanded
    result = normalize_for_matching("FROM.BLC NAT.7,6%MG", synonyms)
    assert result == "FROMAGE BLANC NATURE 7,6%MG"

    # PAP.TOIL → PAPIER TOILETTE (BLC/U stripped)
    result = normalize_for_matching("PAP.TOIL.BLC 2PL.U", synonyms)
    assert result == "PAPIER TOILETTE 2PL"


def test_synonym_digit_lookahead() -> None:
    """Synonym followed by digits expands correctly after regex fix."""
    synonyms = compile_synonyms({"B MAMAN": "BONNE MAMAN"})
    assert expand_synonyms("B.MAMAN750G", synonyms) == "BONNE MAMAN750G"


def test_synonym_bmam_expansion() -> None:
    """BMAM abbreviation expands to BONNE MAMAN."""
    synonyms = compile_synonyms({"BMAM": "BONNE MAMAN"})
    assert expand_synonyms("BMAM CONF FRAISE", synonyms) == "BONNE MAMAN CONF FRAISE"


# --- volume ---


def test_get_volume_liters() -> None:
    name, vol, units = _get_volume("PUR JUS MULTIFRUITS U BIO 1L")
    assert vol == 1000.0
    assert units is None
    assert "1L" not in name


def test_get_volume_centiliters() -> None:
    name, vol, units = _get_volume("VIN ROGUE BORDEAUX 75CL")
    assert vol == 750.0
    assert units is None
    assert "75CL" not in name


def test_get_volume_milliliters() -> None:
    _name, vol, units = _get_volume("CREME LIQUIDE 250ML")
    assert vol == 250.0
    assert units is None


def test_get_volume_multiplier() -> None:
    name, vol, units = _get_volume("LAIT DEMI-ECREME 6X1L")
    assert vol == 6000.0
    assert units == 6
    assert "6X1L" not in name


def test_get_volume_none() -> None:
    _name, vol, units = _get_volume("SUCRE POUDRE 1KG")
    assert vol is None
    assert units is None


def test_normalize_strips_volume() -> None:
    assert "1L" not in normalize_for_matching("PUR JUS MULTIFRUITS U BIO 1L")
    assert "75CL" not in normalize_for_matching("VIN ROGUE 75CL")


# --- brand ---


def test_get_brand() -> None:
    assert get_brand("BRIOCHE TRESSEE PASQUIER") == "PASQUIER"
    assert get_brand("SPAGHETTI PANZANI 500G") == "PANZANI"
    assert get_brand("LAIT DEMI-ECREME LACTEL 1L") == "LACTEL"
    assert get_brand("BRIE PASTEURISE ROITELET") == "ROITELET"
    assert get_brand("OEUFS PA CAL.MIXTE U X12") == "U"
    assert get_brand("SUCRE POUDRE 1KG") is None
    assert get_brand("AUBERGINE") is None


def test_get_brand_u_standalone() -> None:
    """U should only match as a standalone word, not inside other words."""
    assert get_brand("SUCRE POUDRE") is None
    assert get_brand("AIL BLC U BIO FILET") == "U"


def test_get_brand_new_brands() -> None:
    """Newly added brands are detected."""
    assert get_brand("GLACE EXTREME VANILLE") == "EXTREME"
    assert get_brand("FIGURINE SCHLEICH DINOSAURE") == "SCHLEICH"
    assert get_brand("TABS LAVE VAISSELLE SUN") == "SUN"
    assert get_brand("SUZI-WAN SAUCE SOJA") == "SUZI-WAN"
    assert get_brand("FOL EPI FROMAGE TRANCHE") == "FOL EPI"
    assert get_brand("GALETTES SAINT MICHEL") == "SAINT MICHEL"


def test_get_brand_nana_no_ananas() -> None:
    r"""NANA brand must not match inside ANANAS (\\b prevents it)."""
    assert get_brand("SERVIETTES NANA ULTRA") == "NANA"
    assert get_brand("ANANAS ENTIER") is None


# --- quality label ---


def test_get_quality_label() -> None:
    assert get_quality_label("BEAUFORT AOP LAIT CRU") == "AOP"
    assert get_quality_label("COMTE AOP") == "AOP"
    assert get_quality_label("SAUCISSE SECHE IGP") == "IGP"
    assert get_quality_label("POULET LABEL ROUGE") == "Label Rouge"
    assert get_quality_label("OEUF.PA.MOYEN LR LOUE X10+5OFF") == "Label Rouge"
    assert get_quality_label("SUCRE POUDRE") is None


def test_get_quality_label_label_rouge_before_lr() -> None:
    """LABEL ROUGE should be detected even when LR also appears."""
    assert get_quality_label("POULET LABEL ROUGE LR") == "Label Rouge"


# --- packaging ---


def test_get_packaging() -> None:
    assert get_packaging("LAIT UHT ENTIER U BRIQUE 6X1L") == "BRIQUE"
    assert get_packaging("EAU MINERALE BOUTEILLE 1,5L") == "BOUTEILLE"
    assert get_packaging("SUCRE POUDRE 1KG") is None
    # Abbreviations BK/BL are NOT detected — they're ambiguous (BL = blanc in clothing).
    # Synonym expansion (BK→BRIQUE, BL→BOUTEILLE) handles them upstream.
    assert get_packaging("LAIT UHT 1/2 ECREM U BK 1L") is None
    assert get_packaging("MCH UNI MBLC BL/MA 21/23") is None


def test_normalize_strips_packaging_brique_bouteille() -> None:
    assert "BRIQUE" not in normalize_for_matching("LAIT UHT ENTIER U BRIQUE 6X1L")
    assert "BOUTEILLE" not in normalize_for_matching("EAU MINERALE BOUTEILLE 1,5L")


# --- affinage (cheese aging) ---


def test_get_affinage_months() -> None:
    assert get_affinage_months("BEAUFORT 5 MOIS AFFINAGE") == 5
    assert get_affinage_months("BEAUFORT 5 MOIS D'AFFINAGE") == 5
    assert get_affinage_months("BEAUFORT AFFINE 9 MOIS") == 9
    assert get_affinage_months("BEAUFORT AFFINÉ 9 MOIS") == 9
    assert get_affinage_months("COMTE AFFINAGE 12 MOIS") == 12
    assert get_affinage_months("MONT JURA 9MOIS AFFINAGE") == 9
    # Standalone N MOIS without affinage keyword → only detected in cheese mode
    assert get_affinage_months("COMTE 18 MOIS") is None
    assert get_affinage_months("COMTE 18 MOIS", cheese=True) == 18
    assert get_affinage_months("BLEDINE BISCUIT 6MOIS") is None
    assert get_affinage_months("BLEDINE BISCUIT 6MOIS", cheese=True) == 6
    assert get_affinage_months("SUCRE POUDRE") is None
    assert get_affinage_months("AUBERGINE") is None


def test_strip_affinage() -> None:
    assert strip_affinage("BEAUFORT 5 MOIS AFFINAGE") == "BEAUFORT"
    assert strip_affinage("BEAUFORT AFFINE 9 MOIS") == "BEAUFORT"
    assert strip_affinage("BEAUFORT AFFINÉ 9 MOIS") == "BEAUFORT"
    assert strip_affinage("COMTE AFFINAGE 12 MOIS") == "COMTE"
    # Standalone N MOIS only stripped in cheese mode
    assert strip_affinage("COMTE 18 MOIS") == "COMTE 18 MOIS"
    assert strip_affinage("COMTE 18 MOIS", cheese=True) == "COMTE"
    assert strip_affinage("BLEDINE BISCUIT 6MOIS") == "BLEDINE BISCUIT 6MOIS"
    assert strip_affinage("BLEDINE BISCUIT 6MOIS", cheese=True) == "BLEDINE BISCUIT"
    assert strip_affinage("SUCRE POUDRE") == "SUCRE POUDRE"


def test_normalize_strips_affinage() -> None:
    assert "MOIS" not in normalize_for_matching("BEAUFORT 5 MOIS AFFINAGE")
    assert "AFFINAGE" not in normalize_for_matching("BEAUFORT 5 MOIS AFFINAGE")
    assert "AFFINE" not in normalize_for_matching("BEAUFORT AFFINE 9 MOIS")
    assert normalize_for_matching("COMTE 18 MOIS") == "COMTE"


# --- production (fermier / laitier) ---


def test_get_production() -> None:
    assert get_production("REBLOCHON AOP FERMIER") == "fermier"
    assert get_production("REBLOCHON AOP LAITIER LC 27%MG") == "laitier"
    assert get_production("FOURME AMBERT FERMIER") == "fermier"
    assert get_production("REBLOCHON SAVOIE AOP LAIT CRU") is None
    assert get_production("SUCRE POUDRE") is None
    assert get_production("AUBERGINE") is None


def test_normalize_strips_production() -> None:
    assert "FERMIER" not in normalize_for_matching("REBLOCHON AOP FERMIER")
    assert "LAITIER" not in normalize_for_matching("REBLOCHON AOP LAITIER LC 27%MG")


# --- baby food normalization ---


def test_normalize_strips_baby_food_age() -> None:
    # Age stripped, but content after placeholder also stripped → just placeholder
    assert normalize_for_matching("BLEDINA CAR/RZ/JAMB 8M") == "BLEDINA CAR/RZ/JAMB"
    # "DES 12M" = "dès 12 mois" — DES prefix stripped with age
    assert normalize_for_matching("BLEDINA CROISSANCE DES 12M") == "BLEDINA CROISSANCE"
    # Does NOT strip MG (fat) — %MG is not a baby age suffix
    assert "%MG" in normalize_for_matching("FROMAGE 32%MG")


def test_normalize_groups_baby_food_by_type() -> None:
    # All PLAT BEBE products group together — recipe stripped from normalized name
    assert normalize_for_matching("BLEDICHEF RISOTTO SAUMON") == "PLAT BEBE"
    assert normalize_for_matching("BLEDINER LEGUMES RIZ") == "PLAT BEBE"
    assert normalize_for_matching("BLEDICHEF ASSIETTE PDT/CH FL") == "PLAT BEBE"
    assert normalize_for_matching("BLEDINA BOL CAR/RZ/JAMB 8M") == "BLEDINA PLAT BEBE"
    assert normalize_for_matching("BLEDINA POT LEGUMES 6M") == "BLEDINA PLAT BEBE"
    # CEREALES BEBE and LAIT BEBE also group
    assert normalize_for_matching("BLEDINE BISCUIT") == "CEREALES BEBE"
    assert normalize_for_matching("BLEDILAIT CROISSANCE DES 12M") == "LAIT BEBE"


def test_get_baby_recipe() -> None:
    # Sub-brands
    assert get_baby_recipe("BLEDICHEF ASSIETTE RISOTTO SAUMON 15M") == "RISOTTO SAUMON"
    assert get_baby_recipe("BLEDICHEF ASSIETTE PDT/CH FL") == "PDT/CH FL"
    assert get_baby_recipe("BLEDILAIT CROISSANCE DES 12M") == "CROISSANCE"
    assert get_baby_recipe("BLEDINE BISCUIT 6MOIS") == "BISCUIT 6MOIS"
    # Format words
    assert get_baby_recipe("BOLS LEG.OUBLIES 8M UTP BIO") == "LEG.OUBLIES"
    assert get_baby_recipe("BOL.H.VERT/PLET 6M UTPB") == "H.VERT/PLET"
    assert get_baby_recipe("BOLS SPAGHET/BOLO 8M UTP BIO") == "SPAGHET/BOLO"
    # BLEDINA and LRB stripped from recipe
    assert (
        get_baby_recipe("BLEDINA BOL TOMATE/PATES/JAMBON 12M") == "TOMATE/PATES/JAMBON"
    )
    assert get_baby_recipe("LRB POT CAROTTE/JAMBON 6M") == "CAROTTE/JAMBON"
    # Not baby food
    assert get_baby_recipe("FROMAGE COMTÉ 12 MOIS") is None
    assert get_baby_recipe("SAUCE TOMATE") is None


def test_get_baby_food_type() -> None:
    # Sub-brands
    assert get_baby_food_type("BLEDICHEF ASSIETTE RISOTTO 15M") == "PLAT BEBE"
    assert get_baby_food_type("BLEDINER BOL AUB/CAR 12M") == "PLAT BEBE"
    assert get_baby_food_type("BLEDINE CER INST BLE/CACAO") == "CEREALES BEBE"
    assert get_baby_food_type("BLEDILAIT CROISSANCE 12M") == "LAIT BEBE"
    # Format words
    assert get_baby_food_type("BOL TOMATE/PATES 8M") == "PLAT BEBE"
    assert get_baby_food_type("POT CAROTTE/JAMBON 6M") == "PLAT BEBE"
    # Dot prefix
    assert get_baby_food_type("BOL.H.VERT/PLET 6M") == "PLAT BEBE"
    # Not baby food
    assert get_baby_food_type("FROMAGE COMTÉ") is None
    assert get_baby_food_type("SAUCE TOMATE") is None


# --- parse pipeline (end-to-end) ---


def test_parse_reblochon_readme_example() -> None:  # pylint: disable=too-many-locals
    """The README example: REBL.SAVE.AOP.LC BIO BQTX12 450G 32%MG."""
    synonyms = {
        "REBL": "REBLOCHON",
        "SAVE": "SAVOIE",
        "FRM": "FERMIER",
        "LC": "LAIT CRU",
        "BQT": "BARQUETTE",
    }
    (
        name,
        grams,
        units,
        fat_pct,
        bio,
        milk_treatment,
        volume_ml,
        brand,
        label,
        packaging,
        origin,
        affinage_months,
        production,
        baby_months,
        baby_recipe,
    ) = _parse_name_attributes("REBL.SAVE.AOP.FRM.LC BIO BQT.X12 450G 32%MG", synonyms)
    assert name == "REBLOCHON"
    assert grams == 450.0
    assert units == 12
    assert fat_pct == 32.0
    assert bio is True
    assert milk_treatment == "cru"
    assert production == "fermier"
    assert label == "AOP"
    assert packaging == "BARQUETTE"
    assert origin == "SAVOIE"
    assert volume_ml is None
    assert brand is None
    assert affinage_months is None
    assert baby_months is None
    assert baby_recipe is None
