import json
from collections.abc import Mapping, Sequence
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from investigation_engine.core.errors import UpstreamError
from investigation_engine.core.rate_limit import DailyQuota
from investigation_engine.llm.client import Completion, Message
from tests.conftest import ScriptedLlm, tool_call

pytestmark = pytest.mark.integration

CHANGELOG = b"CHG-2291 reduced the payments-db pool from 50 to 20 connections."


@pytest.fixture
def llm() -> ScriptedLlm:
    return ScriptedLlm(
        tool_call("plan_investigation", {"sub_questions": ["payments-db pool"]}),
        tool_call(
            "submit_answer",
            {"status": "answered", "answer": "The pool went from 50 to 20 connections [1]."},
        ),
    )


def test_create_investigation_answers_from_the_indexed_documents(client: TestClient) -> None:
    client.post("/documents", files=[("files", ("changelog.md", CHANGELOG))])

    response = client.post("/investigations", json={"question": "How big is the pool?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["answer"] == "The pool went from 50 to 20 connections [1]."
    assert body["sources"] == [
        {
            "number": 1,
            "documentId": body["sources"][0]["documentId"],
            "documentTitle": "changelog.md",
            "fileType": "md",
            "excerpt": CHANGELOG.decode(),
        }
    ]
    assert body["steps"][0]["title"] == "Planned the investigation"


def test_create_investigation_rejects_a_blank_question(client: TestClient) -> None:
    response = client.post("/investigations", json={"question": "   "})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"


def test_create_investigation_over_the_daily_cap_is_rate_limited(client: TestClient) -> None:
    app = cast(FastAPI, client.app)
    app.state.investigation_quota = DailyQuota(per_client=1, total=10)
    client.post("/investigations", json={"question": "How big is the pool?"})

    # A different question: the same one would be answered from the cache.
    response = client.post("/investigations", json={"question": "Who owns payments-db?"})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


def test_create_investigation_answers_a_repeated_question_from_the_cache(
    client: TestClient, llm: ScriptedLlm
) -> None:
    app = cast(FastAPI, client.app)
    app.state.investigation_quota = DailyQuota(per_client=1, total=10)
    client.post("/documents", files=[("files", ("changelog.md", CHANGELOG))])
    first = client.post("/investigations", json={"question": "How big is the pool?"}).json()

    response = client.post("/investigations", json={"question": "how big is the pool"})

    assert response.status_code == 200  # not 429: a cached answer costs no quota
    body = response.json()
    assert body["answer"] == first["answer"]
    assert body["steps"][0]["title"] == "Reused a recent answer"
    assert len(llm.calls) == 2  # the plan and the answer of the first request only


def _plan_and_answer(answer: str) -> list[Completion]:
    return [
        tool_call("plan_investigation", {"sub_questions": ["payments-db pool"]}),
        tool_call("submit_answer", {"status": "answered", "answer": answer}),
    ]


@pytest.mark.parametrize(
    "llm",
    [ScriptedLlm(*_plan_and_answer("50 connections [1]."), *_plan_and_answer("20 [1]."))],
)
def test_create_investigation_after_an_upload_does_not_reuse_the_old_answer(
    client: TestClient,
) -> None:
    client.post("/documents", files=[("files", ("runbook.md", b"The pool has 50 connections."))])
    client.post("/investigations", json={"question": "How big is the pool?"})
    client.post("/documents", files=[("files", ("changelog.md", CHANGELOG))])

    response = client.post("/investigations", json={"question": "How big is the pool?"})

    assert response.json()["answer"] == "20 [1]."


# Overrides the module's `llm` fixture: the app starts without an LLM.
@pytest.mark.parametrize("llm", [None])
def test_create_investigation_without_an_llm_key_is_not_configured(client: TestClient) -> None:
    response = client.post("/investigations", json={"question": "How big is the pool?"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "not_configured"


def _events(body: str) -> list[tuple[str, dict[str, object]]]:
    """(event name, data) pairs from a Server-Sent Events body."""
    events = []
    for block in body.strip().split("\n\n"):
        name_line, data_line = block.split("\n")
        events.append(
            (name_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: ")))
        )
    return events


def test_stream_investigation_sends_each_step_then_the_result(client: TestClient) -> None:
    client.post("/documents", files=[("files", ("changelog.md", CHANGELOG))])

    response = client.post("/investigations/stream", json={"question": "How big is the pool?"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _events(response.text)
    names = [name for name, _ in events]
    assert names[-1] == "result"
    assert set(names[:-1]) == {"step"}
    assert events[0][1]["title"] == "Planned the investigation"
    result = events[-1][1]
    assert result["answer"] == "The pool went from 50 to 20 connections [1]."
    assert result["steps"] == [data for name, data in events if name == "step"]


def test_stream_investigation_sends_a_cached_answer_at_once(client: TestClient) -> None:
    client.post("/documents", files=[("files", ("changelog.md", CHANGELOG))])
    client.post("/investigations", json={"question": "How big is the pool?"})

    response = client.post("/investigations/stream", json={"question": "How big is the pool?"})

    events = _events(response.text)
    assert events[0] == (
        "step",
        {
            "title": "Reused a recent answer",
            "detail": "The same question was answered less than a minute ago; "
            "no document has been uploaded, replaced or deleted since.",
            "result": None,
        },
    )
    assert events[-1][0] == "result"


class FailingLlm:
    """An LLM provider that is down: every call fails after the client's retries."""

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[Mapping[str, object]] = (),
        force_tool: str | None = None,
    ) -> Completion:
        raise UpstreamError("The language model is unavailable. Please try again in a minute.")


@pytest.mark.parametrize("llm", [FailingLlm()])
def test_stream_investigation_reports_a_failure_as_an_error_event(client: TestClient) -> None:
    response = client.post("/investigations/stream", json={"question": "How big is the pool?"})

    assert _events(response.text)[-1] == (
        "error",
        {
            "error": {
                "code": "upstream_error",
                "message": "The language model is unavailable. Please try again in a minute.",
            }
        },
    )
