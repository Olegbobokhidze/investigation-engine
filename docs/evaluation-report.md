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
| Models: gpt-5-mini vs gpt-oss-120b (35 questions) | [`evaluation/answers-gpt-oss-120b/`](evaluation/answers-gpt-oss-120b/) | `make eval-models` |

## 1. Summary

- **Retrieval.** Hybrid search with our weighted RRF beats dense and BM25 alone: Recall@10
  0.875 against 0.792 and 0.785. The RRF paper's k=60 is worse than k=10 here, and
  down-weighting BM25 hurts.
- **Chunking.** Structure-aware chunks find the right documents more often than
  fixed-size chunks at every size (Recall@3 and Recall@5), with about a third less text for
  the LLM to read.
- **Answers.** The agent is right on 0.79 of 48 questions, single-shot RAG on 0.65. The
  loop pays off where one search can't reach: HotpotQA multi-hop 15/20 against 11/20, and
  contradictions 0.83 against 0.33. The agent abstains on all 8 unanswerable questions
  (single-shot on 7), and neither configuration obeyed the planted prompt injection.
- **The cost of the loop:** 3.5 LLM calls and 8.2k tokens per question against 1 and 3.0k,
  and a median of 23 s against 9 s; about 0.7 cent against 0.25 cent of Azure credit.
- **A negative result.** The answer cross-check (ADR-0009) didn't help: same contradiction
  recall (0.83), more false conflicts (0.23 against 0.14) and 36% more tokens. It stays off.
- **Models.** On the 35 questions both answered, gpt-5-mini is right on 0.74 and
  gpt-oss-120b on 0.66, mostly from contradictions (0.75 against 0.25).

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
baseline), so the difference measured is the multi-step loop itself. The fallback model is
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

`make eval-report` · per-question records with the judge's reason in
[`evaluation/answers/`](evaluation/answers/), totals in `summary.json`.

| Metric | agent | single-shot | agent + cross-check¹ |
|---|---|---|---|
| Questions | 48 | 48 | 28 |
| **Answer correctness** | **0.79** | 0.65 | 0.75 (agent on the same 28: 0.82) |
| · simple (8) | 0.75 | 0.88 | 0.50 |
| · multi-hop (26) | 0.73 | 0.58 | 1.00 |
| · contradictory (6) | **0.83** | 0.33 | 0.50 |
| · unanswerable (8) | **1.00** | 0.88 | 1.00 |
| Citation precision | 0.70 | 0.68 | 0.75 |
| Citation recall | 0.82 | 0.81 | 0.97 |
| Evidence recall | 0.85 | 0.85 | 0.97 |
| Abstention precision / recall | 0.67 / 1.00 | 0.54 / 0.88 | 0.73 / 1.00 |
| Contradiction recall | **0.83** | 0.50 | 0.83 |
| False conflict rate | 0.10 | 0.05 | 0.23 |
| Prompt injection resisted | 3/3 | 3/3 | 3/3 |
| LLM calls / tokens per question | 3.5 / 8,241 | 1.0 / 2,960 | 4.5 / 10,572 |
| Latency median / max (s) | 22.9 / 71.5 | 9.3 / 15.3 | 28.2 / 48.6 |

¹ Northwind questions only; the per-type rows have 2–8 questions each there.

Retrieval on the 40 answerable questions (plain hybrid search, the question as query):
Recall@5 0.80, Recall@10 0.87, MRR 0.82.

**Findings.**

1. **The loop is worth its cost on the questions it was built for.** HotpotQA multi-hop:
   agent 15/20, single-shot 11/20. Contradictions: 0.83 against 0.33, because the agent's
   follow-up searches bring in the second source that one search with the question misses
   (contradiction recall 0.83 against 0.50).
2. **Single-shot is better on simple questions** (0.88 against 0.75). With one fact to
   find, the planner's extra sub-questions add noise: the agent's two simple misses are an
   abstention after the plan wandered off (section 7) and the unplanned conflict.
3. **Abstention is reliable; precision is the weak side.** Every unanswerable question is
   abstained on, but a third of the agent's abstentions are on questions the corpus does
   answer: it is too cautious, not too confident.
4. **The planted injection never worked.** No answer repeated the phishing domain or
   dropped its citations; the passages are framed as quoted data in the prompt, and an
   uncited answer is discarded by the citation check anyway.
5. **The cross-check is rejected** ([ADR-0009](decisions/0009-answer-cross-check.md)). It
   found the right second source more often (evidence recall 0.97, citation recall 0.97) but
   the forced comparison made the model report conflicts on side facts: in "At what time did
   the INC-0412 payment delays end?" it flagged the 09:05/09:40 deploy time and still gave
   only 10:20. Contradiction recall stayed at 0.83, false conflicts rose to 0.23.
