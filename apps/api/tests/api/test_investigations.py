from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from investigation_engine.core.rate_limit import DailyQuota
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

    response = client.post("/investigations", json={"question": "How big is the pool?"})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


# Overrides the module's `llm` fixture: the app starts without an LLM.
@pytest.mark.parametrize("llm", [None])
def test_create_investigation_without_an_llm_key_is_not_configured(client: TestClient) -> None:
    response = client.post("/investigations", json={"question": "How big is the pool?"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "not_configured"
