import pytest

from investigation_engine.core.percentiles import percentile


def test_percentile_returns_a_measured_value_by_nearest_rank() -> None:
    values = [float(n) for n in range(1, 101)]  # 1..100

    assert percentile(values, 0.50) == 50
    assert percentile(values, 0.95) == 95
    assert percentile(values, 1.0) == 100
    assert percentile([7.0], 0.95) == 7


def test_percentile_needs_values() -> None:
    with pytest.raises(ValueError, match="at least one value"):
        percentile([], 0.5)
