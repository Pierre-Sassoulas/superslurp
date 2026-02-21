from __future__ import annotations

from difflib import SequenceMatcher

from superslurp.compare.normalize import normalize_for_matching


class FuzzyMatcher:  # pylint: disable=too-few-public-methods
    """Groups product names by fuzzy similarity.

    Returns the canonical name for a given product name.
    """

    def __init__(self, threshold: float = 0.90) -> None:
        self.threshold = threshold
        # Maps canonical_normalized -> original canonical name
        self._canonicals: dict[str, str] = {}

    def match(self, name: str) -> str:
        """Return the canonical name for the given product."""
        normalized = normalize_for_matching(name)
        for canon_norm, canon_name in self._canonicals.items():
            ratio = SequenceMatcher(None, normalized, canon_norm).ratio()
            if ratio >= self.threshold:
                return canon_name
        # New canonical entry — keep first-seen name as canonical
        self._canonicals[normalized] = name
        return name
