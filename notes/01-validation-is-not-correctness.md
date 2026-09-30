# Experiment 01 — Validation guarantees form, not correctness

**Date:** 2026-09-18
**Model:** `nvidia/nemotron-3-super-120b-a12b` (NVIDIA NIM), `temperature=0`
**Setup:** `structured.py` — Pydantic schema + validators + retry loop (max 3 attempts), answering from a short FICTIONAL regulation text given in the prompt.

## Baseline (`MAX_ANSWER_CHARS = 400`)

All 3 questions valid on the first attempt:
- Answerable question → correct answer, cited `MADDE 13`.
- Two-part question → combined two articles, cited `MADDE 12` and `MADDE 13`.
- Question NOT covered by the text (summer school) → `found_in_regulation: false`, no citations, confidence `low`.

Compare with [Experiment 00](00-baseline-without-rag.md): the same model invented rules when asked without a source text. Giving it the text, telling it to use only that, and enforcing the output shape in code turned fabrication into an explicit "not found".

## Stress test (`MAX_ANSWER_CHARS = 60`)

The retry loop fired for the first time:

```
✗ attempt 1: rejected → String should have at most 60 characters
✓ attempt 2: valid
```

Every final answer **passed validation** — but look at what was lost:

| Regulation says | 60-char answer | Lost |
|---|---|---|
| Can withdraw until week 10 **with advisor approval** | "Evet, 10. haftaya kadar çekilebilir; transkriptte W." | The advisor-approval condition |
| At most 4 withdrawals **over the whole degree** | "Ekle-bıraktan sonra eklenemez;max 4 çekilebilir." | Scope of the limit (per term? total?) |

A student acting on these answers could drop a course without approval, or assume 4 withdrawals per term.

## Takeaways

1. **Validators check shape, not truth.** JSON valid, length OK, citation real — and still a misleading answer.
2. **Over-tight constraints make models "pass the test" by dropping information.** The constraint was satisfied at the cost of a critical condition.
3. Correctness and completeness need a separate **evaluation** step (Phase 4): compare answers against expected facts, not just against a schema.
4. Keep 400 chars: short enough to stay focused, long enough to keep conditions.
