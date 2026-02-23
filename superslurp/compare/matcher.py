from __future__ import annotations

from difflib import SequenceMatcher

from superslurp.compare.normalize import normalize_for_matching


class FuzzyMatcher:  # pylint: disable=too-few-public-methods
    """Groups product names by fuzzy similarity.

    Returns the canonical (normalized) name for a given product name.
    """

    def __init__(
        self,
        threshold: float = 0.90,
    ) -> None:
        self.threshold = threshold
        self._canonicals: list[str] = []

    def match(self, name: str) -> str:
        """Return the canonical name for the given product."""
        normalized = normalize_for_matching(name)
        for canon_norm in self._canonicals:
            ratio = SequenceMatcher(None, normalized, canon_norm).ratio()
            if ratio >= self.threshold:
                return canon_norm
        self._canonicals.append(normalized)
        return normalized
