from investigation_engine.investigation.agent import Investigator
from investigation_engine.llm.client import Completion
from investigation_engine.retrieval.search import SearchHit
from investigation_engine.retrieval.vector_store import ChunkRecord
from tests.conftest import ScriptedLlm, tool_call


def _record(document_id: str, text: str, chunk_index: int = 0) -> ChunkRecord:
    return ChunkRecord(
        document_id=document_id,
        document_title=f"{document_id}.md",
        file_type="md",
        origin="dataset",
        chunk_index=chunk_index,
        section=None,
        text=text,
    )


class FakeCorpus:
    """Returns scripted results per query and records the queries."""

    def __init__(self, results: dict[str, list[ChunkRecord]]) -> None:
        self._results = results
        self.queries: list[str] = []

    async def search(self, query: str, limit: int) -> list[SearchHit]:
        self.queries.append(query)
        return [SearchHit(record=record, score=1.0) for record in self._results.get(query, [])]

    async def read_document(self, document_id: str, limit: int) -> list[ChunkRecord]:
        return [
            record
            for records in self._results.values()
            for record in records
            if record.document_id == document_id
        ][:limit]


INCIDENT = _record("incident", "CHG-2291 deployed at 09:05 caused INC-0412.")
CHANGELOG = _record("changelog", "CHG-2291 deployed at 09:40.")
ARCHITECTURE = _record("architecture", "payments-db is owned by Platform Data.")


def _plan(*sub_questions: str) -> Completion:
    return tool_call("plan_investigation", {"sub_questions": list(sub_questions)})


def _answer(
    answer: str, status: str = "answered", conflicts: list[str] | None = None
) -> Completion:
    return tool_call(
        "submit_answer", {"status": status, "answer": answer, "conflicts": conflicts or []}
    )


def _investigator(llm: ScriptedLlm, corpus: FakeCorpus, max_turns: int = 3) -> Investigator:
    return Investigator(llm, corpus, max_turns=max_turns, search_limit=5)


async def test_investigate_answers_with_sources_renumbered_from_one() -> None:
    llm = ScriptedLlm(_plan("cause"), _answer("CHG-2291 caused it [2]."))
    corpus = FakeCorpus({"cause": [CHANGELOG, INCIDENT]})

    result = await _investigator(llm, corpus).investigate("What caused INC-0412?")

    assert result.status == "answered"
    assert result.answer == "CHG-2291 caused it [1]."
    assert [(source.number, source.document_id) for source in result.sources] == [(1, "incident")]
    assert result.retrieved_document_ids == ["changelog", "incident"]


async def test_investigate_searches_each_sub_question_of_the_plan() -> None:
    llm = ScriptedLlm(_plan("cause", "owner"), _answer("Platform Data [2]."))
    corpus = FakeCorpus({"cause": [INCIDENT], "owner": [ARCHITECTURE]})

    result = await _investigator(llm, corpus).investigate("Who owns the cause of INC-0412?")

    assert sorted(corpus.queries) == ["cause", "owner"]
    assert [step.title for step in result.steps] == [
        "Planned the investigation",
        "Searched documents",
        "Searched documents",
        "Verified claims against sources",
    ]


async def test_investigate_lets_the_model_search_for_the_next_hop() -> None:
    llm = ScriptedLlm(
        _plan("cause"),
        tool_call("search_documents", {"query": "payments-db owner"}),
        _answer("Platform Data owns payments-db [2]."),
    )
    corpus = FakeCorpus({"cause": [INCIDENT], "payments-db owner": [ARCHITECTURE]})

    result = await _investigator(llm, corpus).investigate("Who owns the cause of INC-0412?")

    assert corpus.queries == ["cause", "payments-db owner"]
    assert result.sources[0].document_id == "architecture"


