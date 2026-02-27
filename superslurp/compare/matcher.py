from __future__ import annotations

from difflib import SequenceMatcher

from superslurp.compare.normalize import normalize_for_matching


class FuzzyMatcher:  # pylint: disable=too-few-public-methods
    """Groups product names by fuzzy similarity.

    Returns the canonical (normalized) name for a given product name.
    Uses a token inverted index to avoid comparing every name against
    every canonical, and reuses SequenceMatcher instances so that the
    expensive ``set_seq2`` (``__chain_b``) runs only once per canonical.
    """

    def __init__(
        self,
        threshold: float = 0.90,
    ) -> None:
        self.threshold = threshold
        self._canonicals: list[str] = []
        self._cache: dict[str, str] = {}
        # Raw name → canonical, skips normalize_for_matching entirely on repeats
        self._raw_cache: dict[str, str] = {}
        # One SequenceMatcher per canonical, with seq2 pre-set
        self._matchers: list[SequenceMatcher[str]] = []
        # Token → list of canonical indices (inverted index)
        self._token_index: dict[str, list[int]] = {}

    def match(self, name: str) -> str:
        """Return the canonical name for the given product."""
        if (cached := self._raw_cache.get(name)) is not None:
            return cached
        if (normalized := normalize_for_matching(name)) in self._cache:
            result = self._cache[normalized]
            self._raw_cache[name] = result
            return result

        # Find candidates that share at least one word token
        tokens = normalized.split()
        candidate_indices: set[int] = set()
        for token in tokens:
            if (indices := self._token_index.get(token)) is not None:
                candidate_indices.update(indices)

        len_n = len(normalized)
        # Check candidates in insertion order (first registered wins)
        for idx in sorted(candidate_indices):
            canon_norm = self._canonicals[idx]
            # Length pre-filter
            len_c = len(canon_norm)
            shorter = min(len_n, len_c)
            if 2 * shorter < self.threshold * (len_n + len_c):
                continue
            sm = self._matchers[idx]
            sm.set_seq1(normalized)
            if sm.quick_ratio() >= self.threshold and sm.ratio() >= self.threshold:
                self._cache[normalized] = canon_norm
                self._raw_cache[name] = canon_norm
                return canon_norm

        # No match — register new canonical
        idx = len(self._canonicals)
        self._canonicals.append(normalized)
        sm = SequenceMatcher(None, "", normalized)
        self._matchers.append(sm)
        for token in tokens:
            self._token_index.setdefault(token, []).append(idx)
        self._cache[normalized] = normalized
        self._raw_cache[name] = normalized
        return normalized
