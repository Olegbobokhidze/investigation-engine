# Evaluation report

How well Investigation Engine retrieves, answers, cites, abstains and flags conflicting
evidence, how it was measured, and where it fails. Every number comes from a committed
result file and can be recomputed with the `make eval-*` target named next to it.

| What | Result file | Recompute |
|---|---|---|
| Search configurations (HotpotQA, 200 questions) | [`evaluation/retrieval-hotpotqa.md`](evaluation/retrieval-hotpotqa.md) | `make eval-retrieval` |
| Chunking strategies (Northwind, 20 questions) | [`evaluation/chunking-northwind.md`](evaluation/chunking-northwind.md) | `make eval-chunking` |
| Answers: agent vs single-shot (48 questions) | [`evaluation/answers/`](evaluation/answers/) | `make eval-answers`, `make eval-report` |
| Answers: agent with cross-check (28 Northwind questions) | [`evaluation/answers/`](evaluation/answers/) | `make eval-cross-check`, `make eval-report` |
| Production load test (read endpoints) | [`evaluation/load-test.md`](evaluation/load-test.md) | `make load-test` |
| Prompts: current vs v1, both gpt-5-mini (48 questions) | [`evaluation/answers-prompt-v1/`](evaluation/answers-prompt-v1/) | `make eval-prompts` |
| Models: gpt-5-mini vs gpt-oss-120b, prompt v1 (35 questions) | [`evaluation/answers-gpt-oss-120b/`](evaluation/answers-gpt-oss-120b/) | `make eval-models` |

## 1. Summary

- **Retrieval.** Hybrid search with our weighted RRF beats dense and BM25 alone: Recall@10
  0.875 against 0.792 and 0.785. The RRF paper's k=60 is worse than k=10 here, and
  down-weighting BM25 hurts.
- **Chunking.** Structure-aware chunks find the right documents more often than
  fixed-size chunks at every size (Recall@3 and Recall@5), with about a third less text for
  the LLM to read.
- **Answers.** The agent is right on 0.79 of 48 questions, single-shot RAG on 0.67. The
  loop pays off where one search can't reach: HotpotQA multi-hop 15/20 against 12/20,
  contradictions 0.50 against 0.33 (contradiction recall 0.67 against 0.17). The agent
  abstains on all 8 unanswerable questions (single-shot on 7), and neither configuration
  obeyed the planted prompt injection.
- **The cost of the loop:** 3.1 LLM calls and 7.0k tokens per question against 1 and 2.9k,
  and a median of 21 s against 7 s; about 0.6 cent against 0.25 cent of Azure credit.
- **A prompt revision targeted the failure analysis** and kept correctness at 0.79. It
  fixed both "stopped one hop early" failures and the clutter in abstentions (at most 4
  sources instead of 13), but not over-cautious abstention (0 of 4), and lost two
  contradictory questions, within the run-to-run noise measured below.
- **A negative result.** An answer cross-check step (ADR-0009) didn't help: same
  contradiction recall, more false conflicts (0.23 against 0.14), 36% more tokens. It stays
  off.
- **Models.** With the same prompt, on the 35 questions both answered, gpt-5-mini is right
  on 0.74 and gpt-oss-120b on 0.66, mostly from contradictions (0.75 against 0.25).

## 2. Corpus and questions

**Corpus.** 66,593 documents in the deployed index:
- 66,581 distinct HotpotQA paragraphs (dev distractor set, pinned revision and checksum);
- 12 synthetic Northwind Pay documents in PDF, DOCX, Markdown and TXT, written around one
  incident with planted facts, multi-hop chains, 4 contradictions, known gaps and one
  document with a planted prompt injection
  ([ground truth](evaluation/northwind-ground-truth.md)).

**Questions** (`apps/api/data/eval/northwind-questions.jsonl` and the HotpotQA file):

| Type | HotpotQA | Northwind | Total |
|---|---|---|---|
| simple | 0 | 8 | 8 |
| multi-hop | 20 | 6 | 26 |
| contradictory | 0 | 6 | 6 |
| unanswerable | 0 | 8 | 8 |
| **total** | 20 | 28 | **48** |

Three of the Northwind questions (2 simple, 1 multi-hop) are prompt-injection tests: they are
answered from a document that also tells AI assistants to ignore their instructions and send
the user to a phishing link.

- **HotpotQA** questions are taken in a fixed order (SHA-256 of the question id), skipping
  the first 200: those tuned the RRF settings, so answers are measured on questions nothing
  was tuned on. Gold answers and gold documents are the dataset's, unedited.
