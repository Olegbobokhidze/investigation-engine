# Evaluation report

How well Investigation Engine retrieves, answers, cites, abstains and flags conflicting
evidence, how it was measured, and where it fails. Every number comes from a committed
result file and can be recomputed with the `make eval-*` target named next to it.

| What | Result file | Recompute |
|---|---|---|
| Search configurations (HotpotQA, 200 questions) | [`evaluation/retrieval-hotpotqa.md`](evaluation/retrieval-hotpotqa.md) | `make eval-retrieval` |
| Chunking strategies (Northwind, 17 questions) | [`evaluation/chunking-northwind.md`](evaluation/chunking-northwind.md) | `make eval-chunking` |
| Answers: agent vs single-shot (45 questions) | [`evaluation/answers/`](evaluation/answers/) | `make eval-answers`, `make eval-report` |

## 1. Summary

- **Retrieval.** Hybrid search with our weighted RRF beats dense and BM25 alone: Recall@10
  0.875 against 0.792 and 0.785. The RRF paper's k=60 is worse than k=10 here, and
  down-weighting BM25 hurts.
- **Chunking.** Structure-aware chunks find the right documents more often than
  fixed-size chunks at every size, and give the LLM 35–40% less text for the same facts.
- **Answers.** *(Final table pending: the answer run is being completed.)* On the 11
  HotpotQA multi-hop questions both configurations have answered so far, the agent is right
  on 9 and single-shot RAG on 5.

## 2. Corpus and questions

**Corpus.** 66,592 documents in the deployed index:
- 66,581 distinct HotpotQA paragraphs (dev distractor set, pinned revision and checksum);
- 11 synthetic Northwind Pay documents in PDF, DOCX, Markdown and TXT, written around one
  incident with planted facts, multi-hop chains, 4 contradictions and known gaps
  ([ground truth](evaluation/northwind-ground-truth.md)).

**Questions** (`apps/api/data/eval/northwind-questions.jsonl` and the HotpotQA file):

| Type | HotpotQA | Northwind | Total |
|---|---|---|---|
| simple | 0 | 6 | 6 |
| multi-hop | 20 | 5 | 25 |
| contradictory | 0 | 6 | 6 |
| unanswerable | 0 | 8 | 8 |
| **total** | 20 | 25 | **45** |

- **HotpotQA** questions are taken in a fixed order (SHA-256 of the question id), skipping
  the first 200: those tuned the RRF settings, so answers are measured on questions nothing
  was tuned on. Gold answers and gold documents are the dataset's, unedited.
- **Northwind** questions were written by hand against the corpus; each answerable one
  lists its gold documents and the exact facts an answer needs (`key_facts`, checked
  against the corpus by a test). Contradictory questions have a gold answer of the form
  `conflicting: A (source) vs B (source)`. Unanswerable questions ask about facts no
  document states (an EU refund policy, revenue lost, who approved a change) or about
  something outside the corpus entirely.

## 3. Method

**Configurations compared.**
- **agent:** plan sub-questions → search each → tool-calling loop (`search_documents`,
  `get_document`, `submit_answer`, at most 4 turns) → citation check;
- **single-shot:** one hybrid search with the question (10 passages) → one answer call →
  the same citation check.

Both use the same model (`openai/gpt-oss-120b` on Groq), the same prompts, tools and
verification code (`Investigator(plan=False, max_turns=1)` is the baseline), so the
difference measured is the multi-step loop itself. The fallback model is switched off for
evaluation runs, so no answer silently comes from a different model.

**Metrics.**

| Metric | Definition |
|---|---|
| Answer correctness | Answerable: an LLM judge accepts the answer against the gold answer (an abstention counts as wrong). Unanswerable: correct when the engine abstains. |
| Citation precision | Cited documents that are gold documents / all cited documents |
| Citation recall | Gold documents cited / all gold documents |
| Evidence recall | Gold documents the agent saw at all / all gold documents: separates retrieval misses from answering mistakes |
| Abstention precision / recall | Abstentions that were right / all abstentions; unanswerable questions abstained on / all unanswerable |
| Contradiction recall / false conflict rate | Contradictory questions with a reported conflict / all contradictory; other questions with a reported conflict / all others |
| Recall@5, Recall@10, MRR | Plain hybrid search with the question as query, at document level |
| Cost | LLM calls, tokens and latency per question |

**The judge.** `qwen/qwen3.8-27b`, a different model family from the agent's gpt-oss, so it
doesn't grade its own family's answers. It sees the question, the gold answer, the system's
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
| fixed 200 words, overlap 40 | 0.804 | 0.912 | 0.912 | 556 |
| **structured 200 words (default)** | **0.863** | **0.941** | 0.882 | **354** |

## 6. Answers

*(Pending: the run stopped on the LLM provider's daily token quota and resumes when it
resets. The final table, per-type breakdown and cost comparison go here.)*

## 7. Failure analysis

*(Draft from the agent's first 35 answers; to be finalised with the full run.)*

| Failure | Example | What happened |
|---|---|---|
| Retrieval miss | "What is another name for basidiomycete fungus?" | Neither gold paragraph was retrieved (evidence recall 0/2); the agent answered from a related paragraph ("honey fungus") instead of the gold "Funki Porcini". |
| Facts found, not connected | "What English competitive sailor has Mike Bushell included top tips from?" | Both gold paragraphs were retrieved, but the agent abstained. |
| Stopped one hop early | "Why was the change that caused INC-0412 made?" | The answer cites the change log ("recommended by the Q1 capacity review") but never opens the capacity review, so the cost saving is missing. |
| Contradiction missed | "When was INC-0412 resolved?" | Both sources were retrieved; the answer gives only the status page's 10:20 and not the incident report's 10:05. |
| Unplanned contradiction found | "How long could customers not sign in during INC-0398?" | The agent reported 22 minutes (incident report) against 18 minutes (status page: 14:12 to 14:30). That conflict is real but wasn't planted, so the gold answer "22 minutes" marks it wrong: a ground-truth gap, not a model error. |
| Question wording | "Where Ken Kwapis and John Woo both working on films in the 1980's?" | The HotpotQA question is a yes/no question with a typo ("Where" for "Were"); the agent answered *where* they worked. |

## 8. Limits of this evaluation

- **Small sets.** One question moves a per-type score by 0.1–0.2 (6 questions per type for
  Northwind); differences of that size are not findings on their own.
- **One judge model.** The judge can be strict or lenient on paraphrases; its reason is
  stored with every verdict in the result files, so a verdict can be checked by hand.
- **Synthetic contradictions.** Northwind's conflicts were written by us; real document sets
  conflict in subtler ways. The unplanned conflict the agent found (section 7) shows the
  ground truth itself is incomplete.
- **Free-tier LLM.** Latency includes waits for the provider's per-minute token limit, so
  it overstates what a paid tier would show.
