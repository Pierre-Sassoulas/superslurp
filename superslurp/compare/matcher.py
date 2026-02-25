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
        self._cache: dict[str, str] = {}

    def match(self, name: str) -> str:
        """Return the canonical name for the given product."""
        normalized = normalize_for_matching(name)
        if normalized in self._cache:
            return self._cache[normalized]
        len_n = len(normalized)
        for canon_norm in self._canonicals:
            # Length ratio can't exceed 2*min/max; skip if below threshold
            len_c = len(canon_norm)
            shorter = min(len_n, len_c)
            if 2 * shorter < self.threshold * (len_n + len_c):
                continue
            sm = SequenceMatcher(None, normalized, canon_norm)
            if sm.quick_ratio() >= self.threshold and sm.ratio() >= self.threshold:
                self._cache[normalized] = canon_norm
                return canon_norm
        self._canonicals.append(normalized)
        self._cache[normalized] = normalized
        return normalized
