"""Retrieval metrics over a ranked list of document ids and the set of relevant ones."""

import math
from collections.abc import Collection, Iterable, Sequence


def unique_in_order(items: Iterable[str]) -> list[str]:
    """Drops repeats, keeping first occurrences: several chunks of one document count as
    one hit at the rank of its best chunk."""
    return list(dict.fromkeys(items))


def recall_at_k(ranked: Sequence[str], relevant: Collection[str], k: int) -> float:
    """Share of the relevant items that appear in the top k."""
    if not relevant:
        raise ValueError("Recall is undefined without relevant items.")
    return len(set(ranked[:k]) & set(relevant)) / len(relevant)


def reciprocal_rank(ranked: Sequence[str], relevant: Collection[str]) -> float:
    """1 / rank of the first relevant item (1.0 when it's first), 0.0 when none is found.
    Averaged over questions, this is MRR."""
    for rank, item in enumerate(ranked, start=1):
        if item in relevant:
            return 1 / rank
    return 0.0


def percentile(values: Sequence[float], share: float) -> float:
    """Nearest-rank percentile: the smallest value with at least `share` of the values at or
    below it (`share=0.95` is p95). No interpolation, so it is always a measured value."""
    if not values:
        raise ValueError("A percentile needs at least one value.")
    if not 0 < share <= 1:
        raise ValueError("share must be in (0, 1].")
    ordered = sorted(values)
    return ordered[max(math.ceil(share * len(ordered)), 1) - 1]
