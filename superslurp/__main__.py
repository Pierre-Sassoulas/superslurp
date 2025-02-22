from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pypdf import PdfReader

from superslurp.parser import parse_text


def parse_superu_receipt(filename: str | Path) -> str:
    text = extract_text(filename)
    return json.dumps(parse_text(text), indent=4)


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
    print("File processed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
