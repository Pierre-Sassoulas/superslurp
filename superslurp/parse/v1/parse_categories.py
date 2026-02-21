from __future__ import annotations

import logging
import re
from collections.abc import Generator

from superslurp.superslurp_typing import Category

category_pattern = re.compile(
    r">>>>(?P<category>.*)\n(?P<items>(?:(?!>>>>|====)[\S\s])*)"
)
single_undefined_category_pattern = re.compile(
    r"Ticket  \n[\w \/:]+[\n ]+(?P<items>(?:(?!==)[\S\s])*\n)[\n =]+"
)


def iter_categories_and_items(text: str) -> Generator[tuple[Category, str]]:
    logging.debug(f"Parsing with {category_pattern}:\n<\n{text}\n>")
    if not (category_matches := list(category_pattern.finditer(text))):
        if (
            items_without_category := single_undefined_category_pattern.search(text)
        ) is not None:
            logging.debug(
                f"Category could not be found, will continue parsing using {Category.UNDEFINED}."
            )
            yield Category.UNDEFINED, items_without_category.group("items")
            return
        err_msg = f"Using {single_undefined_category_pattern}, couldn't find any category in:\n<\n{text}\n>\n"
        print(err_msg)
        raise AssertionError(err_msg)
    for match in category_matches:
        category = Category(match.group("category").strip())
        items_info = match.group("items")
        yield category, items_info
