# Campus Regulations Agent

An AI assistant that answers students' questions about the METU Northern Cyprus Campus
undergraduate regulation, **shows the article it relied on**, and says *"I could not find this"*
instead of guessing.

> Unofficial student project. The binding text is the regulation itself.
> Built as an application project for the YTU Startup House × NVIDIA AI Engineer Bootcamp.

## Why

Asked without a source, the model invents university rules. Same question, three runs, three
different sets of rules — [experiment 00](notes/00-baseline-without-rag.md):

> *"Bu dönemde sınırsız sayıda ders bırakabilirsiniz (akademik ceza yoktur)."*
> — "You can drop unlimited courses this semester (there is no academic penalty)."

The real regulation (Article 22) puts **five** restrictions on withdrawal: it happens in the tenth
week, one course per semester, six in total, never from first-year courses, never from repeated
courses. A student planning around the model's answer would be in trouble.

For rules, a confident wrong answer is worse than no answer.

## What it does

```
Student: Birinci sınıftayım, bu dönem bir dersten çekilebilir miyim?

  💭 Düşünüyor...
  📚 Yönetmelikte aranıyor...

Asistan: MADDE 22'ye göre dersten çekilme işlemi yarıyılın onuncu haftası içinde yapılır;
bir yarıyılda en çok bir, öğrenim boyunca en çok altı dersten çekilebilirsiniz. Ancak
müfredatın ilk iki yarıyılındaki derslerden çekilme yapılamaz. Birinci sınıf öğrencisi
olduğunuz için bu dönem bir dersten çekilemezsiniz.
  📄 Kaynak: MADDE 22 – Dersten çekilme
```

- **Grounded answers** — every claim comes from the retrieved article, in Turkish or English.
- **Verified citations** — an article number is shown only if the search really returned it in that
  conversation. Citations recalled from the model's memory are rejected and rewritten.
- **Refusals** — cafeteria hours, dormitories and clubs are not in the regulation, and the agent
  says so instead of inventing an answer.
- **Deterministic tools** — GPA and date arithmetic run in Python, not in the model.

## Measured results

Evaluation set: **28 questions**, three of them written by an actual METU NCC student
([questions.json](data/eval/questions.json)), in three categories — answerable from the
regulation, partially answerable (the regulation defers to the Senate or the academic calendar),
and out of scope.

**Retrieval** — does the search surface the article that answers the question?
([full table](data/eval/retrieval_results.md))

| embedding model | index | Turkish questions | English questions |
|---|---|---|---|
| `nemotron-3-embed-1b` | tr+en | hit@1 42% · hit@4 79% | hit@1 88% · hit@4 100% |
| **`llama-nemotron-embed-vl-1b-v2`** | **tr+en** | **hit@1 88% · hit@4 100%** | **hit@1 88% · hit@4 100%** |
| `llama-nemotron-embed-vl-1b-v2` | tr only | hit@1 88% · hit@4 100% | hit@1 75% · hit@4 88% |
| `llama-nemotron-embed-vl-1b-v2` | en only | hit@1 58% · hit@4 79% | hit@1 88% · hit@4 100% |

Two decisions came out of this table: the embedding model (the alternative was half as accurate on
Turkish) and keeping both languages in the index (each single-language index loses accuracy for
questions asked in the other language).

<!-- AGENT_RESULTS -->

## How it works

```
question → agent loop ─┬─► search_regulations → Chroma (94 chunks: 47 articles × 2 languages)
                       ├─► calculate_gpa       → deterministic Python
                       └─► days_until          → deterministic Python
                       ↓
              final answer as JSON {answer, sources}
                       ↓
     validation: schema · citations were actually retrieved · no foreign script
                       ↓          ↳ invalid → feed the error back, retry
                    answer + the article it rests on
```

The agent loop is written directly rather than with a framework: call the model, run the tools it
asks for, feed the results back, repeat until it answers — with a step limit, and a final
tools-disabled call so partial work is not thrown away.

[**docs/HOW-IT-WORKS.md**](docs/HOW-IT-WORKS.md) covers the design decisions, what each one cost,
and the known limitations.

## Experiment notes

The build was driven by experiments, and the failures are documented too:

| Note | Finding |
|---|---|
| [00 — baseline](notes/00-baseline-without-rag.md) | Without sources: three runs, three different invented rule sets |
| [01 — validation is not correctness](notes/01-validation-is-not-correctness.md) | A tight length limit produced answers that passed every check while dropping a condition of the rule |
| [02 — embedding model choice](notes/02-embedding-model-choice.md) | One model ranked the English version of the correct article below an unrelated sentence |
| [03 — first grounded answers](notes/03-first-grounded-answers.md) | Grounded answers work; a stray Korean character appeared at temperature 0, so the validator now checks for it |

## Running it

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env          # then paste your free key from https://build.nvidia.com
```

```bash
.venv\Scripts\python.exe ingest.py             # download the regulation, split it by article
.venv\Scripts\python.exe retrieval.py --rebuild # embed and index it
```

```bash
.venv\Scripts\python.exe agent.py   # terminal
.venv\Scripts\streamlit.exe run app.py         # web interface
```

Evaluation:

```bash
.venv\Scripts\python.exe eval_retrieval.py     # search quality
.venv\Scripts\python.exe eval_agent.py         # end-to-end, graded by a second model
```

## Files

| File | Role |
|---|---|
| `agent.py` | Agent loop, answer schema, citation validation |
| `tools.py` | Tools the model may call, and their schemas |
| `retrieval.py` | Embedding, Chroma index, bilingual search |
| `ingest.py` | Downloads the regulation and splits it into articles |
| `app.py` | Streamlit interface |
| `eval_retrieval.py` / `eval_agent.py` | The two evaluations |
| `chat.py`, `structured.py`, `hello_nim.py` | Build-up steps kept for reference |
| `data/regulations/` | Source texts (TR + EN) with URL, date and checksum |
| `notes/` | Experiment notes |

## Stack

Python 3.12 · NVIDIA NIM (`nemotron-3-super-120b-a12b` for chat, `llama-nemotron-embed-vl-1b-v2`
for embeddings, `gpt-oss-20b` as evaluation judge) · Chroma · Pydantic · Streamlit.

The LLM calls use the OpenAI-compatible API, so the provider can be swapped by changing a base URL.
