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
from superslurp.parse.common import CompiledSynonyms, resolve_synonyms
from superslurp.serialize.json_dump import make_json_serializable

_DEFAULT_SYNONYMS_PATH = Path(__file__).resolve().parent / "synonyms.json"


def _load_synonyms(path: Path) -> dict[str, str]:
    """Load a synonyms JSON file and uppercase all keys and values."""
    with open(path, encoding="utf8") as f:
        raw = json.load(f)
    return {k.upper(): v.upper() for k, v in raw.items()}


def _load_default_synonyms() -> dict[str, str]:
    """Load the built-in synonyms bundled with the package."""
    return _load_synonyms(_DEFAULT_SYNONYMS_PATH)


def parse_superu_receipt(
    filename: str | Path,
    *,
    debug: bool = False,
    synonyms: dict[str, str] | None = None,
    compiled_synonyms: CompiledSynonyms | None = None,
) -> dict[str, Any]:
    """Parse a SuperU receipt PDF into a dict.

    When debug=True, each item includes a 'raw' field with the original
    receipt line before parsing.

    When synonyms is provided (an ordered dict mapping patterns to
    replacements), item names are expanded before output. Iteration order
    matters: put multi-word patterns before single-word fallbacks.

    When *compiled_synonyms* is provided, synonym compilation is skipped
    (use :func:`resolve_synonyms` to pre-compile once for many receipts).
    """
    text = convert_to_text(filename)
    logging.debug("Extracted text, parsing receipt...")
    receipt = parse_text(text, synonyms=synonyms, compiled_synonyms=compiled_synonyms)
    logging.debug("Parsing done, checking consistency...")
    check_consistency(receipt)
    logging.debug("Rendering json result...")
    return make_json_serializable(receipt, include_raw=debug)


def generate_report(
    filenames: list[str | Path],
    *,
    synonyms: dict[str, str] | None = None,
    threshold: float = 0.90,
) -> str:
    """Parse multiple SuperU receipt PDFs and generate an HTML report.

    Returns a self-contained HTML string with an interactive price dashboard.
    """
    compiled_syn = resolve_synonyms(synonyms)
    receipts = [
        parse_superu_receipt(f, compiled_synonyms=compiled_syn) for f in filenames
    ]
    aggregate = compare_receipt_dicts(receipts, threshold=threshold)
    return generate_html(aggregate)


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse a receipt.")
    parser.add_argument("filename", type=str, help="The name of the file to process")
    add_synonyms_arg(parser)
    parsed_args = parser.parse_args(args)
    print(f"Processing file: {parsed_args.filename}")
    synonyms: dict[str, str] | None = None
    if not parsed_args.no_default_synonyms:
        synonyms = _load_default_synonyms()
    if parsed_args.synonyms:
        if synonyms is None:
            synonyms = {}
        synonyms.update(_load_synonyms(parsed_args.synonyms))
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
    synonyms: dict[str, str] | None = None
    if not parsed_args.no_default_synonyms:
        synonyms = _load_default_synonyms()
    if parsed_args.synonyms:
        if synonyms is None:
            synonyms = {}
        synonyms.update(_load_synonyms(parsed_args.synonyms))
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
