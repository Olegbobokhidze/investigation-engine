from investigation_engine.investigation.cache import InMemoryAnswerCache, cache_key
from investigation_engine.investigation.models import Investigation, Step, Usage


def _investigation(answer: str = "CHG-2291 [1].") -> Investigation:
    return Investigation(
        id="inv_1",
        question="What caused INC-0412?",
        status="answered",
        answer=answer,
        sources=[],
        conflicts=[],
        steps=[Step(title="Planned the investigation", detail="cause")],
        usage=Usage(llm_calls=2, total_tokens=5000, models=["gpt-5-mini"]),
        retrieved_document_ids=[],
    )


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_cache_key_ignores_case_spacing_and_the_closing_mark() -> None:
    assert cache_key("  What caused   INC-0412? ") == cache_key("what caused inc-0412")


def test_cache_returns_the_answer_with_a_step_saying_it_was_reused() -> None:
    clock = FakeClock()
    cache = InMemoryAnswerCache(max_entries=10, ttl_s=3600, clock=clock)
    cache.put("What caused INC-0412?", _investigation())
    clock.now += 300

    cached = cache.get("what caused INC-0412")

    assert cached is not None
    assert cached.answer == "CHG-2291 [1]."
    assert [step.title for step in cached.steps] == [
        "Reused a recent answer",
        "Planned the investigation",
    ]
    assert "5 min ago" in cached.steps[0].detail


def test_cache_misses_a_question_it_has_not_seen() -> None:
    cache = InMemoryAnswerCache(max_entries=10, ttl_s=3600)

    assert cache.get("What caused INC-0412?") is None


def test_cache_drops_an_entry_older_than_the_time_limit() -> None:
    clock = FakeClock()
    cache = InMemoryAnswerCache(max_entries=10, ttl_s=60, clock=clock)
    cache.put("What caused INC-0412?", _investigation())
    clock.now += 61

    assert cache.get("What caused INC-0412?") is None


def test_cache_drops_the_least_recently_used_entry_when_full() -> None:
    cache = InMemoryAnswerCache(max_entries=2, ttl_s=3600)
    cache.put("first", _investigation())
    cache.put("second", _investigation())
    cache.get("first")  # now the most recently used

    cache.put("third", _investigation())

    assert cache.get("second") is None
    assert cache.get("first") is not None
    assert cache.get("third") is not None


def test_cache_clear_forgets_every_answer() -> None:
    cache = InMemoryAnswerCache(max_entries=10, ttl_s=3600)
    cache.put("What caused INC-0412?", _investigation())

    cache.clear()

    assert cache.get("What caused INC-0412?") is None


def test_cache_with_no_entries_allowed_keeps_nothing() -> None:
    cache = InMemoryAnswerCache(max_entries=0, ttl_s=3600)

    cache.put("What caused INC-0412?", _investigation())

    assert cache.get("What caused INC-0412?") is None
