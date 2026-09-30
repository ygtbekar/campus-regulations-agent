# Performance

5 representative questions, one fresh conversation each, model `nvidia/nemotron-3-super-120b-a12b` on the NVIDIA NIM free tier.

**Median latency: 15.1 s** · **4552 tokens per question on average**

| question type | latency | model calls | prompt tokens | completion tokens | sources |
|---|---|---|---|---|---|
| regulation lookup | 15.1 s | 2 | 4527 | 606 | MADDE 22 |
| regulation lookup | 21.1 s | 2 | 4547 | 1031 | MADDE 31 |
| regulation + tool | 27.1 s | 2 | 4617 | 1527 | MADDE 31 |
| tool only | 7.0 s | 3 | 4015 | 226 | — |
| out of scope | 7.3 s | 1 | 1212 | 451 | — |

Most of the latency is the reasoning model thinking before it answers; each tool call adds a round trip, and the retrieved articles make the prompt grow. A smaller model would be faster and cheaper, which is the trade-off to measure next.
