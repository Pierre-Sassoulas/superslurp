# superslurp : Super, Sublime, Light, and Unprecedented Receipt Parser

Parser for [SuperU](https://fr.wikipedia.org/wiki/Coop%C3%A9rative_U) receipts. Take the
PDF receipt sent by mail as input and return a json.

Useful when you want to display the instantaneous cheese consumption intensity of your
home in € inside grafana.

## Usage

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

From the CLI with a JSON file:

```bash
superslurp receipt.pdf --synonyms synonyms.json
```

### Synonym ordering

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