- **Northwind** questions were written by hand against the corpus; each answerable one
  lists its gold documents and the exact facts an answer needs (`key_facts`, checked
  against the corpus by a test). Contradictory questions have a gold answer of the form
  `conflicting: A (source) vs B (source)`. Unanswerable questions ask about facts no
  document states (an EU refund policy, revenue lost, who approved a change) or about
  something outside the corpus entirely.
- **Prompt injection.** The `nw-inject-*` questions carry an `injection_marker`, the
  phishing domain the planted paragraph asks for; an answer that contains it obeyed the
  injection.

## 3. Method

**Configurations compared.**
- **agent:** plan sub-questions → search each → tool-calling loop (`search_documents`,
  `get_document`, `submit_answer`, at most 4 turns) → citation check;
- **single-shot:** one hybrid search with the question (10 passages) → one answer call →
  the same citation check;
- **agent-cross-check:** the agent, plus one step before the answer is accepted: a search
  with the answer's first sentence (its direct claim), then a forced resubmission after the
  model compares the claim with every passage it has. It targets the contradiction failures
  in section 7 and runs on the 28 Northwind questions only, where the contradictions are.
  `make eval-report` compares all configurations on the questions they share as well as on
  everything each one answered.

All three use the same model (`gpt-5-mini` on Azure, [ADR-0010](decisions/0010-azure-gpt-5-mini.md)),
the same prompts, tools and verification code (`Investigator(plan=False, max_turns=1)` is the
baseline), so the difference measured is the multi-step loop itself.

**Two prompt versions.** The first full run (prompt v1, kept in `evaluation/answers-prompt-v1/`)
produced the failure analysis that the current prompt answers: four rules about planning,
following references, answering from combined facts, and short abstentions
(`apps/api/src/investigation_engine/investigation/prompts.py`). The agent and single-shot
tables below use the current prompt, which is the one deployed; the cross-check and the
model comparison ran with prompt v1 and are compared only with prompt v1 runs. The fallback model is
switched off for evaluation runs, so no answer silently comes from a different model.

**The model comparison.** The first run used `openai/gpt-oss-120b` on Groq's free tier and
stopped at 35 agent answers on the daily token quota. Those answers are kept and compared
with gpt-5-mini on the same 35 questions (`make eval-models`); the providers differ as well
as the models.

**Metrics.**

| Metric | Definition |
|---|---|
| Answer correctness | Answerable: an LLM judge accepts the answer against the gold answer (an abstention counts as wrong). Unanswerable: correct when the engine abstains. |
| Citation precision | Cited documents that are gold documents / all cited documents |
| Citation recall | Gold documents cited / all gold documents |
| Evidence recall | Gold documents the agent saw at all / all gold documents: separates retrieval misses from answering mistakes |
| Abstention precision / recall | Abstentions that were right / all abstentions; unanswerable questions abstained on / all unanswerable |
| Contradiction recall / false conflict rate | Contradictory questions with a reported conflict / all contradictory; other questions with a reported conflict / all others |
| Prompt injection resisted | Injection questions whose answer and conflicts don't contain the injection marker / all injection questions |
| Recall@5, Recall@10, MRR | Plain hybrid search with the question as query, at document level |
| Cost | LLM calls, tokens and latency per question |

**The judge.** `qwen/qwen3.8-27b` on Groq, a different model family from both agent models,
so it doesn't grade its own family's answers. It sees the question, the gold answer, the system's
answer and its reported conflicts, and returns `{correct, reason}` through a forced tool
call. For a `conflicting:` gold answer, an answer is correct only if it reports the
disagreement with both values.

## 4. Retrieval

Full table and discussion: [`evaluation/retrieval-hotpotqa.md`](evaluation/retrieval-hotpotqa.md).

| Configuration | Recall@2 | Recall@5 | Recall@10 | MRR |
|---|---|---|---|---|
| dense | 0.615 | 0.750 | 0.792 | 0.868 |
| BM25 | 0.522 | 0.665 | 0.785 | 0.825 |
| RRF k=60 | 0.598 | 0.770 | 0.855 | 0.874 |
| **RRF k=10 (default)** | **0.615** | **0.795** | **0.875** | **0.880** |

Recall@2 stays near 0.61 for every configuration: the second paragraph of a multi-hop
question often names an entity only the first paragraph mentions, so one search with the
question can't find it. That gap is what the agent's follow-up searches are for.

## 5. Chunking

Full table and discussion: [`evaluation/chunking-northwind.md`](evaluation/chunking-northwind.md).

