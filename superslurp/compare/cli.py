from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from superslurp._cli_args import add_output_arg, add_synonyms_arg, add_threshold_arg
from superslurp.compare.aggregate import compare_receipt_files
from superslurp.compare.html_report import generate_html


def main_aggregate() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate parsed receipt JSONs into a comparison JSON."
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Directory containing receipt JSON files.",
    )
    add_threshold_arg(parser)
    add_output_arg(parser)
    add_synonyms_arg(parser)
    args = parser.parse_args()

    directory: Path = args.directory
    if not directory.is_dir():
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    paths = sorted(directory.glob("*.json"))
    if not paths:
        print(f"Error: no JSON files found in {directory}", file=sys.stderr)
        sys.exit(1)

    synonyms: dict[str, str] | None = None
    if args.synonyms:
        with open(args.synonyms, encoding="utf8") as f:
            raw = json.load(f)
        synonyms = {k.upper(): v.upper() for k, v in raw.items()}

    result = compare_receipt_files(paths, threshold=args.threshold, synonyms=synonyms)
    output_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        args.output.write_text(output_json, encoding="utf8")
    else:
        print(output_json)


def main_report() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an HTML dashboard from an aggregate JSON."
    )
    parser.add_argument(
        "aggregate",
        help="Aggregate JSON file path, or '-' for stdin.",
    )
    add_output_arg(parser)
    args = parser.parse_args()

    if args.aggregate == "-":
        data = json.load(sys.stdin)
    else:
        data = json.loads(Path(args.aggregate).read_text(encoding="utf8"))

    html = generate_html(data)

    if args.output:
        args.output.write_text(html, encoding="utf8")
    else:
        print(html)