async def test_investigate_offers_only_the_answer_tool_on_the_last_turn() -> None:
    llm = ScriptedLlm(
        _plan("cause"),
        tool_call("search_documents", {"query": "more"}),
        _answer("CHG-2291 [1]."),
    )

    await _investigator(llm, FakeCorpus({"cause": [INCIDENT]}), max_turns=2).investigate("Why?")

    assert llm.tool_names(1) == ["search_documents", "get_document", "submit_answer"]
    assert llm.tool_names(2) == ["submit_answer"]
    assert llm.calls[2]["force"] == "submit_answer"


async def test_investigate_sends_an_uncited_answer_back_for_citations() -> None:
    llm = ScriptedLlm(_plan("cause"), _answer("CHG-2291 caused it."), _answer("CHG-2291 [1]."))

    result = await _investigator(llm, FakeCorpus({"cause": [INCIDENT]})).investigate("Why?")

    assert result.status == "answered"
    assert "Sent the answer back" in [step.title for step in result.steps]


async def test_investigate_abstains_when_the_final_answer_cites_nothing() -> None:
    llm = ScriptedLlm(_plan("cause"), _answer("CHG-2291 caused it."))

    result = await _investigator(llm, FakeCorpus({"cause": [INCIDENT]}), max_turns=1).investigate(
        "Why?"
    )

    assert result.status == "insufficient_evidence"
    assert result.sources == []


async def test_investigate_reports_a_conflict_citing_both_sides() -> None:
    llm = ScriptedLlm(
        _plan("deploy time"),
        _answer(
            "The sources disagree: 09:05 [1] or 09:40 [2].",
            conflicts=["The incident report says 09:05 [1]; the change log says 09:40 [2]."],
        ),
    )
    corpus = FakeCorpus({"deploy time": [INCIDENT, CHANGELOG]})

    result = await _investigator(llm, corpus).investigate("When was CHG-2291 deployed?")

    assert [conflict.summary for conflict in result.conflicts] == [
        "The incident report says 09:05 [1]; the change log says 09:40 [2]."
    ]


async def test_investigate_tells_the_model_about_invalid_tool_arguments() -> None:
    llm = ScriptedLlm(
        _plan("cause"),
        tool_call("search_documents", {"wrong": "field"}),
        _answer("CHG-2291 [1]."),
    )

    await _investigator(llm, FakeCorpus({"cause": [INCIDENT]})).investigate("Why?")

    tool_result = llm.last_message(call=2)
    assert tool_result["role"] == "tool"
    assert str(tool_result["content"]).startswith("Invalid arguments")


async def test_investigate_searches_the_question_itself_when_the_plan_is_invalid() -> None:
    llm = ScriptedLlm(
        tool_call("plan_investigation", {"sub_questions": []}), _answer("CHG-2291 [1].")
    )
    corpus = FakeCorpus({"Why INC-0412?": [INCIDENT]})

    result = await _investigator(llm, corpus).investigate("Why INC-0412?")

    assert corpus.queries == ["Why INC-0412?"]
    assert result.status == "answered"


async def test_investigate_opens_a_document_the_model_asks_for() -> None:
    llm = ScriptedLlm(
        _plan("cause"),
        tool_call("get_document", {"document_id": "changelog"}),
        _answer("Deployed at 09:40 [2]."),
    )
    corpus = FakeCorpus({"cause": [INCIDENT], "unused": [CHANGELOG]})

    result = await _investigator(llm, corpus).investigate("When?")

    assert "Opened a document" in [step.title for step in result.steps]
    assert result.sources[0].document_id == "changelog"


async def test_investigate_without_planning_is_one_search_and_one_answer() -> None:
    llm = ScriptedLlm(_answer("CHG-2291 [1]."))
    corpus = FakeCorpus({"Why INC-0412?": [INCIDENT]})
    investigator = Investigator(llm, corpus, max_turns=1, search_limit=5, plan=False)

    result = await investigator.investigate("Why INC-0412?")

    assert corpus.queries == ["Why INC-0412?"]
    assert result.usage.llm_calls == 1
    assert result.status == "answered"
