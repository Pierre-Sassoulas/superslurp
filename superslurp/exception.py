from __future__ import annotations

from superslurp.superslurp_typing import Item, Receipt


class ConsistencyError(Exception):
    def __init__(self, receipt: Receipt, msg: str):
        super().__init__(
            f"Something must be wrong with the parsing because {msg}."
            # Might want to comment next line some of the time:
            # f"\n\n{json_dump_receipt(receipt)}"
            f"\n{self.show_items(receipt)}"
        )

    @staticmethod
    def show_items(receipt: Receipt) -> str:
        result = ""
        s = 0.0
        for category, items in receipt["items"].items():
            result += f"{category} ({len(items)}):\n"
            for item in items:
                p = item["price"]
                q = item["quantity"]
                s += p * q
                result += f"{item['name']}: {p} * {q} ({s})\n"
        return result


class UndetectedAttributeError(ConsistencyError):
    def __init__(self, receipt: Receipt, item: Item, attribute: str):
        super().__init__(receipt, f"{attribute!r} in {item} is not set")


class UnexpectedSumOfParsedItems(ConsistencyError):
    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
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
