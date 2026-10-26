"""Weighted Reciprocal Rank Fusion: merges several rankings of the same items into one.

Dense (cosine) and BM25 scores live on different scales, so they can't be added. RRF ignores
scores and uses only positions:

    score(item) = Σ_i  weight_i / (k + rank_i(item))        rank counts from 1

An item near the top of any list scores well; one high in several lists scores best.
`k` sets how fast credit decays with rank (small k: the top few ranks dominate), and a
weight lets a noisier list count for less. An item missing from a list gets nothing from it.

Reference: Cormack, Clarke & Büttcher, "Reciprocal Rank Fusion outperforms Condorcet and
individual Rank Learning Methods" (SIGIR 2009), which uses k = 60 and equal weights.
"""

from collections.abc import Sequence


def weighted_rrf(
    rankings: Sequence[Sequence[str]], weights: Sequence[float], k: int
) -> list[tuple[str, float]]:
    """Returns (item, score) pairs, best first. Ties keep the order items were first seen,
    so the first ranking breaks them."""
    if len(rankings) != len(weights):
        raise ValueError("Pass one weight per ranking.")
    if k < 0:
        raise ValueError("k must not be negative.")

    scores: dict[str, float] = {}
    for ranking, weight in zip(rankings, weights, strict=True):
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + weight / (k + rank)
    # sorted() is stable, and dicts keep insertion order: equal scores stay first-seen first.
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
