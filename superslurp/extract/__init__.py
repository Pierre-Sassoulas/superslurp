from __future__ import annotations

__all__ = ["convert_to_text", "extract_text"]

import logging
from pathlib import Path

from pypdf import PdfReader


def extract_text(filename: str | Path) -> str:
    reader = PdfReader(filename)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text


def convert_to_text(filename: str | Path) -> str:
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
    return text.strip()
