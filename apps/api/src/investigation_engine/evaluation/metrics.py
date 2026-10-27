"""Retrieval metrics over a ranked list of document ids and the set of relevant ones."""

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
