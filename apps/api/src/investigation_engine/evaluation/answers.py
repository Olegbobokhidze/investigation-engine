"""Answer evaluation: the agent against a single-shot RAG baseline on 48 questions.

Scores answer correctness (an LLM judge from another model family), citation precision and
recall against gold documents, abstention, contradiction detection, resistance to an
instruction planted in a document, and retrieval Recall@K / MRR, plus tokens and latency.

Two steps, so scoring never spends LLM quota again:
    run     asks every question with each configuration and appends one JSON line per
            answer; resumable: questions already in the file are skipped
    report  computes the metrics from those files and prints Markdown tables
    compare scores the agent of two runs (e.g. two models) on their shared questions

Run from apps/api against the loaded corpus:
    uv run python -m investigation_engine.evaluation.answers run --output-dir DIR
    uv run python -m investigation_engine.evaluation.answers report --output-dir DIR
"""

import argparse
import asyncio
import hashlib
import json
import statistics
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pyarrow.parquet as parquet
import structlog
from pydantic import BaseModel, ValidationError

from investigation_engine.core.config import Settings, get_settings
from investigation_engine.core.errors import UpstreamError
from investigation_engine.core.logging import configure_logging
from investigation_engine.datasets.hotpotqa import document_id, download
from investigation_engine.evaluation.metrics import recall_at_k, reciprocal_rank, unique_in_order
from investigation_engine.investigation.agent import Investigator
from investigation_engine.investigation.models import Investigation
from investigation_engine.llm.client import ChatModel, LlmClient, system_message, user_message
from investigation_engine.llm.tools import Tool
from investigation_engine.retrieval.embeddings import Embedder
from investigation_engine.retrieval.search import FusionSettings, Retriever
from investigation_engine.retrieval.vector_store import VectorStore

log = structlog.get_logger()

NORTHWIND_QUESTIONS = Path("data/eval/northwind-questions.jsonl")
# The retrieval evaluation tuned RRF on the first 200 questions (by hash), so these come
# after them: answers are measured on questions nothing was tuned on.
HOTPOTQA_OFFSET = 200
HOTPOTQA_COUNT = 20
# A batch run has no user waiting: retry often and wait out long rate limits (the
# per-minute and rolling daily token quotas) instead of failing the question.
EVAL_MAX_RETRIES = 8
EVAL_MAX_RETRY_AFTER_S = 600.0


@dataclass(frozen=True)
class EvalQuestion:
    id: str
    type: str  # simple, multi_hop, contradictory or unanswerable
    question: str
    answer: str | None  # None: the corpus can't answer it
    gold_document_ids: list[str]
    # Exact strings an answer needs to have seen (Northwind only); the chunking
    # evaluation checks they are in the retrieved chunks.
    key_facts: list[str] = field(default_factory=list)
    # Prompt-injection questions: a string only an answer that obeyed the instruction
    # planted in a document would contain.
    injection_marker: str | None = None


@dataclass(frozen=True)
class Config:
    name: str
    plan: bool
    max_turns: int
    search_limit: int
    cross_check: bool = False


# Single-shot gets more passages from its one search, so both see a similar amount of text.
CONFIGS = {
    "agent": Config("agent", plan=True, max_turns=4, search_limit=6),
    "single-shot": Config("single-shot", plan=False, max_turns=1, search_limit=10),
    "agent-cross-check": Config(
        "agent-cross-check", plan=True, max_turns=4, search_limit=6, cross_check=True
    ),
}


def load_northwind_questions() -> list[EvalQuestion]:
    return [
        EvalQuestion(**json.loads(line))
        for line in NORTHWIND_QUESTIONS.read_text().splitlines()
        if line.strip()
    ]


def load_questions() -> list[EvalQuestion]:
    northwind = load_northwind_questions()
    table = parquet.read_table(
        download(), columns=["id", "question", "answer", "supporting_facts"]
    ).to_pylist()
    table.sort(key=lambda row: hashlib.sha256(row["id"].encode()).hexdigest())
    hotpotqa = [
        EvalQuestion(
            id=f"hp-{row['id']}",
            type="multi_hop",
            question=row["question"],
            answer=row["answer"],
            gold_document_ids=sorted(
                {document_id(title) for title in row["supporting_facts"]["title"]}
            ),
        )
        for row in table[HOTPOTQA_OFFSET : HOTPOTQA_OFFSET + HOTPOTQA_COUNT]
    ]
    return hotpotqa + northwind


class Grade(BaseModel):
    correct: bool
    reason: str


GRADE_TOOL = Tool("grade", "Record the verdict.", Grade)

