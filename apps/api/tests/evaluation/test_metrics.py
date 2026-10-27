import pytest

from investigation_engine.evaluation.metrics import (
    percentile,
    recall_at_k,
    reciprocal_rank,
    unique_in_order,
)


def test_unique_in_order_keeps_first_occurrences() -> None:
    assert unique_in_order(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]


def test_recall_at_k_counts_relevant_items_in_the_top_k() -> None:
    ranked = ["x", "gold_1", "y", "gold_2"]

    assert recall_at_k(ranked, {"gold_1", "gold_2"}, k=2) == 0.5
    assert recall_at_k(ranked, {"gold_1", "gold_2"}, k=4) == 1.0


def test_recall_at_k_needs_relevant_items() -> None:
    with pytest.raises(ValueError, match="undefined"):
        recall_at_k(["x"], set(), k=1)


def test_reciprocal_rank_uses_the_first_relevant_item() -> None:
    assert reciprocal_rank(["gold", "x"], {"gold"}) == 1.0
    assert reciprocal_rank(["x", "y", "gold"], {"gold"}) == pytest.approx(1 / 3)
    assert reciprocal_rank(["x", "y"], {"gold"}) == 0.0


def test_percentile_returns_a_measured_value_by_nearest_rank() -> None:
    values = [float(n) for n in range(1, 101)]  # 1..100

    assert percentile(values, 0.50) == 50
    assert percentile(values, 0.95) == 95
    assert percentile(values, 1.0) == 100
    assert percentile([7.0], 0.95) == 7


def test_percentile_needs_values() -> None:
    with pytest.raises(ValueError, match="at least one value"):
        percentile([], 0.5)
