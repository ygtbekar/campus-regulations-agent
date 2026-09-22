# Experiment 03 — First grounded answers from the real regulation

**Date:** 2026-09-22
**Setup:** `agent.py` with four tools (`search_regulations`, `calculate_gpa`, `days_until`, `get_today`), `nvidia/nemotron-3-super-120b-a12b` at `temperature=0`, bilingual Chroma index (`notes/02`). The final answer is JSON (`answer`, `sources`) and every cited article must have been returned by `search_regulations` in the same conversation.

## Results

| Question | Tools used | Answer | Verdict |
|---|---|---|---|
| "I'm a first-year student, can I withdraw from a course this term? How many in total?" | search | All five Art. 22 limits, **applied to the student**: first two semesters → cannot withdraw now; 1 per semester, 6 in total | ✅ cites MADDE 22 |
| "Minimum GPA to graduate? My grades: 3 cr CC, 4 cr DD, 3 cr CB" | search + GPA | Art. 31 requires ≥ 2,00; computed 1,75 → requirement not met | ✅ cites MADDE 31, math verified by hand |
| "When does the campus cafeteria open?" | none | "Could not find this" | ✅ no sources |
| "When is add-drop?" | search | Art. 21: dates are announced in the academic calendar | ✅ cites MADDE 21 |

Compare with [Experiment 00](00-baseline-without-rag.md): the same model, asked without sources, invented "first 2 weeks, unlimited drops". The real rules (Art. 21, 22) contradict that.

## Bug found: stray foreign-script token at temperature 0

The cafeteria answer contained a Korean character mid-word: *"mevcut **규**lamada bilgi bulamadım"*. Experiment 00 showed the same kind of leak (Japanese) at temperature 1.0 — this shows it also happens at temperature 0.

**Fix:** the final-answer validator now rejects answers containing CJK/Hangul characters, and the model rewrites them (same validate → feedback → retry loop as `structured.py`).

## Validator unit test (offline, no model calls)

| Input | Result |
|---|---|
| Answer with `규` | rejected → rewrite in Turkish |
| Correct answer citing a retrieved article | accepted |
| Citation of an article that was never retrieved (`MADDE 99`) | **rejected** — blocks invented citations |
| `"Madde 31"` (case difference) | accepted, normalized to `MADDE 31` |
| JSON wrapped in a code fence | accepted |

A validator should block real problems (invented sources, garbled text) without rejecting harmless format differences.
