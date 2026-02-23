from __future__ import annotations

import argparse
from pathlib import Path


def add_synonyms_arg(parser: argparse.ArgumentParser) -> None:
    """Add the --synonyms argument to an argparse parser."""
    parser.add_argument(
        "--synonyms",
        type=Path,
        default=None,
        help="JSON file mapping abbreviations to full names.",
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
