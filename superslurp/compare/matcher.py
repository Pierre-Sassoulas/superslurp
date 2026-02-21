from __future__ import annotations

from difflib import SequenceMatcher

from superslurp.compare.normalize import normalize_for_matching


class FuzzyMatcher:
    """Groups product names by fuzzy similarity.

    Match key is (normalized_name, grams). Grams must match exactly
    for items to be grouped together.
    """

    def __init__(self, threshold: float = 0.90) -> None:
        self.threshold = threshold
        # Maps (canonical_normalized, grams) -> original canonical name
        self._canonicals: dict[tuple[str, float | None], str] = {}

    def match(
        self, name: str, grams: float | None
    ) -> tuple[str, float | None]:
        """Return the (canonical_name, grams) key for the given product."""
        normalized = normalize_for_matching(name)
        for (canon_norm, canon_grams), canon_name in self._canonicals.items():
            if canon_grams != grams:
                continue
            ratio = SequenceMatcher(None, normalized, canon_norm).ratio()
            if ratio >= self.threshold:
                return canon_name, grams
        # New canonical entry — keep first-seen name as canonical
        self._canonicals[(normalized, grams)] = name
        return name, grams