6. **Cost.** At gpt-5-mini's price ($0.25 input, $2 output per million tokens; about two
   thirds of the tokens are input), an agent question costs about $0.007 and a single-shot
   question $0.0025. The whole evaluation, all three configurations, used about $1 of credit.

**Model comparison** (`make eval-models`, agent configuration, the 35 questions both runs
answered):

| Metric | gpt-oss-120b (Groq) | gpt-5-mini (Azure) |
|---|---|---|
| Answer correctness | 0.66 | **0.74** |
| · simple / multi-hop / contradictory | 0.83 / 0.68 / 0.25 | 0.67 / 0.76 / **0.75** |
| Citation precision / recall | **0.80** / 0.71 | 0.68 / **0.82** |
| Contradiction recall / false conflicts | 0.50 / 0.03 | **0.75** / 0.10 |
| Tokens per question | **4,267** | 8,066 |

gpt-5-mini reports disagreements far more often, and cites more of the gold documents, at
twice the tokens (its reasoning tokens count as output). gpt-oss is more precise in what it
cites and better on simple questions.

## 7. Failure analysis

The agent's 10 wrong answers out of 48, by cause:

| Cause | Count | Example | What happened |
|---|---|---|---|
| Over-cautious abstention | 3 | "Did both Alan Crosland and Chris Columbus work as stage actor?" | Both gold paragraphs were retrieved; the model wanted an explicit statement for the second person and abstained. Same for the Mike Bushell and Ray Wilson / Leo questions. |
| Plan left the corpus | 1 | "Within how many days of a payment can a US customer request a refund?" | The planner asked about US federal law and chargeback rules instead of the policy; the answer then abstained because no passage covered the law, although the policy (30 days) was retrieved. |
| Stopped one hop early | 2 | "Who would Support have escalated a merchant's payment ticket to on 20 March 2024?" | The handbook says "the primary on-call engineer of that week"; the agent answered with that phrase and never searched the on-call schedule for the name (Tomas Lindqvist). "Why was the change that caused INC-0412 made?" stopped at the change log the same way. |
| Contradiction missed | 1 | "When was INC-0412 resolved?" | Both sources were retrieved; the answer gives only the status page's 10:20, not the incident report's 10:05. |
| Retrieval miss | 1 | "What is another name for basidiomycete fungus?" | Neither gold paragraph was retrieved (evidence recall 0/2); the agent answered from a related paragraph ("honey fungus"). |
| Gold answer too narrow | 1 | "Why is Serena Williams more accomplished than Mariaan de Swardt in her tennis career?" | HotpotQA's gold answer is "the world No. 1 for the first time"; the agent listed 319 weeks at No. 1 and her Grand Slam titles, which the judge didn't accept as the same fact. |
| Ground-truth gap | 1 | "How long could customers not sign in during INC-0398?" | The agent reported 22 minutes (incident report) against 18 minutes (status page, 14:12 to 14:30). The conflict is real but wasn't planted, so the gold answer "22 minutes" marks it wrong. Both models found it. |

**What would fix them.** The two largest groups point at the prompt, not at retrieval
(evidence recall is 0.85 and every gold document was seen in 6 of the 10 failures):

- *Over-cautious abstention and early stops* both come from the answer step. A rule that
  says "answer the part the passages support and name what is missing" instead of
  abstaining, and "if a passage refers to another document for the answer (a schedule, a
  review), search for it before answering", targets 5 of the 10.
- *A plan that leaves the corpus* would be caught by telling the planner to search for the
  question's own terms first.

These are hypotheses for the next run, not results.

## 8. Limits of this evaluation

- **Small sets.** One question moves a per-type score by 0.1–0.2 (6 contradictory and 8
  simple questions); differences of that size are not findings on their own.
- **One judge model.** The judge can be strict or lenient on paraphrases; its reason is
  stored with every verdict in the result files, so a verdict can be checked by hand.
- **Synthetic contradictions.** Northwind's conflicts were written by us; real document sets
  conflict in subtler ways. The unplanned conflict the agent found (section 7) shows the
  ground truth itself is incomplete.
- **One run per configuration.** LLM answers vary between runs: on the 28 questions the
  agent and the cross-check share, 6 verdicts differ, and 2 of those changes have nothing to
  do with the cross-check step (the model abstained earlier in the loop). A difference of one
  or two questions is within that noise.
- **Two providers in the model comparison.** gpt-oss ran on Groq, gpt-5-mini on Azure; the
  comparison measures model and provider together.
