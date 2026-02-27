from __future__ import annotations

import cProfile
import pstats
from pathlib import Path

from superslurp.__main__ import _load_synonyms, generate_report


def main() -> None:
    fixtures = Path(__file__).resolve().parent / "fixtures"
    pdfs: list[str | Path] = sorted(fixtures.glob("Ticket*.pdf"))
    synonyms = _load_synonyms(fixtures / "synonyms.json")

    profiler = cProfile.Profile()
    profiler.enable()
    generate_report(pdfs, synonyms=synonyms)
    profiler.disable()

    stats = pstats.Stats(profiler)
    print("\n--- By tottime (self time) ---\n")
    stats.sort_stats("tottime")
    stats.print_stats(40)


if __name__ == "__main__":
    main()
