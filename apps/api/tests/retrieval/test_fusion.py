import pytest

from investigation_engine.retrieval.fusion import weighted_rrf


def test_weighted_rrf_rewards_items_ranked_high_in_both_lists() -> None:
    dense = ["a", "b", "c"]
    sparse = ["b", "d", "a"]

    fused = weighted_rrf([dense, sparse], weights=[1.0, 1.0], k=60)

    # b: 1/62 + 1/61, a: 1/61 + 1/63, d: 1/62, c: 1/63
    assert [item for item, _ in fused] == ["b", "a", "d", "c"]
    assert fused[0][1] == pytest.approx(1 / 62 + 1 / 61)


def test_weighted_rrf_weights_shift_the_order() -> None:
    dense = ["a", "b"]
    sparse = ["b", "a"]

    dense_first = weighted_rrf([dense, sparse], weights=[1.0, 0.5], k=10)
    sparse_first = weighted_rrf([dense, sparse], weights=[0.5, 1.0], k=10)

    assert [item for item, _ in dense_first] == ["a", "b"]
    assert [item for item, _ in sparse_first] == ["b", "a"]


def test_weighted_rrf_breaks_ties_by_the_first_ranking() -> None:
    fused = weighted_rrf([["a", "b"], ["b", "a"]], weights=[1.0, 1.0], k=60)

    assert [item for item, _ in fused] == ["a", "b"]


def test_weighted_rrf_smaller_k_favours_the_top_rank() -> None:
    # "a" is first in one list only; "b" is third in both.
    rankings = [["a", "x", "b"], ["y", "z", "b"]]

    gentle = weighted_rrf(rankings, weights=[1.0, 1.0], k=60)
    steep = weighted_rrf(rankings, weights=[1.0, 1.0], k=0)

    assert gentle[0][0] == "b"  # 2/63 beats 1/61: agreement wins
    assert steep[0][0] == "a"  # 1/1 beats 2/3: the top rank wins


def test_weighted_rrf_needs_one_weight_per_ranking() -> None:
    with pytest.raises(ValueError, match="one weight per ranking"):
        weighted_rrf([["a"], ["b"]], weights=[1.0], k=60)
