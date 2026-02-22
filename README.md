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
