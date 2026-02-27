from __future__ import annotations

import argparse
from pathlib import Path


def add_synonyms_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --synonyms and --no-default-synonyms arguments to an argparse parser."""
    parser.add_argument(
        "--synonyms",
        type=Path,
        default=None,
        help="JSON file with extra abbreviation mappings (merged on top of built-in defaults).",
    )
    parser.add_argument(
        "--no-default-synonyms",
        action="store_true",
        default=False,
        help="Disable built-in synonyms. Only use synonyms from --synonyms if provided.",
    )


def add_threshold_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --threshold argument to an argparse parser."""
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.90,
        help="Fuzzy matching threshold (default: 0.90).",
    )


def add_output_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --output argument to an argparse parser."""
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path. Prints to stdout if not specified.",
    )