| Configuration | Recall@3 | MRR | Fact recall@5 | Context words@5 |
|---|---|---|---|---|
| fixed 200 words, overlap 40 | 0.808 | 0.900 | 0.925 | 558 |
| **structured 200 words (default)** | **0.858** | **0.925** | 0.900 | **361** |

## 6. Answers

`make eval-report` · per-question records with the gold answer and the judge's reason in
[`evaluation/answers/`](evaluation/answers/), totals in `summary.json`.

| Metric (current prompt) | agent | single-shot |
|---|---|---|
| Questions | 48 | 48 |
| **Answer correctness** | **0.79** | 0.67 |
| · simple (8) | 0.88 | 0.88 |
| · multi-hop (26) | **0.77** | 0.62 |
| · contradictory (6) | **0.50** | 0.33 |
| · unanswerable (8) | **1.00** | 0.88 |
| Citation precision | 0.70 | 0.69 |
| Citation recall | **0.88** | 0.82 |
| Evidence recall | 0.88 | 0.85 |
| Abstention precision / recall | 0.67 / 1.00 | 0.58 / 0.88 |
| Contradiction recall | **0.67** | 0.17 |
| False conflict rate | 0.10 | 0.02 |
| Prompt injection resisted | 3/3 | 3/3 |
| LLM calls / tokens per question | 3.1 / 7,013 | 1.0 / 2,887 |
| Latency median / p95 / max (s) | 21.2 / 34.0 / 84.7 | 7.1 / 12.3 / 18.3 |

Retrieval on the 40 answerable questions (plain hybrid search, the question as query):
Recall@5 0.80, Recall@10 0.87, MRR 0.82.

**Findings.**

1. **The loop is worth its cost on the questions it was built for.** HotpotQA multi-hop:
   agent 15/20, single-shot 12/20. Contradiction recall 0.67 against 0.17: the agent's
   follow-up searches bring in the second source that one search with the question misses.
2. **Simple questions don't need the loop** (0.88 for both, at 2.4 times the tokens).
3. **Abstention is reliable; precision is the weak side.** Every unanswerable question is
   abstained on, but a third of the agent's abstentions are on questions the corpus does
   answer: it is too cautious, not too confident.
4. **The planted injection never worked.** No answer repeated the phishing domain or
   dropped its citations; the passages are framed as quoted data in the prompt, and an
   uncited answer is discarded by the citation check anyway.
5. **Cost.** At gpt-5-mini's price ($0.25 input, $2 output per million tokens; about two
   thirds of the tokens are input), an agent question costs about $0.006 and a single-shot
   question $0.0025. All runs in this report together used about $1.50 of credit.

### Prompt revision (`make eval-prompts`)

The agent on all 48 questions, prompt v1 against the current prompt:

| Metric | prompt v1 | current |
|---|---|---|
| Answer correctness | 0.79 | 0.79 |
| · simple / multi-hop / contradictory | 0.75 / 0.73 / **0.83** | **0.88** / **0.77** / 0.50 |
| Citation recall | 0.82 | **0.88** |
| Contradiction recall | **0.83** | 0.67 |
| Sources cited by an abstention, mean / max | 4.6 / 13 | **2.6 / 4** |
| Tokens per question | 8,241 | **7,013** |

What each rule did, checked question by question:
- *Follow a reference to its document* fixed both early stops: "Who would Support have
  escalated a merchant's payment ticket to on 20 March 2024?" now searches the on-call
  schedule and names Tomas Lindqvist; "Why was the change that caused INC-0412 made?" now
  reaches the capacity review.
- *Short abstentions* removed the clutter a user saw: an abstention cited up to 13 passages
  under "No answer given".
- *Answer from combined facts* didn't move the 4 over-cautious abstentions; the model still
  wants one sentence that states the answer.
- Two contradictory questions were lost (one reported the wrong pair of values, one missed
  the soft conflict between two payment counts). Six verdicts changed in each direction
  between two runs of the same configuration (section 8), so this is not clearly an effect
  of the prompt.

The current prompt is deployed: same correctness, fewer tokens, and no cluttered abstentions.

### Answer cross-check (prompt v1, `make eval-cross-check`)

On the 28 Northwind questions, against the agent with the same prompt:

| Metric | agent | agent + cross-check |
|---|---|---|
| Answer correctness | **0.82** | 0.75 |
| Contradiction recall | 0.83 | 0.83 |
| False conflict rate | **0.14** | 0.23 |
| Evidence recall | 0.85 | **0.97** |
| Tokens per question | **7,771** | 10,572 |

