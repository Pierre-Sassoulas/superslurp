from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from superslurp.check import check_consistency
from superslurp.extract import convert_to_text
from superslurp.parse import parse_text
from superslurp.serialize.json_dump import make_json_serializable


def parse_superu_receipt(
    filename: str | Path, *, debug: bool = False
) -> dict[str, Any]:
    """Parse a SuperU receipt PDF into a dict.

    When debug=True, each item includes a 'raw' field with the original
    receipt line before parsing.
    """
    text = convert_to_text(filename)
    logging.debug("Extracted text, parsing receipt...")
    receipt = parse_text(text)
    logging.debug("Parsing done, checking consistency...")
    check_consistency(receipt)
    logging.debug("Rendering json result...")
    return make_json_serializable(receipt, include_raw=debug)


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse a receipt.")
    parser.add_argument("filename", type=str, help="The name of the file to process")
    parsed_args = parser.parse_args(args)
    print(f"Processing file: {parsed_args.filename}")
    parsed_content = parse_superu_receipt(parsed_args.filename)
    print(f"Result:\n{json.dumps(parsed_content, indent=4, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
