# Experiment 02 — Choosing an embedding model for a bilingual (TR/EN) regulation

**Date:** 2026-09-22
**Documents:** official METU NCC Undergraduate Regulation (2026), Turkish and English versions, one chunk per article.
**Question:** students will ask in Turkish. Should we index Turkish, English, or both — and which embedding model?

## Setup

- Queries — TR: "Bir dönemde kaç dersi bırakabilirim?" / EN: "How many courses can I withdraw from in one semester?"
- Correct answer: Article 22 (course withdrawal). Distractors: Articles 30 (probation), 31 (graduation) and an unrelated sentence about the cafeteria.
- Cosine similarity between query and passage embeddings (`input_type` = query / passage).
- Only two NIM embedding models were available to this free-tier account; the others returned 404.

## Results

| Model | TR query → TR Art. 22 | EN query → EN Art. 22 | TR query → **EN** Art. 22 |
|---|---|---|---|
| `nvidia/nemotron-3-embed-1b` | 0.26 (rank 1, weak margin) | **0.70** | 0.09 — below the unrelated cafeteria sentence (0.10) ❌ |
| `nvidia/llama-nemotron-embed-vl-1b-v2` | **0.40** (rank 1) | 0.57 | 0.26 — above unrelated passages ✓ |

Note that the TR query matched Article 22 even though it says "bırakmak" and the article says "çekilme": embeddings match meaning, not words.

## Decision (provisional)

- Use **`llama-nemotron-embed-vl-1b-v2`**: stronger on Turkish and it can bridge languages.
- Index **both** languages; merge results by article number; always cite the **Turkish** article, because the Turkish text published in the Official Gazette is the binding one (the English page is a translation).
- An English-only index would have failed the most basic Turkish question with `nemotron-3-embed-1b`.

**Caveat:** one query is an anecdote, not evidence. Re-check both models on the full eval set in Phase 4.
