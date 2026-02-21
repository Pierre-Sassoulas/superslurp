from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from superslurp.compare.aggregate import compare_receipt_files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare product prices across SuperU receipts."
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Directory containing receipt JSON files.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.90,
        help="Fuzzy matching threshold (default: 0.90).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path. Prints to stdout if not specified.",
    )
    args = parser.parse_args()

    directory: Path = args.directory
    if not directory.is_dir():
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    paths = sorted(directory.glob("*.json"))
    if not paths:
        print(f"Error: no JSON files found in {directory}", file=sys.stderr)
        sys.exit(1)

    result = compare_receipt_files(paths, threshold=args.threshold)
    output_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        args.output.write_text(output_json, encoding="utf8")
    else:
        print(output_json)
