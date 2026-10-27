from datetime import date

import pytest

from investigation_engine.core.errors import RateLimitedError
from investigation_engine.core.rate_limit import DailyQuota


class Clock:
    def __init__(self) -> None:
        self.day = date(2026, 10, 27)

    def __call__(self) -> date:
        return self.day


def test_daily_quota_allows_uses_up_to_the_client_cap() -> None:
    quota = DailyQuota(per_client=2, total=10, today=Clock())
    quota.take("1.1.1.1")
    quota.take("1.1.1.1")

    with pytest.raises(RateLimitedError, match="limit of 2"):
        quota.take("1.1.1.1")


def test_daily_quota_counts_each_client_separately() -> None:
    quota = DailyQuota(per_client=1, total=10, today=Clock())
    quota.take("1.1.1.1")

    quota.take("2.2.2.2")  # doesn't raise


def test_daily_quota_stops_everyone_at_the_total_cap() -> None:
    quota = DailyQuota(per_client=5, total=2, today=Clock())
    quota.take("1.1.1.1")
    quota.take("2.2.2.2")

    with pytest.raises(RateLimitedError, match="demo has reached"):
        quota.take("3.3.3.3")


def test_daily_quota_resets_on_a_new_day() -> None:
    clock = Clock()
    quota = DailyQuota(per_client=1, total=1, today=clock)
    quota.take("1.1.1.1")

    clock.day = date(2026, 10, 28)

    quota.take("1.1.1.1")  # doesn't raise
