from __future__ import annotations

__all__ = [
    "compare_receipt_dicts",
    "compare_receipt_files",
    "generate_report",
    "main",
    "parse_superu_receipt",
]

from superslurp.__main__ import generate_report, main, parse_superu_receipt
from superslurp.compare.aggregate import compare_receipt_dicts, compare_receipt_files
