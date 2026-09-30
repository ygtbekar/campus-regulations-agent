# Retrieval evaluation

24 questions with a known correct article (in_scope + partial), top-4 after merging the two language versions.

| embedding model | question asked in | languages indexed | hit@1 | hit@4 |
|---|---|---|---|---|
| `nemotron-3-embed-1b` | TR | tr | 42% | 79% |
| `nemotron-3-embed-1b` | TR | en | 33% | 67% |
| `nemotron-3-embed-1b` | TR | tr+en | 42% | 79% |
| `nemotron-3-embed-1b` | EN | tr | 58% | 88% |
| `nemotron-3-embed-1b` | EN | en | 88% | 100% |
| `nemotron-3-embed-1b` | EN | tr+en | 88% | 100% |
| `llama-nemotron-embed-vl-1b-v2` | TR | tr | 88% | 100% |
| `llama-nemotron-embed-vl-1b-v2` | TR | en | 58% | 79% |
| `llama-nemotron-embed-vl-1b-v2` | TR | tr+en | 88% | 100% |
| `llama-nemotron-embed-vl-1b-v2` | EN | tr | 75% | 88% |
| `llama-nemotron-embed-vl-1b-v2` | EN | en | 88% | 100% |
| `llama-nemotron-embed-vl-1b-v2` | EN | tr+en | 88% | 100% |

**Best configuration (worst case across question languages):** `llama-nemotron-embed-vl-1b-v2` with **tr+en** — hit@1 ≥ 88%, hit@4 ≥ 100%.

