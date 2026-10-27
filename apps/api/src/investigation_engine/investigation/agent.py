"""The investigation agent: plan, search, let the model search further, verify, answer.

1. Plan: the model splits the question into sub-questions (decomposition).
2. Search each sub-question with hybrid search.
3. Tool-calling loop: the model reads the numbered passages and either searches again
   (often with a name it just learned, which is how multi-hop questions get their second
   hop), opens a document, or submits an answer that cites passages as [n]. The last turn
   forces an answer, so a question costs at most `max_turns` + 1 LLM calls (+1 with the
   cross-check).
4. Cross-check (optional): search once more with the answer's own claim and make the
   model compare it with every passage, so a second source that disagrees is reported
   rather than ignored.
5. Verify: citations must point at passages the model was given (`citations.py`).
"""

import asyncio
import re
import uuid
from dataclasses import dataclass, field
from typing import Literal, Protocol

import structlog
from pydantic import BaseModel, Field, ValidationError

from investigation_engine.investigation import prompts
from investigation_engine.investigation.citations import check_citations, has_citation
from investigation_engine.investigation.evidence import Evidence, Passage, format_passages
from investigation_engine.investigation.models import (
    Conflict,
    Investigation,
    InvestigationStatus,
    Source,
    Step,
    Usage,
)
from investigation_engine.llm.client import (
    ChatModel,
    Completion,
    Message,
    ToolCall,
    assistant_message,
    system_message,
    tool_message,
    user_message,
)
from investigation_engine.llm.tools import Tool
from investigation_engine.retrieval.search import SearchHit
from investigation_engine.retrieval.vector_store import ChunkRecord

log = structlog.get_logger()

# get_document shows at most this many chunks: enough context, bounded tokens.
_DOCUMENT_CHUNKS = 4


class Corpus(Protocol):
    """The search the agent needs; `retrieval.search.Retriever` provides it."""

    async def search(self, query: str, limit: int) -> list[SearchHit]: ...

    async def read_document(self, document_id: str, limit: int) -> list[ChunkRecord]: ...


class PlanArguments(BaseModel):
    sub_questions: list[str] = Field(
        min_length=1, max_length=4, description="Search queries, in the order to answer them."
    )


class SearchArguments(BaseModel):
    query: str = Field(min_length=1, description="Keywords or a short question.")


class GetDocumentArguments(BaseModel):
    document_id: str = Field(description="The document_id shown with a passage.")


class AnswerArguments(BaseModel):
    status: Literal["answered", "insufficient_evidence"]
    answer: str = Field(description="The answer, citing passages as [n].")
    conflicts: list[str] = Field(
        default=[], description="One sentence per disagreement, citing each side as [n]."
    )


PLAN_TOOL = Tool("plan_investigation", "Record the sub-questions to search.", PlanArguments)
SEARCH_TOOL = Tool(
    "search_documents",
    "Hybrid (semantic + keyword) search over the documents. Returns new numbered passages.",
    SearchArguments,
)
GET_DOCUMENT_TOOL = Tool(
    "get_document", "Read the beginning of one document as numbered passages.", GetDocumentArguments
)
ANSWER_TOOL = Tool("submit_answer", "Finish with a cited answer, or abstain.", AnswerArguments)
_LOOP_TOOLS = [SEARCH_TOOL.spec(), GET_DOCUMENT_TOOL.spec(), ANSWER_TOOL.spec()]


@dataclass
class _Run:
    """State of one investigation."""

    question: str
    evidence: Evidence = field(default_factory=Evidence)
    steps: list[Step] = field(default_factory=list)
    llm_calls: int = 0
    total_tokens: int = 0
    models: list[str] = field(default_factory=list)

    def record(self, completion: Completion) -> None:
        self.llm_calls += 1
        self.total_tokens += completion.total_tokens
        if completion.model not in self.models:
            self.models.append(completion.model)


