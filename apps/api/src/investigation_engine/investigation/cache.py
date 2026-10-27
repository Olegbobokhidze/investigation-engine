"""Recent answers by question, so asking the same question again costs no LLM calls.

An answer is only as current as the documents it came from, so the API clears the cache
whenever a document is uploaded, replaced or deleted; the time limit bounds what it can't
see (the dataset scripts index outside the API). In memory, like the daily quota: the API
runs as one instance, and a restart only means the next question is answered again.
Several instances would share the cache through Redis (docs/decisions/0013-answer-cache.md).
"""

import dataclasses
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Protocol

from investigation_engine.investigation.models import Investigation, Step


class AnswerCache(Protocol):
    def get(self, question: str) -> Investigation | None: ...

    def put(self, question: str, investigation: Investigation) -> None: ...

    def clear(self) -> None: ...


def cache_key(question: str) -> str:
    """Questions that differ only in case, spacing or the closing mark share an answer."""
    return " ".join(question.lower().split()).rstrip("?.! ")


class InMemoryAnswerCache:
    """Least recently used entries are dropped past `max_entries`; entries expire after
    `ttl_s` seconds. `clock` is for tests."""

    def __init__(
        self, max_entries: int, ttl_s: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._max_entries = max_entries
        self._ttl_s = ttl_s
        self._clock = clock
        # Insertion order is recency order: a hit moves its entry to the end.
        self._entries: OrderedDict[str, tuple[float, Investigation]] = OrderedDict()

    def get(self, question: str) -> Investigation | None:
        """The stored answer with a first step saying it was reused, or None."""
        key = cache_key(question)
        entry = self._entries.get(key)
        if entry is None:
            return None
        stored_at, investigation = entry
        age_s = self._clock() - stored_at
        if age_s > self._ttl_s:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        reused = Step(
            title="Reused a recent answer",
            detail=f"The same question was answered {_describe_age(age_s)}; "
            "no document has been uploaded, replaced or deleted since.",
        )
        return dataclasses.replace(investigation, steps=[reused, *investigation.steps])

    def put(self, question: str, investigation: Investigation) -> None:
        if self._max_entries == 0:
            return
        key = cache_key(question)
        self._entries[key] = (self._clock(), investigation)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()


def _describe_age(age_s: float) -> str:
    minutes = int(age_s // 60)
    if minutes < 1:
        return "less than a minute ago"
    if minutes < 60:
        return f"{minutes} min ago"
    return f"{minutes // 60} h ago"
