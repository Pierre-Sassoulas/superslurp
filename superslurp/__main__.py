from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from superslurp.check_consistency import check_consistency
from superslurp.parser import Receipt, parse_text


def make_json_serializable(
    receipt: Receipt,
) -> dict[str, dict[str, Any]]:
    serializable_result: dict[str, Any] = {"items": {}}
    for key, value in receipt.items():
        if key == "items":
            for category, items in receipt["items"].items():
                serializable_result["items"][category.value] = items
            continue
        serializable_result[key] = value

    return serializable_result


def parse_superu_receipt(filename: str | Path) -> str:
    text = extract_text(filename)
    receipt = parse_text(text)
    check_consistency(receipt)
    return json.dumps(make_json_serializable(receipt), indent=4)


def extract_text(filename: str | Path) -> str:
    reader = PdfReader(filename)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse a receipt.")
    parser.add_argument("filename", type=str, help="The name of the file to process")
    parsed_args = parser.parse_args(args)
    print(f"Processing file: {parsed_args.filename}")
    parsed_content = parse_superu_receipt(parsed_args.filename)
    print(f"Result:\n{parsed_content}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
