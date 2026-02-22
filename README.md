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

```json
{
  "items": {
    "EPICERIE": [
      {
        "name": "POELLE JARDINIERE DAUCY",
        "price": 2.59,
        "quantity": 1,
        "units": null,
        "grams": 580.0,
        "tr": false,
        "way_of_paying": "11",
        "discount": null
      }
    ]
  }
}
```

Pass `debug=True` to include the original receipt line on each item:

```python
result = parse_superu_receipt("Ticket de caisse_01032022-165652.pdf", debug=True)
```

```json
{
  "items": {
    "EPICERIE": [
      {
        "raw": "POELLE JARDINIERE DAUCY 580G                2,59 €  11",
        "name": "POELLE JARDINIERE DAUCY",
        "price": 2.59,
        "quantity": 1,
        "units": null,
        "grams": 580.0,
        "tr": false,
        "way_of_paying": "11",
        "discount": null
      }
    ]
  }
}
```

Pass a `synonyms` dict to expand receipt abbreviations in item names:

```python
synonyms = {"TABS": "TABLETTES", "VAISS": "VAISSELLE"}
result = parse_superu_receipt("receipt.pdf", synonyms=synonyms)
# "TABS LAVE VAISS.STANDARD U" → "TABLETTES LAVE VAISSELLE STANDARD U"
```

CLI:

```bash
superu-receipt-parser receipt.pdf --synonyms synonyms.json
```

## 2. Aggregate receipts

Compare items across multiple parsed receipts with fuzzy matching. Products are grouped
under a canonical name, each observation tracking price, grams, units, and discount.

```python
from superslurp.compare.aggregate import compare_receipt_files

result = compare_receipt_files(
    paths=[Path("receipt1.json"), Path("receipt2.json")],
    threshold=0.90,       # fuzzy matching threshold (default: 0.90)
    synonyms=synonyms,    # optional, same format as parse
)
```

The result contains stores, sessions, per-session totals, a rolling weekly average, and
products with their observations:

```json
{
  "stores": [{ "id": "123_456", "store_name": "...", "location": "..." }],
  "sessions": [{ "id": 1, "date": "2025-01-15 10:00:00", "store_id": "123_456" }],
  "session_totals": [{ "session_id": 1, "date": "2025-01-15", "total": 42.5 }],
  "rolling_average": [{ "date": "2025-01-13", "value": 85.3 }],
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
          "unit_count": 12,
          "price_per_unit": 0.2625
        }
      ]
    }
  ]
}
```

CLI:

```bash
superu-aggregate-parsed-receipt receipts/ --synonyms synonyms.json --output aggregate.json
```

## 3. Generate an HTML report

Generate a self-contained HTML dashboard from the aggregate JSON. Includes a session
totals chart with rolling average, a per-product price evolution chart, and sortable
detail tables.

```python
from superslurp.compare.html_report import generate_html

html = generate_html(aggregate_result)
Path("report.html").write_text(html)
```

CLI:

```bash
superu-report-from-aggregate aggregate.json --output report.html
```

Or pipe directly from aggregate:

```bash
superu-aggregate-parsed-receipt receipts/ --synonyms synonyms.json \
  | superu-report-from-aggregate - --output report.html
```

## Synonyms

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
