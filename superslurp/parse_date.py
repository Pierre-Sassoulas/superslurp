from __future__ import annotations

from datetime import datetime

from superslurp.safe_search import safe_search

DATETIME_PATTERN = r"Opérateur        Date      Heure      TPV     Ticket  \n.*(\d2\/\d+\/\d+ +\d+:\d+)"


def parse_date(text: str) -> datetime | None:
    if (str_date := safe_search(DATETIME_PATTERN, text)) is None:
        return None
    return datetime.strptime(str_date, "%d/%m/%y %H:%M")
