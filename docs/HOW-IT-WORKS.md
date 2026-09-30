# How it works

A walk through the system, the decisions behind it and what each decision cost.

## The problem

Ask a general-purpose LLM "how many courses can I withdraw from at METU NCC?" and it answers
confidently — and wrongly. In [the first experiment of this project](../notes/00-baseline-without-rag.md)
the same question was asked three times and produced three different sets of rules
("unlimited", "no penalty", "at least 12 credits"). The actual regulation has five separate
restrictions on withdrawal.

For a student, a confident wrong answer is worse than no answer: they plan around it.

## The pipeline

```
question
   │
   ▼
agent loop (agent.py) ──────────────────────────────────────────────┐
   │  the model decides which tools to call                         │
   ├─► search_regulations → retrieval.py → Chroma → 4 articles      │
   ├─► calculate_gpa      → deterministic Python                    │
   ├─► days_until         → deterministic Python                    │
   │                                                                │
   ▼                                                                │
final answer as JSON {answer, sources}                              │
   │                                                                │
   ▼                                                                │
validation: schema · citations must have been retrieved · script check
   │        └─ invalid → tell the model what was wrong, retry ──────┘
   ▼
answer + the article it rests on
```

## Ingestion (`ingest.py`)

The source is the official METU NCC Undergraduate Education Regulation, fetched from the
university's own site in **both Turkish and English**. `data/regulations/sources.json` records the
URL, the retrieval date and a SHA-256 hash of each page, so a later change to the source is
detectable.

The regulation was updated in 2026 (it repeals the 2015 regulation, Articles 45–46). An assistant
serving an outdated version would be worse than no assistant: it would cite a real article number
for a rule that no longer applies.

**Chunking: one chunk per article.** A regulation is already divided into self-contained rules.
Fixed-size chunking would cut a rule away from its conditions — exactly the failure mode this
project is trying to avoid — and it would leave chunks without a citable identity. One article per
chunk also makes citations verifiable: an article number either exists in the document or it does not.

## Retrieval (`retrieval.py`)

Each article is embedded with an NVIDIA NIM embedding model and stored in Chroma (94 chunks:
47 articles × 2 languages). A question is embedded the same way, and cosine similarity finds the
closest articles.

Embeddings match meaning rather than words: the Turkish question *"Bir dönemde kaç dersi
**bırakabilirim**?"* retrieves the article titled *"Dersten **çekilme**"*, which shares no keyword
with the question.

Two decisions here were measured, not guessed — see [Retrieval evaluation](../data/eval/retrieval_results.md):

| Decision | Evidence |
|---|---|
| `llama-nemotron-embed-vl-1b-v2` over `nemotron-3-embed-1b` | hit@1 88% vs 42% on Turkish questions |
| Index both languages | Turkish-only drops English questions to hit@4 88%; English-only drops Turkish questions to 79%; both give 100% either way |
| Return the **Turkish** text as the citation | The Turkish text is the one published in the Official Gazette; the English page is a translation |
| No similarity threshold | The correct article sometimes scores only slightly above a wrong one (0.358 vs 0.348). A threshold would create false negatives; deciding relevance is left to the model, which sees four candidates |

Results from both language versions are merged by article number, so the model never spends two of
its four slots on the same rule.

## The agent loop (`agent.py`)

Written directly rather than with a framework:

```
repeat at most MAX_STEPS times:
    call the model with the conversation and the tool definitions
    append its reply to the conversation
    if it requested tools: run them, append each result, continue
    otherwise: validate the final answer and return it
```

The model never executes anything. It emits a request (`finish_reason: tool_calls`); the Python code
runs the function and returns the result as a `role: "tool"` message.

Deterministic work is deliberately kept out of the model: GPA is computed in Python from the
coefficient table in Article 24(5), and date arithmetic uses the system clock. The model decides
*when* to compute, not *what the result is*.

**Failure handling, all of it learned from watching the system break:**

| Behaviour observed | Response |
|---|---|
| Free-tier API returns "Service temporarily overloaded" | Caught; the unfinished turn is removed so the conversation stays consistent |
| Tool called with a bad argument (`15.01.2027`) | Tools return errors as data, so the model can read the message and retry |
| Step limit reached with useful tool results already gathered | One final call with `tool_choice="none"`: answer with what you have, instead of discarding it |
| Reasoning model returns an empty visible answer, everything in its hidden thinking field | Detected and retried |
| A stray Korean character appeared mid-sentence at temperature 0 | Validator rejects CJK/Hangul characters and asks for a rewrite |

## Validation: the part that makes it trustworthy

The final reply is a JSON object matching a Pydantic schema. Three checks run before anything
reaches the student:

1. **Schema** — it parses, and the fields have the right types.
2. **Citations are real** — every article in `sources` must have been returned by
   `search_regulations` *in this conversation*. A model that recalls "Article 99" from memory is
   blocked here, which is the single most dangerous failure mode for this product: a fabricated
   citation looks more trustworthy than a plain hallucination.
3. **Script check** — no characters from other writing systems.

A failed check is not a crash. The error message is fed back to the model, which corrects itself;
up to `MAX_STEPS` attempts.

Note what validation does *not* do. In [experiment 01](../notes/01-validation-is-not-correctness.md)
a 60-character answer limit produced answers that passed every check while dropping a condition of
the rule ("with advisor approval"). Validation constrains form; only evaluation measures substance.

## Evaluation (`eval_retrieval.py`, `eval_agent.py`)

28 questions (`data/eval/questions.json`), three of them written by an actual METU NCC student,
in three categories:

- **in_scope** — the regulation answers it.
- **partial** — the regulation addresses the topic but defers the detail to the Senate or the
  academic calendar. The right answer cites the article *and* says the detail is not here.
- **out_of_scope** — cafeteria hours, dormitories, clubs. The right answer is a refusal.

`eval_retrieval.py` grades search alone (hit@1, hit@4) across models and language setups.
`eval_agent.py` runs the whole agent per question and grades answers with a **different model
family** as judge (`openai/gpt-oss-20b`), so the system is not marking its own homework. Results:
[agent_results.md](../data/eval/agent_results.md).

Out-of-scope questions are graded on refusal, because an assistant that answers everything is
indistinguishable from one that invents things.

## What was deliberately not built

- **No reranker.** The usual next step in a RAG pipeline, and a reasonable thing to reach for — but
  hit@4 is already 100% on the evaluation set, so there is nothing for a reranker to fix. Adding it
  would have added a model call per question and a dependency, for a measured gain of zero.
- **No academic calendar (yet).** The obvious next source: it would turn "when is add-drop?" from a
  pointer into an answer, and combined with `days_until` it could answer "how many days are left?".
  It was left out because it introduces a second citation type and a second validation rule, and the
  system was stable two days before the deadline. It is the first thing to add next.

## Known limitations

- **One document.** Only the undergraduate regulation. The academic calendar is not indexed, so
  date questions correctly point to it instead of answering.
- **Small evaluation set.** 28 questions catch systematic failures, not rare ones.
- **The judge is a model.** LLM-as-judge is consistent enough to compare versions, but it is not
  a human grader.
- **Unbounded conversation memory.** Long chats grow the context window; there is no summarisation
  or trimming yet.
- **Free-tier limits.** Rate limits and occasional overload errors; handled, but they slow the
  evaluation runs.
- **Not official.** The binding text is the regulation itself; this is a student project.
