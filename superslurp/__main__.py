from __future__ import annotations

import argparse
import json
import logging
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
    path = Path(filename)
    cached_text_file = Path(path.parent / f".{path.name}.txt")
    if not cached_text_file.exists():
        logging.debug(f"Converting {path!r} to text...")
        text = extract_text(filename)
        with open(cached_text_file, "w", encoding="utf8") as f:
            f.write(text)
    else:
        logging.debug("Reading text from cache without converting from pdf...")
        with open(cached_text_file, encoding="utf8") as f:
            text = f.read()
    logging.debug("Extracted text, parsing receipt...")
    receipt = parse_text(text)
    logging.debug("Parsing done, checking consistency...")
    check_consistency(receipt)
    logging.debug("Rendering json result...")
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
