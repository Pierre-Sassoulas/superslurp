from __future__ import annotations

from superslurp.superslurp_typing import Category, Item


def repr_items(items: dict[Category, list[Item]]) -> str:
    result = ""
    for category, _items in items.items():
        print(category, items)
        str_items = [str(s) for s in _items]
        result += f"- {category}:\n\t{'\n\t'.join(str_items)}\n"
    return result