JUDGE_PROMPT = """You grade a question-answering system's answer against a reference answer.
The answer is correct when it states the same fact as the reference. Wording, format and \
extra correct detail don't matter; a missing or different key fact does.
If the reference starts with "conflicting:", the sources disagree: the answer is correct \
only if it says they disagree and gives both values. Picking one value is incorrect."""


async def grade(judge: ChatModel, question: EvalQuestion, investigation: Investigation) -> Grade:
    conflicts = "\n".join(conflict.summary for conflict in investigation.conflicts) or "none"
    completion = await judge.complete(
        [
            system_message(JUDGE_PROMPT),
            user_message(
                f"Question: {question.question}\nReference: {question.answer}\n"
                f"Answer: {investigation.answer}\nConflicts reported: {conflicts}"
            ),
        ],
        tools=[GRADE_TOOL.spec()],
        force_tool=GRADE_TOOL.name,
    )
    try:
        return GRADE_TOOL.parse(completion.tool_calls[0])
    except (IndexError, ValidationError):
        return Grade(correct=False, reason="The judge returned no valid verdict.")


async def run(
    output_dir: Path, config_names: list[str], settings: Settings, northwind_only: bool = False
) -> None:
    questions = load_northwind_questions() if northwind_only else load_questions()
    llm_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else ""
    judge_key = settings.judge_api_key.get_secret_value() if settings.judge_api_key else llm_key

    def client(base_url: str, api_key: str, model: str) -> LlmClient:
        # One model, no fallback: a silent switch to another model would skew the comparison.
        return LlmClient(
            base_url=base_url,
            api_key=api_key,
            models=[model],
            timeout_s=settings.llm_timeout_s,
            max_retries=EVAL_MAX_RETRIES,
            max_retry_after_s=EVAL_MAX_RETRY_AFTER_S,
        )

    store = VectorStore.from_settings(settings)
    retriever = Retriever(
        Embedder(settings.embedding_model, settings.embedding_query_prefix),
        store,
        FusionSettings.from_settings(settings),
    )
    llm = client(settings.llm_base_url, llm_key, settings.llm_model)
    judge = client(settings.judge_base_url, judge_key, settings.judge_model)
    try:
        await _record_retrieval(retriever, questions, output_dir / "retrieval.jsonl")
        for name in config_names:
            config = CONFIGS[name]
            investigator = Investigator(
                llm,
                retriever,
                max_turns=config.max_turns,
                search_limit=config.search_limit,
                plan=config.plan,
                cross_check=config.cross_check,
            )
            await _record_answers(investigator, judge, questions, output_dir / f"{name}.jsonl")
    finally:
        await llm.close()
        await judge.close()
        await store.close()


async def _record_retrieval(
    retriever: Retriever, questions: list[EvalQuestion], path: Path
) -> None:
    """The documents plain hybrid search ranks for each question, for Recall@K and MRR."""
    for question in _pending(questions, path):
        hits = await retriever.search(question.question, limit=10)
        ranked = unique_in_order(hit.record.document_id for hit in hits)
        _append(path, {"id": question.id, "ranked_document_ids": ranked})


async def _record_answers(
    investigator: Investigator, judge: ChatModel, questions: list[EvalQuestion], path: Path
) -> None:
    for index, question in enumerate(_pending(questions, path), 1):
        started = time.monotonic()
        try:
            investigation = await investigator.investigate(question.question)
        except UpstreamError:
            # Most likely the daily token quota: stop, and resume later from this question.
            log.error("evaluation_stopped", question=question.id, file=str(path))
            return
        seconds = time.monotonic() - started
        verdict = None
        if question.answer is not None and investigation.status == "answered":
            verdict = await grade(judge, question, investigation)
        _append(
            path,
            {
                **asdict(question),
                "status": investigation.status,
                "answer": investigation.answer,
                "conflicts": [conflict.summary for conflict in investigation.conflicts],
                "cited_document_ids": unique_in_order(s.document_id for s in investigation.sources),
                "retrieved_document_ids": investigation.retrieved_document_ids,
                "steps": [asdict(step) for step in investigation.steps],
                "verdict": verdict.model_dump() if verdict else None,
                "llm_calls": investigation.usage.llm_calls,
                "total_tokens": investigation.usage.total_tokens,
                "models": investigation.usage.models,
                "seconds": round(seconds, 2),
            },
        )
        log.info("evaluation_progress", file=path.name, done=index, question=question.id)


def _pending(questions: list[EvalQuestion], path: Path) -> list[EvalQuestion]:
    done = {record["id"] for record in _read(path)}
    return [question for question in questions if question.id not in done]


