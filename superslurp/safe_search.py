from __future__ import annotations

import re
from typing import Any


def safe_search(
    pattern: str, text: str, group: int = 1, default: Any | None = None
) -> str | None:
    if match := re.search(pattern, text):
        return match.group(group).strip()
    return default