class Investigator:
    def __init__(
        self,
        llm: ChatModel,
        corpus: Corpus,
        *,
        max_turns: int,
        search_limit: int,
        plan: bool = True,
        cross_check: bool = False,
    ) -> None:
        """`plan=False, max_turns=1` is single-shot RAG (one search, one answer): the
        baseline the evaluation compares the agent with. `cross_check` costs one more
        search and LLM call per answered question."""
        self._llm = llm
        self._corpus = corpus
        self._max_turns = max_turns
        self._search_limit = search_limit
        self._should_plan = plan
        self._should_cross_check = cross_check

    async def investigate(self, question: str) -> Investigation:
        run = _Run(question)
        sub_questions = await self._plan(run) if self._should_plan else [question]
        results = await asyncio.gather(*(self._search(run, query) for query in sub_questions))
        seed_passages = [passage for new_passages in results for passage in new_passages]
        answer = await self._answer(run, sub_questions, seed_passages)
        investigation = self._verify(run, answer)
        log.info(
            "investigation_completed",
            status=investigation.status,
            llm_calls=run.llm_calls,
            total_tokens=run.total_tokens,
            passages=len(run.evidence.document_ids),
        )
        return investigation

    async def _plan(self, run: _Run) -> list[str]:
        completion = await self._llm.complete(
            [system_message(prompts.PLANNER), user_message(run.question)],
            tools=[PLAN_TOOL.spec()],
            force_tool=PLAN_TOOL.name,
        )
        run.record(completion)
        try:
            sub_questions = PLAN_TOOL.parse(completion.tool_calls[0]).sub_questions
        except (IndexError, ValidationError):
            # Planning only seeds the search: without a plan, search the question itself.
            log.warning("investigation_plan_invalid")
            sub_questions = [run.question]
        run.steps.append(
            Step(
                title="Planned the investigation",
                detail=" · ".join(sub_questions),
                result=_count(len(sub_questions), "sub-question"),
            )
        )
        return sub_questions

    async def _search(self, run: _Run, query: str) -> list[Passage]:
        hits = await self._corpus.search(query, self._search_limit)
        new_passages, _ = run.evidence.add([hit.record for hit in hits])
        run.steps.append(
            Step(
                title="Searched documents",
                detail=f'search_documents(query="{query}")',
                result=f"{_count(len(hits), 'result')}, {len(new_passages)} new",
            )
        )
        return new_passages

    async def _answer(
        self, run: _Run, sub_questions: list[str], seed_passages: list[Passage]
    ) -> AnswerArguments | None:
        plan = "\n".join(f"{index}. {query}" for index, query in enumerate(sub_questions, 1))
        passages = format_passages(seed_passages) or "None found yet."
        messages: list[Message] = [
            system_message(prompts.INVESTIGATOR),
            user_message(f"Question: {run.question}\n\nPlan:\n{plan}\n\nPassages:\n{passages}"),
        ]
        for turn in range(self._max_turns):
            is_last_turn = turn == self._max_turns - 1
            if is_last_turn:
                # Only the answer tool is offered: a forced tool the model may not see
                # alongside others, or the API rejects its attempt to search instead.
                messages.append(user_message("No more searching: submit your answer now."))
            completion = await self._llm.complete(
                messages,
                tools=[ANSWER_TOOL.spec()] if is_last_turn else _LOOP_TOOLS,
                force_tool=ANSWER_TOOL.name if is_last_turn else None,
            )
            run.record(completion)
            messages.append(assistant_message(completion))
            for call in completion.tool_calls:
                if call.name == ANSWER_TOOL.name:
                    try:
                        answer = ANSWER_TOOL.parse(call)
                    except ValidationError as error:
                        result = f"Invalid arguments: {error.errors()[0]['msg']}. Try again."
                    else:
                        if answer.status != "answered":
                            return answer
                        if has_citation(answer.answer):
                            if not self._should_cross_check:
                                return answer
                            later_calls = completion.tool_calls[
                                completion.tool_calls.index(call) + 1 :
                            ]
                            return await self._cross_check(run, messages, call, later_calls, answer)
                        # An uncited answer would be discarded as ungrounded, so while
                        # turns are left, the model is asked to add its citations.
                        if is_last_turn:
                            return answer
                        run.steps.append(
                            Step(
                                title="Sent the answer back",
                                detail="The answer cited no passages; asked for [n] citations.",
                            )
                        )
                        result = (
                            "Rejected: the answer has no [n] citations. Resubmit it with every "
                            "sentence citing the passages it relies on."
                        )
                else:
                    result = await self._run_tool(run, call)
                # Every tool call needs its result before the model's next turn.
                messages.append(tool_message(call.id, result))
        return None

    async def _cross_check(
        self,
        run: _Run,
        messages: list[Message],
        call: ToolCall,
        later_calls: list[ToolCall],
        answer: AnswerArguments,
    ) -> AnswerArguments:
        """Searches with the answer's direct claim, then forces the model to resubmit after
        comparing it with every passage. Keeps the first answer if the second is unusable.

        `later_calls` are tool calls the model made after submitting, in the same turn:
        each still needs a result before the next LLM call."""
        claim = _first_sentence(answer.answer)
        hits = await self._corpus.search(claim, self._search_limit)
        new_passages, seen = run.evidence.add([hit.record for hit in hits])
        run.steps.append(
            Step(
                title="Cross-checked the answer",
                detail=f'search_documents(query="{claim}")',
                result=f"{_count(len(hits), 'result')}, {len(new_passages)} new",
            )
        )
        messages.append(tool_message(call.id, self._describe(new_passages, seen)))
        messages.extend(
            tool_message(later.id, "Skipped: an answer was submitted.") for later in later_calls
        )
        messages.append(user_message(prompts.CROSS_CHECK))
        completion = await self._llm.complete(
            messages, tools=[ANSWER_TOOL.spec()], force_tool=ANSWER_TOOL.name
        )
        run.record(completion)
        try:
            checked = ANSWER_TOOL.parse(completion.tool_calls[0])
        except (IndexError, ValidationError):
            return answer
        is_usable = checked.status == "answered" and has_citation(checked.answer)
        return checked if is_usable else answer

    async def _run_tool(self, run: _Run, call: ToolCall) -> str:
        try:
            if call.name == SEARCH_TOOL.name:
                query = SEARCH_TOOL.parse(call).query
                return self._describe(await self._search(run, query), [])
            if call.name == GET_DOCUMENT_TOOL.name:
                document_id = GET_DOCUMENT_TOOL.parse(call).document_id
                records = await self._corpus.read_document(document_id, _DOCUMENT_CHUNKS)
                new_passages, seen = run.evidence.add(records)
                run.steps.append(
                    Step(
                        title="Opened a document",
                        detail=f'get_document(document_id="{document_id}")',
                        result=_count(len(records), "passage"),
                    )
                )
                return self._describe(new_passages, seen)
        except ValidationError as error:
            return f"Invalid arguments: {error.errors()[0]['msg']}. Try again."
        return f"Unknown tool {call.name}. Use one of the tools provided."

    @staticmethod
    def _describe(new_passages: list[Passage], seen: list[Passage]) -> str:
        if not new_passages and not seen:
            return "No passages found. Try other words."
        parts = [format_passages(new_passages)] if new_passages else ["No new passages."]
        if seen:
            parts.append("Already shown: " + ", ".join(f"[{p.number}]" for p in seen))
        return "\n\n".join(parts)

    def _verify(self, run: _Run, answer: AnswerArguments | None) -> Investigation:
        status: InvestigationStatus = answer.status if answer else "insufficient_evidence"
        checked = check_citations(
            status,
            answer.answer if answer else "",
            answer.conflicts if answer else [],
            is_known=lambda number: run.evidence.get(number) is not None,
        )
        run.steps.append(
            Step(
                title="Verified claims against sources",
                detail=(
                    f"{_count(len(checked.cited_passages), 'source')} cited · "
                    f"{_count(checked.removed_citations, 'invalid citation')} removed · "
                    f"{_count(len(checked.conflicts), 'conflict')}"
                ),
                result="answered" if checked.status == "answered" else "abstained",
            )
        )
        sources = []
        for index, number in enumerate(checked.cited_passages, 1):
            passage = run.evidence.get(number)
            assert passage is not None  # check_citations keeps only known numbers
            record = passage.record
            sources.append(
                Source(
                    number=index,
                    document_id=record.document_id,
                    document_title=record.document_title,
                    file_type=record.file_type,
                    excerpt=record.text,
                )
            )
        return Investigation(
            id=f"inv_{uuid.uuid4().hex[:12]}",
            question=run.question,
            status=checked.status,
            answer=checked.answer,
            sources=sources,
            conflicts=[Conflict(summary=summary) for summary in checked.conflicts],
            steps=run.steps,
            usage=Usage(llm_calls=run.llm_calls, total_tokens=run.total_tokens, models=run.models),
            retrieved_document_ids=run.evidence.document_ids,
        )


def _first_sentence(answer: str) -> str:
    """The direct answer (the prompt puts it first), without its [n] citations."""
    sentence = re.split(r"(?<=[.!?])\s", answer.strip(), maxsplit=1)[0]
    return re.sub(r"\s*\[\d+\]", "", sentence)


def _count(number: int, noun: str) -> str:
    """'1 source', '2 sources': step texts are shown to users as they are."""
    return f"{number} {noun}{'' if number == 1 else 's'}"