def _append(path: Path, record: dict[str, object]) -> None:
    with path.open("a") as file:
        file.write(json.dumps(record) + "\n")


def _read(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# --- report ---------------------------------------------------------------------------


def is_correct(record: dict[str, object]) -> bool:
    """Unanswerable questions are correct when the engine abstains; answerable ones when
    the judge accepts the answer (an abstention there counts as wrong)."""
    if record["type"] == "unanswerable":
        return record["status"] == "insufficient_evidence"
    verdict = record["verdict"]
    return isinstance(verdict, dict) and verdict["correct"] is True


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def score(records: list[dict[str, object]]) -> dict[str, float | None]:
    answerable = [r for r in records if r["type"] != "unanswerable"]
    abstained = [r for r in records if r["status"] == "insufficient_evidence"]
    unanswerable = [r for r in records if r["type"] == "unanswerable"]
    contradictory = [r for r in records if r["type"] == "contradictory"]
    others = [r for r in records if r["type"] != "contradictory"]
    attacked = [r for r in records if r.get("injection_marker")]

    cited = gold_cited = gold_total = retrieved_gold = 0
    for record in answerable:
        gold = set(_strings(record["gold_document_ids"]))
        citations = set(_strings(record["cited_document_ids"]))
        cited += len(citations)
        gold_cited += len(citations & gold)
        gold_total += len(gold)
        retrieved_gold += len(set(_strings(record["retrieved_document_ids"])) & gold)
    cited_correct = sum(
        len(set(_strings(r["cited_document_ids"])) & set(_strings(r["gold_document_ids"])))
        for r in answerable
    )

    def correct_share(subset: Callable[[dict[str, object]], bool]) -> float | None:
        chosen = [r for r in records if subset(r)]
        return _ratio(sum(is_correct(r) for r in chosen), len(chosen))

    seconds = [float(str(r["seconds"])) for r in records]
    return {
        "questions": len(records),
        "correct": correct_share(lambda r: True),
        "correct_simple": correct_share(lambda r: r["type"] == "simple"),
        "correct_multi_hop": correct_share(lambda r: r["type"] == "multi_hop"),
        "correct_contradictory": correct_share(lambda r: r["type"] == "contradictory"),
        "correct_unanswerable": correct_share(lambda r: r["type"] == "unanswerable"),
        "citation_precision": _ratio(cited_correct, cited),
        "citation_recall": _ratio(gold_cited, gold_total),
        "evidence_recall": _ratio(retrieved_gold, gold_total),
        "abstention_precision": _ratio(
            sum(r["type"] == "unanswerable" for r in abstained), len(abstained)
        ),
        "abstention_recall": _ratio(
            sum(r["status"] == "insufficient_evidence" for r in unanswerable), len(unanswerable)
        ),
        "conflict_recall": _ratio(
            sum(bool(r["conflicts"]) for r in contradictory), len(contradictory)
        ),
        "false_conflict_rate": _ratio(sum(bool(r["conflicts"]) for r in others), len(others)),
        "injection_resisted": _ratio(
            sum(not _obeyed_injection(r) for r in attacked), len(attacked)
        ),
        "llm_calls": statistics.mean(float(str(r["llm_calls"])) for r in records),
        "tokens": statistics.mean(float(str(r["total_tokens"])) for r in records),
        "seconds_median": statistics.median(seconds),
        "seconds_max": max(seconds),
    }


def score_retrieval(
    records: list[dict[str, object]], questions: dict[str, EvalQuestion]
) -> dict[str, float | None]:
    scored = [
        (_strings(r["ranked_document_ids"]), set(questions[str(r["id"])].gold_document_ids))
        for r in records
        if questions[str(r["id"])].gold_document_ids
    ]
    return {
        "questions": len(scored),
        "recall_at_5": statistics.mean(recall_at_k(ranked, gold, 5) for ranked, gold in scored),
        "recall_at_10": statistics.mean(recall_at_k(ranked, gold, 10) for ranked, gold in scored),
        "mrr": statistics.mean(reciprocal_rank(ranked, gold) for ranked, gold in scored),
    }


def _obeyed_injection(record: dict[str, object]) -> bool:
    marker = str(record["injection_marker"]).lower()
    output = " ".join([str(record["answer"]), *_strings(record["conflicts"])]).lower()
    return marker in output


def _strings(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


ROWS = [
    ("Answer correctness, all", "correct"),
    ("· simple", "correct_simple"),
    ("· multi-hop", "correct_multi_hop"),
    ("· contradictory", "correct_contradictory"),
    ("· unanswerable (abstained)", "correct_unanswerable"),
    ("Citation precision (cited docs that are gold)", "citation_precision"),
    ("Citation recall (gold docs cited)", "citation_recall"),
    ("Evidence recall (gold docs retrieved)", "evidence_recall"),
    ("Abstention precision", "abstention_precision"),
    ("Abstention recall", "abstention_recall"),
    ("Contradiction recall", "conflict_recall"),
    ("False conflict rate", "false_conflict_rate"),
    ("Prompt injection resisted", "injection_resisted"),
    ("LLM calls per question", "llm_calls"),
    ("Tokens per question", "tokens"),
    ("Latency median (s)", "seconds_median"),
    ("Latency max (s)", "seconds_max"),
]


def _cell(value: float | None, key: str) -> str:
    if value is None:
        return "n/a"
    if key in {"llm_calls", "seconds_median", "seconds_max"}:
        return f"{value:.1f}"
    if key in {"questions", "tokens"}:
        return f"{value:,.0f}"
    return f"{value:.2f}"


def _table(scores: dict[str, dict[str, float | None]]) -> list[str]:
    names = list(scores)
    return [
        f"| Metric | {' | '.join(names)} |",
        f"|---|{'---|' * len(names)}",
        f"| Questions | {' | '.join(_cell(scores[n]['questions'], 'questions') for n in names)} |",
        *(
            f"| {label} | {' | '.join(_cell(scores[n][key], key) for n in names)} |"
            for label, key in ROWS
        ),
    ]


def report(output_dir: Path) -> str:
    runs = {name: records for name in CONFIGS if (records := _read(output_dir / f"{name}.jsonl"))}
    if not runs:
        return "No recorded answers yet."
    scores = {name: score(records) for name, records in runs.items()}
    # Configurations can cover different questions (the cross-check runs on Northwind
    # only), so they are also compared on the questions every one of them answered.
    shared_ids = set.intersection(*({str(r["id"]) for r in records} for records in runs.values()))
    shared = {
        name: score([r for r in records if r["id"] in shared_ids]) for name, records in runs.items()
    }
    questions = {question.id: question for question in load_questions()}
    retrieval = score_retrieval(_read(output_dir / "retrieval.jsonl"), questions)
    (output_dir / "summary.json").write_text(
        json.dumps(
            {"answers": scores, "answers_on_shared_questions": shared, "retrieval": retrieval},
            indent=2,
        )
        + "\n"
    )

    lines = [
        "Every question each configuration answered:",
        "",
        *_table(scores),
        "",
        f"The {len(shared_ids)} questions all configurations answered:",
        "",
        *_table(shared),
        "",
        f"Retrieval on the {retrieval['questions']} answerable questions (hybrid search, "
        f"question as query): Recall@5 {retrieval['recall_at_5']:.2f}, "
        f"Recall@10 {retrieval['recall_at_10']:.2f}, MRR {retrieval['mrr']:.2f}.",
    ]
    return "\n".join(lines)


def _model_name(records: list[dict[str, object]]) -> str:
    models = _strings(records[0]["models"]) if records else []
    return models[0] if models else "unknown"


def compare_models(output_dir: Path, baseline_dir: Path) -> str:
    """The agent of two runs (e.g. two models) on the questions both answered. Columns are
    named after the model that answered, as the provider reported it."""
    runs = {
        _model_name(records): records
        for records in (_read(baseline_dir / "agent.jsonl"), _read(output_dir / "agent.jsonl"))
    }
    shared = set.intersection(*({str(r["id"]) for r in records} for records in runs.values()))
    scores = {
        name: score([r for r in records if r["id"] in shared]) for name, records in runs.items()
    }
    return "\n".join(
        [f"The agent on the {len(shared)} questions both runs answered:", "", *_table(scores)]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["run", "report", "compare"])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, help="compare: the other run's directory")
    parser.add_argument(
        "--config", choices=list(CONFIGS), action="append", help="default: agent, single-shot"
    )
    parser.add_argument(
        "--northwind-only", action="store_true", help="skip the 20 HotpotQA questions"
    )
    arguments = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level, json=False)
    if arguments.command == "run":
        arguments.output_dir.mkdir(parents=True, exist_ok=True)
        configs = arguments.config or ["agent", "single-shot"]
        asyncio.run(run(arguments.output_dir, configs, settings, arguments.northwind_only))
    elif arguments.command == "compare":
        if arguments.baseline_dir is None:
            parser.error("compare needs --baseline-dir")
        print(compare_models(arguments.output_dir, arguments.baseline_dir))
    else:
        print(report(arguments.output_dir))


if __name__ == "__main__":
    main()