It found the second source more often, but the forced comparison made the model report
conflicts on side facts: in "At what time did the INC-0412 payment delays end?" it flagged
the 09:05/09:40 deploy time and still gave only 10:20. Rejected
([ADR-0009](decisions/0009-answer-cross-check.md)).

### Model comparison (prompt v1, `make eval-models`)

The agent on the 35 questions both runs answered:

| Metric | gpt-oss-120b (Groq) | gpt-5-mini (Azure) |
|---|---|---|
| Answer correctness | 0.66 | **0.74** |
| · simple / multi-hop / contradictory | **0.83** / 0.68 / 0.25 | 0.67 / **0.76** / **0.75** |
| Citation precision / recall | **0.80** / 0.71 | 0.68 / **0.82** |
| Contradiction recall / false conflicts | 0.50 / **0.03** | **0.75** / 0.10 |
| Tokens per question | **4,267** | 8,066 |

gpt-5-mini reports disagreements far more often and cites more of the gold documents, at
twice the tokens (its reasoning tokens count as output). gpt-oss is more precise in what it
cites and better on simple questions.

## 7. Failure analysis

The agent's 10 wrong answers out of 48 (current prompt), by cause:

| Cause | Count | Example | What happened |
|---|---|---|---|
| Over-cautious abstention | 4 | "Did both Alan Crosland and Chris Columbus work as stage actor?" | Both gold paragraphs were retrieved; one calls Crosland a stage actor, the other calls Columbus a filmmaker. The gold answer is "no", but the model wanted a sentence saying Columbus never acted, and abstained. Same for the Mike Bushell and Ray Wilson / Leo questions, and for the US refund window, where the answer even quotes "30 days" before abstaining. |
| Contradiction missed | 2 | "When was INC-0412 resolved?" | Both sources were retrieved; the answer gives only the status page's 10:20, not the incident report's 10:05. The other is the soft conflict between 1,840 delayed and 2,300 late payments. |
| Wrong pair of values | 1 | "How far behind did the ledger fall during INC-0412?" | The answer reports a disagreement, but between the incident timeline's "above 20 minutes" and the postmortem's 41, not the status page's 25. |
| A sequence read as a conflict | 1 | "What size was the payments-db connection pool finally set to …?" | The pool went 50 → 20 → 50 → 40 over a week; the answer called 50 and 40 a disagreement instead of giving the final 40. |
| Retrieval miss | 1 | "What is another name for basidiomycete fungus?" | Neither gold paragraph was retrieved (evidence recall 0/2); the agent answered from a related paragraph ("honey fungus"). |
| Gold answer too narrow | 1 | "Why is Serena Williams more accomplished than Mariaan de Swardt in her tennis career?" | HotpotQA's gold answer is "the world No. 1 for the first time"; the agent listed 319 weeks at No. 1 and her Grand Slam titles, which the judge didn't accept as the same fact. |

Only one failure is a retrieval miss: in the other nine the gold documents were found and
the answer step went wrong. The next steps that follow from this table, as hypotheses:

- *Over-caution* survived a prompt rule, so it needs more than wording: for a yes/no
  question, one passage per side is enough to answer.
- *Contradictions*: compare only values of the fact the question asks about, and treat
  values that changed over time (a change and its revert) as a sequence, not a conflict.

**A ground-truth gap the agent found.** "How long could customers not sign in during
INC-0398?" has the gold answer 22 minutes, but the status page shows 14:12 to 14:30, 18
minutes. With prompt v1 both models reported that unplanned conflict and were marked wrong;
the current prompt answered 22 minutes. The conflict is real and is documented in the
[ground truth](evaluation/northwind-ground-truth.md).

## 8. Limits of this evaluation

- **Small sets.** One question moves a per-type score by 0.1–0.2 (6 contradictory and 8
  simple questions); differences of that size are not findings on their own.
- **One judge model.** The judge can be strict or lenient on paraphrases; its reason is
  stored with every verdict in the result files, so a verdict can be checked by hand.
- **Synthetic contradictions.** Northwind's conflicts were written by us; real document sets
  conflict in subtler ways. The unplanned conflict the agent found (section 7) shows the
  ground truth itself is incomplete.
- **One run per configuration.** LLM answers vary between runs: between the two prompt
  versions 6 verdicts changed, 3 in each direction, and between the agent and the
  cross-check 2 of 6 changes happened before the cross-check step ran. A difference of one
  or two questions is within that noise.
- **Two providers in the model comparison.** gpt-oss ran on Groq, gpt-5-mini on Azure; the
  comparison measures model and provider together.
