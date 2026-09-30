"""End-to-end evaluation of the agent: is the answer correct, and does it cite the right article?

    python eval_agent.py

For every question in data/eval/questions.json the agent is run from a clean conversation.
A second model (a different family, so it is not grading its own work) compares the answer with
the expected facts. Out-of-scope questions are graded on whether the agent refuses instead of guessing.
"""
import json
import re
import time
from pathlib import Path

from openai import APIError

import agent

ROOT = Path(__file__).parent
QUESTIONS = json.loads((ROOT / "data" / "eval" / "questions.json").read_text(encoding="utf-8"))
RESULTS_MD = ROOT / "data" / "eval" / "agent_results.md"
RESULTS_JSON = ROOT / "data" / "eval" / "agent_results.json"

JUDGE_MODEL = "openai/gpt-oss-20b"

JUDGE_PROMPT = """You grade a university regulation assistant. Reply with ONLY a JSON object:
{{"verdict": "correct" | "partial" | "wrong", "reason": "<one short sentence>"}}

Question: {question}

Expected content: {expected}

Assistant's answer: {answer}

Grading rules:
- "correct": the answer conveys the expected content and adds nothing that contradicts it.
- "partial": the answer is on topic and not wrong, but misses part of the expected content.
- "wrong": the answer contradicts the expected content, invents rules, or fails to address it.
- For questions whose expected content says the topic is NOT covered by the regulation, the answer
  is "correct" only if it clearly says it could not find the information (optionally pointing
  elsewhere), and "wrong" if it states rules as if they were in the regulation."""


def judge(question: str, expected: str, answer: str) -> dict:
    response = agent.client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(
            question=question, expected=expected, answer=answer)}],
        temperature=0,
    )
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", (response.choices[0].message.content or "").strip())
    try:
        result = json.loads(raw)
        if result.get("verdict") in {"correct", "partial", "wrong"}:
            return result
    except json.JSONDecodeError:
        pass
    return {"verdict": "wrong", "reason": f"judge returned an unusable reply: {raw[:120]}"}


def ask_agent(question: str) -> agent.AgentAnswer:
    """Fresh conversation for every question, so answers cannot depend on earlier ones."""
    messages = [{"role": "system", "content": agent.SYSTEM_PROMPT}, {"role": "user", "content": question}]
    for attempt in range(3):
        try:
            return agent.run_agent(messages, set())
        except APIError as error:
            print(f"    API error ({error}); retrying in 10s")
            time.sleep(10)
            messages = messages[:2]
    return agent.AgentAnswer(answer="[agent failed after 3 attempts]")


def main() -> None:
    results = []
    for index, question in enumerate(QUESTIONS, start=1):
        print(f"[{index}/{len(QUESTIONS)}] {question['id']} {question['question'][:60]}...")
        answer = ask_agent(question["question"])
        verdict = judge(question["question"], question["key_facts"], answer.answer)

        cited = {int(source.split()[1]) for source in answer.sources}
        expected = set(question["expected_articles"])
        if question["type"] == "out_of_scope":
            citation_ok = not cited  # it must not cite anything
        else:
            citation_ok = bool(expected & cited)

        results.append({
            **{k: question[k] for k in ("id", "type", "question")},
            "expected_articles": sorted(expected),
            "answer": answer.answer,
            "sources": answer.sources,
            "verdict": verdict["verdict"],
            "reason": verdict["reason"],
            "citation_ok": citation_ok,
        })
        print(f"    → {verdict['verdict']:<8} sources={answer.sources or '[]'} citation_ok={citation_ok}")
        time.sleep(1)  # stay under the free-tier rate limit

    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    def rate(rows, predicate):
        return f"{sum(1 for r in rows if predicate(r))}/{len(rows)}" if rows else "0/0"

    answerable = [r for r in results if r["type"] != "out_of_scope"]
    refusals = [r for r in results if r["type"] == "out_of_scope"]
    summary = [
        ("Answer correct (correct)", answerable, lambda r: r["verdict"] == "correct"),
        ("Answer correct or partial", answerable, lambda r: r["verdict"] in {"correct", "partial"}),
        ("Cited the expected article", answerable, lambda r: r["citation_ok"]),
        ("Refused out-of-scope question", refusals, lambda r: r["verdict"] == "correct"),
        ("Cited nothing when out of scope", refusals, lambda r: r["citation_ok"]),
    ]

    lines = ["# End-to-end agent evaluation", "",
             f"{len(QUESTIONS)} questions ({len(answerable)} answerable, {len(refusals)} out of scope). "
             f"Judge model: `{JUDGE_MODEL}`.", "", "| metric | result |", "|---|---|"]
    print("\n=== SUMMARY ===")
    for label, rows, predicate in summary:
        value = rate(rows, predicate)
        lines.append(f"| {label} | {value} |")
        print(f"{label:<34} {value}")

    lines += ["", "## Per question", "",
              "| id | type | verdict | sources | question |", "|---|---|---|---|---|"]
    for row in results:
        lines.append(f"| {row['id']} | {row['type']} | {row['verdict']} | "
                     f"{', '.join(row['sources']) or '—'} | {row['question'][:70]} |")
    RESULTS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n✓ Wrote {RESULTS_MD}")


if __name__ == "__main__":
    main()
