"""How long does an answer take, and what does it cost?

    python bench.py

Accuracy is not the only production metric. This measures wall-clock latency, the number of model
calls and the tokens spent per question, on a small representative sample.
"""
import json
import statistics
import time
from pathlib import Path

import agent

RESULTS_FILE = Path(__file__).parent / "data" / "eval" / "performance.md"

SAMPLE = [
    ("regulation lookup", "Bir dersten çekilmek istiyorum, ne zaman yapabilirim?"),
    ("regulation lookup", "Mezun olabilmek için genel not ortalamam en az kaç olmalı?"),
    ("regulation + tool", "Notlarım 3 kredi CC, 4 kredi DD, 3 kredi CB. Mezuniyet şartını sağlıyor muyum?"),
    ("tool only", "2 Ekim 2026'ya kaç gün kaldı?"),
    ("out of scope", "Kampüs yemekhanesi saat kaçta açılıyor?"),
]


def measure(question: str) -> dict:
    calls = {"count": 0, "prompt_tokens": 0, "completion_tokens": 0}
    original_create = agent.client.chat.completions.create

    def counting_create(**kwargs):
        response = original_create(**kwargs)
        calls["count"] += 1
        if response.usage:
            calls["prompt_tokens"] += response.usage.prompt_tokens
            calls["completion_tokens"] += response.usage.completion_tokens
        return response

    agent.client.chat.completions.create = counting_create
    try:
        started = time.perf_counter()
        messages = [{"role": "system", "content": agent.SYSTEM_PROMPT}, {"role": "user", "content": question}]
        answer = agent.run_agent(messages, set())
        seconds = time.perf_counter() - started
    finally:
        agent.client.chat.completions.create = original_create

    return {"seconds": round(seconds, 1), "model_calls": calls["count"],
            "prompt_tokens": calls["prompt_tokens"], "completion_tokens": calls["completion_tokens"],
            "sources": answer.sources}


def main() -> None:
    rows = []
    for kind, question in SAMPLE:
        print(f"· {question[:60]}...")
        measurement = measure(question)
        rows.append({"kind": kind, "question": question, **measurement})
        print(f"    {measurement['seconds']}s | {measurement['model_calls']} model calls | "
              f"{measurement['prompt_tokens']}+{measurement['completion_tokens']} tokens")

    median_seconds = statistics.median(row["seconds"] for row in rows)
    total_tokens = sum(row["prompt_tokens"] + row["completion_tokens"] for row in rows)

    lines = ["# Performance", "",
             f"{len(rows)} representative questions, one fresh conversation each, "
             f"model `{agent.MODEL}` on the NVIDIA NIM free tier.", "",
             f"**Median latency: {median_seconds:.1f} s** · "
             f"**{total_tokens / len(rows):.0f} tokens per question on average**", "",
             "| question type | latency | model calls | prompt tokens | completion tokens | sources |",
             "|---|---|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['kind']} | {row['seconds']} s | {row['model_calls']} | "
                     f"{row['prompt_tokens']} | {row['completion_tokens']} | "
                     f"{', '.join(row['sources']) or '—'} |")
    lines += ["",
              "Most of the latency is the reasoning model thinking before it answers; each tool call "
              "adds a round trip, and the retrieved articles make the prompt grow. A smaller model "
              "would be faster and cheaper, which is the trade-off to measure next."]
    RESULTS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nMedian {median_seconds:.1f}s · avg {total_tokens / len(rows):.0f} tokens/question")
    print(f"✓ Wrote {RESULTS_FILE}")


if __name__ == "__main__":
    main()
