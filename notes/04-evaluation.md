# Experiment 04 — Measuring the assistant, and what the numbers changed

**Date:** 2026-09-30
**Evaluation set:** 28 questions ([questions.json](../data/eval/questions.json)), three of them
written by a METU NCC student. Categories: `in_scope` (the regulation answers it), `partial`
(the regulation mentions the topic but defers the detail to the Senate or the academic calendar),
`out_of_scope` (not in the regulation at all).
**Judge:** `openai/gpt-oss-20b` — a different model family from the one being graded, so the system
is not marking its own homework.

## Part 1 — Retrieval

Two embedding models × three index setups × questions asked in Turkish and in English
([full table](../data/eval/retrieval_results.md)):

| model | index | TR questions hit@4 | EN questions hit@4 |
|---|---|---|---|
| `nemotron-3-embed-1b` | tr+en | 79% | 100% |
| **`llama-nemotron-embed-vl-1b-v2`** | **tr+en** | **100%** | **100%** |
| `llama-nemotron-embed-vl-1b-v2` | tr only | 100% | 88% |
| `llama-nemotron-embed-vl-1b-v2` | en only | 79% | 100% |

Two things came out of this:

1. The model chosen in [experiment 02](02-embedding-model-choice.md) from a single query holds up
   over 24 questions: hit@1 88% vs 42% on Turkish questions.
2. **The reason for indexing both languages was wrong, even though the decision was right.** The
   guess was that the English text would help Turkish questions. It does not — `tr` and `tr+en`
   score identically for Turkish. What it does is serve students who ask in English, where a
   Turkish-only index drops to 88%. METU is an English-medium university, so this matters.

## Part 2 — End to end, version 1

| metric | v1 |
|---|---|
| Answer fully correct | 17/24 |
| Answer correct or partially correct | 23/24 |
| Cited the expected article | 21/24 |
| Refused an out-of-scope question | 3/4 |
| Invented a citation | **0/28** |

Reading the failures mattered more than the score. Three patterns, and one mistake of my own:

**a) Incompleteness (5 of the 7 non-perfect answers).** The answers were true but dropped
conditions. Asked how many courses may be dropped in total, the agent answered "six" and omitted
the one-per-semester limit. Asked about the minimum graduation average, it gave 2,00 and omitted
that every course must be passed with at least DD. This is not hallucination — it is
[experiment 01](01-validation-is-not-correctness.md) again: valid output, misleading substance.

**b) Missing citations on `partial` questions (3 cases).** For resit exams and double majors the
agent correctly said "the regulation leaves this to the Senate" but cited nothing, so a student
could not check the claim.

**c) One out-of-scope leak.** Asked how to join a student club, the agent answered from its own
knowledge about club fairs and sign-up forms instead of refusing. Nothing in the regulation covers
clubs. This is the failure mode the whole project exists to prevent.

**d) My answer key was wrong for q02.** The agent was marked wrong for saying that summer-school
course offerings are decided by the program coordinators — which is exactly what Article 7(5)
says. The expected answer had only captured Article 7(2). Fixed the key, not the agent.

## Part 3 — One change, re-measured

Only the system prompt changed: be complete (state every condition of the cited rule), cite the
article even when the regulation defers the detail elsewhere, and never answer campus-life
questions from memory.

### v2: six fixed, two broken

| id | v1 | v2 |
|---|---|---|
| q07, q08, q12, q16, q17 | partial (incomplete) | **correct** |
| q22, q23, q24 | correct but uncited | **cited** |
| q27 (student clubs) | answered from memory | **refused** |
| q23 (double major) | correct | **wrong** — presented Article 10's definition as if it were the admission conditions |
| q26 (dormitories) | refused cleanly | **wrong** — cited Articles 21 and 39 because they contain the word "yurt" in a list of fees |

Both regressions came from the same over-correction: "cite the article" pushed the model to find
*something* to cite, even when the regulation only mentions the topic in passing. A useful reminder
that prompt changes are not local — they alter behaviour on questions you were not thinking about.

### Final: separate "the regulation defers this" from "the regulation does not cover this"

Two clauses were sharpened: when the regulation defers a detail, say that first and only then quote
what it does say; and when the regulation does not govern the topic at all, refuse and cite nothing —
never cite an article merely because it contains the word.

| metric | v1 | final |
|---|---|---|
| Answer correct | 17/24 | **24/24** |
| Answer correct or partial | 23/24 | 24/24 |
| Cited the expected article | 21/24 | **24/24** |
| Refused an out-of-scope question | 3/4 | **4/4** |
| Invented a citation | 0/28 | **0/28** |

One blemish remains, and it is worth stating rather than hiding: asked for a specific course's exam
date (q28), the agent correctly says the regulation does not contain exam dates and points to the
academic calendar — but cites Article 23 ("Attendance and examinations") while doing so. The answer
is right; the citation is over-eager.

## What this says about the method

- Counting correct answers alone would have been useless. The categories (`in_scope` / `partial` /
  `out_of_scope`) are what turned "71% correct" into three specific, fixable defects.
- The main defect was **incompleteness, not hallucination** — answers that were true but dropped a
  condition. Reading five answers by hand would not have revealed it; they all look fine.
- Fixing six questions broke two. Without a regression set the second effect would have shipped
  unnoticed.
- An evaluation set is also a test of the person who wrote it: one of the 28 expected answers was
  wrong, and only the disagreement revealed it.

- The guardrail that blocks invented citations held: zero fabricated sources across all three runs.
  A validator that never fires proves nothing — but this one did fire during the runs, and the model
  corrected itself each time.

Raw results per version: [v1](../data/eval/agent_results_v1.md) ·
[v2](../data/eval/agent_results_v2.md) · [final](../data/eval/agent_results.md).
