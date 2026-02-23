from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from superslurp._cli_args import add_output_arg, add_synonyms_arg, add_threshold_arg
from superslurp.check import check_consistency
from superslurp.compare.aggregate import compare_receipt_dicts
from superslurp.compare.html_report import generate_html
from superslurp.extract import convert_to_text
from superslurp.parse import parse_text
from superslurp.serialize.json_dump import make_json_serializable


def _load_synonyms(path: Path) -> dict[str, str]:
    """Load a synonyms JSON file and uppercase all keys and values."""
    with open(path, encoding="utf8") as f:
        raw = json.load(f)
    return {k.upper(): v.upper() for k, v in raw.items()}


def parse_superu_receipt(
    filename: str | Path,
    *,
    debug: bool = False,
    synonyms: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Parse a SuperU receipt PDF into a dict.

    When debug=True, each item includes a 'raw' field with the original
    receipt line before parsing.

    When synonyms is provided (an ordered dict mapping patterns to
    replacements), item names are expanded before output. Iteration order
    matters: put multi-word patterns before single-word fallbacks.
    """
    text = convert_to_text(filename)
    logging.debug("Extracted text, parsing receipt...")
    receipt = parse_text(text)
    logging.debug("Parsing done, checking consistency...")
    check_consistency(receipt)
    logging.debug("Rendering json result...")
    return make_json_serializable(receipt, include_raw=debug, synonyms=synonyms)


def generate_report(
    filenames: list[str | Path],
    *,
    synonyms: dict[str, str] | None = None,
    threshold: float = 0.90,
) -> str:
    """Parse multiple SuperU receipt PDFs and generate an HTML report.

    Returns a self-contained HTML string with an interactive price dashboard.
    """
    receipts = [parse_superu_receipt(f, synonyms=synonyms) for f in filenames]
    aggregate = compare_receipt_dicts(receipts, threshold=threshold, synonyms=synonyms)
    return generate_html(aggregate)


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse a receipt.")
    parser.add_argument("filename", type=str, help="The name of the file to process")
    add_synonyms_arg(parser)
    parsed_args = parser.parse_args(args)
    print(f"Processing file: {parsed_args.filename}")
    synonyms = _load_synonyms(parsed_args.synonyms) if parsed_args.synonyms else None
    parsed_content = parse_superu_receipt(parsed_args.filename, synonyms=synonyms)
    print(f"Result:\n{json.dumps(parsed_content, indent=4, ensure_ascii=False)}")
    return 0


def main_report(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse receipt PDFs and generate an HTML report."
    )
    parser.add_argument(
        "filenames", nargs="+", type=Path, help="Receipt PDF files to process"
    )
    add_synonyms_arg(parser)
    add_threshold_arg(parser)
    add_output_arg(parser)
    parsed_args = parser.parse_args(args)
    synonyms = _load_synonyms(parsed_args.synonyms) if parsed_args.synonyms else None
    html = generate_report(
        parsed_args.filenames, synonyms=synonyms, threshold=parsed_args.threshold
    )
    if parsed_args.output:
        parsed_args.output.write_text(html, encoding="utf8")
    else:
        print(html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
