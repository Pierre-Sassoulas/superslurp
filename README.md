# superslurp : Super, Sublime, Light, and Unprecedented Receipt Parser

Parser for [SuperU](https://fr.wikipedia.org/wiki/Coop%C3%A9rative_U) receipts. Take the
PDF receipt sent by mail as input and return a json.

Useful when you want to display the instantaneous cheese consumption intensity of your
home in € inside grafana.

## 1. Parse a receipt

```python
from superslurp import parse_superu_receipt

result = parse_superu_receipt("Ticket de caisse_01032022-165652.pdf")
```

The receipt line `QUENELLE NATURE U X6 240G  /  3 x 0,85 €  2,55 €  11` is parsed as:

```json
{
  "name": "QUENELLE NATURE U",
  "price": 0.85,
  "bought": 3,
  "units": 6,
  "grams": 240.0,
  "volume_ml": null,
  "tr": false,
  "way_of_paying": "11",
  "discount": null,
  "properties": {}
}
```

Pass `debug=True` to include the original receipt line (`"raw"` field):

```python
from superslurp import parse_superu_receipt

result = parse_superu_receipt("receipt.pdf", debug=True)
```

Pass a `synonyms` dict to expand receipt abbreviations in item names:

```python
from superslurp import parse_superu_receipt

synonyms = {"TABS": "TABLETTES", "VAISS": "VAISSELLE"}
result = parse_superu_receipt("receipt.pdf", synonyms=synonyms)
# "TABS LAVE VAISS.STANDARD U" → "TABLETTES LAVE VAISSELLE STANDARD U"
```

CLI:

```bash
superu-receipt-parser receipt.pdf --synonyms synonyms.json
```

## 2. Aggregate receipts

Compare items across multiple parsed receipts. Products are grouped under a canonical
name using fuzzy matching (via difflib).

```python
from pathlib import Path

from superslurp.compare.aggregate import compare_receipt_files

result = compare_receipt_files(
    paths=[Path("receipt1.json"), Path("receipt2.json")],
    threshold=0.90,       # difflib threshold (default: 0.90)
)
```

Synonyms are applied at parse time (step 1), so the JSON files fed to
`compare_receipt_files` already contain expanded names.

The result contains stores, sessions, per-session totals, a rolling weekly average, and
products with their observations:

```json
{
  "stores": [{ "id": "123_456", "store_name": "...", "location": "..." }],
  "sessions": [{ "id": 1, "date": "2025-01-15 10:00:00", "store_id": "123_456" }],
  "session_totals": [{ "session_id": 1, "date": "2025-01-15", "total": 42.5 }],
  "rolling_average": [{ "date": "2025-01-13", "value": 85.3 }, "..."],
  "products": [
    {
      "canonical_name": "OEUFS",
      "observations": [
        {
          "original_name": "OEUFS PLEIN AIR MOYEN",
          "session_id": 1,
          "price": 3.15,
          "quantity": 1,
          "grams": null,
          "discount": null,
          "price_per_kg": null,
          "volume_ml": null,
          "price_per_liter": null,
          "unit_count": 12,
          "price_per_unit": 0.2625,
          "bio": true
        }
      ]
    }
  ]
}
```

CLI:

```bash
superu-aggregate-parsed-receipt receipts/ --output aggregate.json
```

## 3. Generate an HTML report

### From PDFs directly

Parse receipt PDFs and generate a self-contained HTML dashboard in one step:

```python
from superslurp import generate_report

html = generate_report(
    ["receipt1.pdf", "receipt2.pdf", "receipt3.pdf"],
    synonyms=synonyms,    # optional
    threshold=0.90,       # fuzzy matching threshold (default: 0.90)
)
Path("report.html").write_text(html)
```

CLI:

```bash
superu-report receipts/*.pdf --synonyms synonyms.json --output report.html
```

### From an existing aggregate JSON

If you already have an aggregate JSON (from step 2):

```python
from superslurp.compare.html_report import generate_html

html = generate_html(aggregate_result)
Path("report.html").write_text(html)
```

```bash
superu-report-from-aggregate aggregate.json --output report.html
```

Or pipe directly from aggregate:

```bash
superu-aggregate-parsed-receipt receipts/ \
  | superu-report-from-aggregate - --output report.html
```

## Synonyms

Synonyms are applied during **parsing** (step 1) — the aggregate step (step 2) only does
fuzzy matching on already-expanded names.

Synonyms is an ordered `dict[str, str]`. Entries are applied sequentially with
word-boundary matching — **insertion order matters**. Earlier entries are replaced
first, so later entries won't match words already consumed.

Dots in both names and keys are normalized to spaces before matching, so `"FROM.BLC"`
matches `FROM.BLC` on the receipt.

```python
synonyms = {
    "FROM.BLC": "FROMAGE BLANC",          # applied 1st: consumes FROM and BLC
    "CHOCO PATIS": "CHOCOLAT PATISSIER",  # applied 2nd: consumes CHOCO and PATIS
    "CHOCO": "CHOCOLAT",                  # applied 3rd: only if CHOCO still present
    "FROM": "FROMAGE",                    # applied 4th: only if FROM still present
    "PATIS": "PATISSERIE",               # applied 5th: only if PATIS still present
}
# "FROM.BLC NAT"         → "FROMAGE BLANC NAT"            (FROM.BLC consumed by 1st)
# "FROM.RAPE"            → "FROMAGE RAPE"                 (FROM consumed by 4th)
# "CHOCO.PATIS.NOIR 52%" → "CHOCOLAT PATISSIER NOIR 52%"  (CHOCO PATIS consumed by 2nd)
# "CHOCO.NOIR"           → "CHOCOLAT NOIR"                (CHOCO consumed by 3rd)
```

The JSON file is a standard object (key order is preserved since Python 3.7):

```json
{
  "FROM.BLC": "FROMAGE BLANC",
  "CHOCO PATIS": "CHOCOLAT PATISSIER",
  "CHOCO": "CHOCOLAT",
  "FROM": "FROMAGE",
  "PATIS": "PATISSERIE"
}
```
