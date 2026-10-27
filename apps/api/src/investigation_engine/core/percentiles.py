"""Latency percentiles, shared by the live metrics and the evaluation runners."""

import math
from collections.abc import Sequence


def percentile(values: Sequence[float], share: float) -> float:
    """Nearest-rank percentile: the smallest value with at least `share` of the values at or
    below it (`share=0.95` is p95). No interpolation, so it is always a measured value."""
    if not values:
        raise ValueError("A percentile needs at least one value.")
    if not 0 < share <= 1:
        raise ValueError("share must be in (0, 1].")
    ordered = sorted(values)
    return ordered[max(math.ceil(share * len(ordered)), 1) - 1]
