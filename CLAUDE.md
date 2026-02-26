# Superslurp — Claude Code Guide

French grocery receipt parser & price tracker for Super U stores. Parses PDF receipts,
extracts items with structured attributes, compares prices across sessions, generates
HTML reports.

## Quick Reference

```bash
pytest tests/                        # Run all tests (258+)
pytest tests/test_compare.py         # Unit tests (normalization, matching, aggregation)
pytest tests/test_parse_text.py      # Fixture-based parse tests (auto-regenerates JSONs)
```

Commit style: `[feat]`, `[fix]`, `[refactor]` prefix.

## Architecture

```
PDF → extract (pypdf) → text → parse (v1/v2) → Receipt JSON → compare → Aggregate → HTML Report
```

### Key Modules

| Module                               | Purpose                                                                                        |
| ------------------------------------ | ---------------------------------------------------------------------------------------------- |
| `superslurp/__main__.py`             | CLI entry points: `superu-receipt-parser`, `superu-report`                                     |
| `superslurp/parse/v1/parse_items.py` | Core parser — `_parse_name_attributes()` extracts all item attributes                          |
| `superslurp/parse/v2/parse_items.py` | V2 format parser (imports `_parse_name_attributes` from v1)                                    |
| `superslurp/compare/normalize.py`    | Name normalization, synonym expansion, property extraction (bio, brand, milk, baby food, etc.) |
| `superslurp/compare/matcher.py`      | `FuzzyMatcher` — groups similar names via token index + SequenceMatcher                        |
| `superslurp/compare/aggregate.py`    | Builds observations, sessions, rolling averages across receipts                                |
| `superslurp/compare/html_report.py`  | Jinja2 HTML dashboard with Chart.js                                                            |
| `superslurp/superslurp_typing.py`    | TypedDict models: `Item`, `Properties`, `Category`, `Receipt`                                  |

### Parse Pipeline (`_parse_name_attributes`)

Order matters — each step operates on the name after previous steps stripped their
content:

1. Synonym expansion (dot-aware, multi-word first)
2. Grams extraction (`350G`, `1.5KG`)
3. Volume extraction (`1L`, `75CL`, `250ML`)
4. Unit count (`X12`, `BTEX6`)
5. Fat % (`33%MG`) + infer from milk type (entier→3.6%, 1/2 écrémé→1.5%)
6. Property extraction: bio, milk_treatment, production, brand, label, packaging,
   origin, affinage, baby_months, baby_recipe
7. Baby food name replacement → `PLAT BEBE` / `CEREALES BEBE` / `LAIT BEBE`

Post-parse steps (category-aware): `extract_bare_fat_pct`, `extract_packaging_abbrev`,
`extract_standalone_affinage_months`, `expand_context_synonyms`.

### Normalization (`normalize_for_matching`)

Strips: accents, colors, packaging, origin, brand, BIO, milk treatment, volumes, units,
baby ages. Protects compounds (FROMAGE BLANC, VIN BLANC). Replaces baby keywords with
type placeholders, then truncates after placeholder for grouping.

### Fuzzy Matching

`FuzzyMatcher` uses token inverted index + `SequenceMatcher` (threshold 0.90). Two-level
cache: raw name → canonical (skips normalization), normalized → canonical. First match
wins (insertion order).

## Data Model

**Item** fields: `raw`, `raw_name`, `name`, `price`, `bought`, `units`, `grams`,
`volume_ml`, `fat_pct`, `tr`, `way_of_paying`, `discount`, `properties`.

**Properties** (all optional): `bio`, `milk_treatment`, `production`, `brand`, `label`,
`packaging`, `origin`, `affinage_months`, `baby_months`, `baby_recipe`.

**Baby food types**: Baby food items get `name` set to normalized type (`PLAT BEBE`,
`CEREALES BEBE`, `LAIT BEBE`) with recipe details in `baby_recipe`. Guard: requires
`baby_months` or a BLEDI-keyword to avoid false positives on generic `BOL`/`POT` words.

## Tests & Fixtures

- **`tests/fixtures/`** — Git submodule. Contains `.pdf` receipts + `.pdf.json` expected
  outputs, `synonyms.json`, `.compare_result.json`.
- **Auto-regeneration**: `test_parse_text.py` overwrites fixture JSONs when parsing
  output changes. After any parsing change, run tests twice (first pass regenerates,
  second pass verifies), then check `cd tests/fixtures && git diff` — the submodule
  needs its own commit/push.
- **`sample_expected_parsed_items.json`** — Hand-maintained fixture for
  `test_parse_items` (not auto-regenerated).

## Key Data Structures

- `_KNOWN_BRANDS` (frozenset in normalize.py) — Recognized brand names
- `_BABY_FOOD_REPLACEMENTS` (dict in normalize.py) — Baby keyword → placeholder mapping
- `_STRIP_WORDS` (frozenset in normalize.py) — Words stripped during normalization
- `_PROTECTED_COMPOUNDS` (dict in normalize.py) — Compounds that must not be split
- `synonyms.json` — Abbreviation → expansion dictionary (order matters: multi-word
  before single-word)

## Tooling

- Python 3.12+, setuptools with setuptools_scm
- Pre-commit hooks: ruff (format+lint), mypy (strict), pylint, codespell, prettier
- Line length: 88 (format), 120 (lint)
- Required: `from __future__ import annotations` in all files
