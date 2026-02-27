# Superslurp

SuperSlurp is a Utility for Parsing & Extracting Receipts via Savage Layers of
Unreadable Regex & Processing

It parses [Super U](https://fr.wikipedia.org/wiki/Coop%C3%A9rative_U) PDF receipts. Can
generate a JSON from a receipt, or a JSON aggregate from multiple receipts for
consumption from another tools, or generate an HTML report directly.

The parser understands the intricacies of French cuisine, for example it knows a
Reblochon _fermier_ from a _laitier_, as per the French government's
[official AOP specification](https://agriculture.gouv.fr/le-reblochon-aop-le-fromage-onctueux-de-savoie).

Useful when you want to display cheese consumption intensity in €/day inside Grafana, or
detect sneaky shrinkflation via fat-content drift on your favorite _fromage blanc_.

## Quick start

### Install

```bash
pip install superslurp
```

### Run

Generate a report from directory of PDF receipts:

```bash
superu-report receipts/*.pdf -o report.html
```

Then open `report.html`

### Synonyms

Receipts are full of abbreviations (`REBL.SAV.` for `REBLOCHON SAVOIE`). ~200 built-in
synonyms handle the common ones. To add your own, create a JSON file mapping
abbreviations to full names:

```json
{
  "FAR.FROM": "FARINE DE FROMENT",
  "FROM": "FROMAGE"
}
```

```bash
superu-report receipts/*.pdf --synonyms extra.json -o report.html
```

**Order matters** — put multi-word abbreviations before their single-word parts. Here
`FAR.FROM` comes before `FROM`, so a receipt line `FAR.FROM` correctly becomes
`FARINE DE FROMENT`. If `FROM` came first, it would be replaced by `FROMAGE` and you'd
end up with flour cheese instead of wheat flour.

Use `--no-default-synonyms` to disable the built-in set entirely.

## Parse example

`REBL.SAV.AOP.FRM.LC BIO BQT.X12 450G 32%MG  8,61 €  11` is parsed as:

```jsonc
{
  "raw": "REBL.SAV.AOP.FRM.LC BIO BQT.X12 450G 32%MG  8,61 €  11", // debug=True
  "name": "REBLOCHON",
  "price": 8.61,
  "bought": 1,
  "units": 12,
  "grams": 450.0,
  "fat_pct": 32.0,
  "properties": {
    "bio": true,
    "milk_treatment": "cru",
    "production": "fermier",
    "label": "AOP",
    "packaging": "BARQUETTE",
    "origin": "SAVOIE",
  },
  "...": "...",
}
```

## Aggregate output

Products are grouped under a canonical name using fuzzy matching (difflib, threshold
0.90):

```jsonc
{
  "stores": [{ "id": "123_456", "store_name": "...", "location": "..." }],
  "sessions": [{ "id": 1, "date": "2025-01-15 10:00:00", "store_id": "123_456" }],
  "session_totals": [{ "session_id": 1, "date": "2025-01-15", "total": 42.5 }],
  "session_category_totals": ["..."],
  "category_rolling_averages": ["..."],
  "products": [
    {
      "canonical_name": "OEUFS",
      "observations": [
        {
          "original_name": "OEUFS PLEIN AIR MOYEN",
          "session_id": 1,
          "price": 3.15,
          "unit_count": 12,
          "price_per_unit": 0.2625,
          "bio": true,
          "...": "...",
        },
      ],
    },
  ],
}
```

## Developer guide

### Pipeline steps

`superu-report` runs parse → aggregate → HTML in one shot. During development you can
run each step individually to avoid re-doing everything when iterating on a single
stage:

```bash
# 1. Parse a single receipt PDF → JSON
superu-receipt-parser receipt.pdf -o receipt.json

# 2. Aggregate multiple parsed JSONs
superu-aggregate-parsed-receipt receipts/ -o aggregate.json

# 3. Generate report from an existing aggregate
superu-report-from-aggregate aggregate.json -o report.html

# Or pipe step 2 → 3
superu-aggregate-parsed-receipt receipts/ | superu-report-from-aggregate - -o report.html
```

### Python API

| Function                                             | Description                                   |
| ---------------------------------------------------- | --------------------------------------------- |
| `parse_superu_receipt(filename, *, synonyms, debug)` | Parse a PDF receipt → `Receipt` dict          |
| `compare_receipt_files(paths, *, threshold)`         | Aggregate parsed JSONs → `CompareResult` dict |
| `generate_report(filenames, *, synonyms)`            | Parse PDFs + aggregate + render HTML string   |
