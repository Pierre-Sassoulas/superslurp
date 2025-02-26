from __future__ import annotations

from superslurp.serialize import json_dump_receipt
from superslurp.superslurp_typing import Item, Receipt


class ConsistencyError(Exception):
    def __init__(self, receipt: Receipt, msg: str):
        super().__init__(
            f"Something must be wrong with the parsing because {msg}."
            # Might want to comment next line some of the time:
            f"\n\n{json_dump_receipt(receipt)}"
        )


class UndetectedAttributeError(ConsistencyError):
    def __init__(self, receipt: Receipt, item: Item, attribute: str):
        super().__init__(receipt, f"{attribute!r} in {item} is not set")


class UnexpectedSumOfParsedItems(ConsistencyError):
    def __init__(
        self,
        receipt: Receipt,
        total: str,
        description: str,
        expected_value: float,
        actual_value: float,
    ):
        super().__init__(
            receipt,
            f"{description} does not match the {total!r} attribute"
            f" ({expected_value} != {actual_value}).",
        )
