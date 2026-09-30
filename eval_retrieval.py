"""Measure retrieval quality: does the search find the article that actually answers the question?

    python eval_retrieval.py

Compares two NIM embedding models and three language setups (Turkish only, English only, both)
on the evaluation set in data/eval/questions.json.

Metrics
  hit@1 : the correct article is the top result
  hit@4 : the correct article is among the four articles the agent gets to read
"""
import json
from pathlib import Path

import chromadb

from retrieval import embed, load_articles

ROOT = Path(__file__).parent
QUESTIONS = json.loads((ROOT / "data" / "eval" / "questions.json").read_text(encoding="utf-8"))
EVAL_CHROMA = ROOT / "data" / "chroma_eval"  # separate from the production index
RESULTS_FILE = ROOT / "data" / "eval" / "retrieval_results.md"

MODELS = {
    "nemotron-3-embed-1b": "nvidia/nemotron-3-embed-1b",
    "llama-nemotron-embed-vl-1b-v2": "nvidia/llama-nemotron-embed-vl-1b-v2",
}
LANGUAGE_SETS = {"tr": ["tr"], "en": ["en"], "tr+en": ["tr", "en"]}
TOP_K = 4


def build_collection(db, key: str, model: str):
    name = f"eval_{key}".replace(".", "_")
    if name in [c.name for c in db.list_collections()]:
        return db.get_collection(name)
    collection = db.create_collection(name, metadata={"hnsw:space": "cosine"})
    for language in ("tr", "en"):
        articles = load_articles(language)
        texts = [f"{a['title']}\n{a['text']}" for a in articles]
        print(f"  embedding {len(texts)} {language.upper()} articles with {key}...")
        collection.add(
            ids=[f"{language}-{a['number']}" for a in articles],
            embeddings=embed(texts, "passage", model=model),
            metadatas=[{"language": language, "article": a["number"]} for a in articles],
        )
    return collection


def ranked_articles(collection, query_vector, languages: list[str], k: int) -> list[int]:
    """Query one or both language versions and merge duplicates by article number."""
    where = {"language": languages[0]} if len(languages) == 1 else None
    hits = collection.query(query_embeddings=[query_vector], n_results=k * 2, where=where)
    best: dict[int, float] = {}
    for metadata, distance in zip(hits["metadatas"][0], hits["distances"][0]):
        number, similarity = metadata["article"], 1 - distance
        best[number] = max(best.get(number, -1), similarity)
    return [number for number, _ in sorted(best.items(), key=lambda item: -item[1])][:k]


def main() -> None:
    graded = [q for q in QUESTIONS if q["expected_articles"]]
    out_of_scope = [q for q in QUESTIONS if not q["expected_articles"]]
    print(f"{len(graded)} graded questions, {len(out_of_scope)} out-of-scope questions\n")

    db = chromadb.PersistentClient(path=str(EVAL_CHROMA))
    rows = []
    for key, model in MODELS.items():
        print(f"== {key}")
        collection = build_collection(db, key, model)
        vector_of = {}
        for asked_in, field in (("TR", "question"), ("EN", "question_en")):
            vectors = embed([q[field] for q in QUESTIONS], "query", model=model)
            vector_of[asked_in] = dict(zip([q["id"] for q in QUESTIONS], vectors))

        for asked_in in ("TR", "EN"):
            for set_name, languages in LANGUAGE_SETS.items():
                hit1 = hit4 = 0
                misses = []
                for question in graded:
                    found = ranked_articles(collection, vector_of[asked_in][question["id"]], languages, TOP_K)
                    expected = set(question["expected_articles"])
                    if found and found[0] in expected:
                        hit1 += 1
                    if expected & set(found):
                        hit4 += 1
                    else:
                        misses.append(f"{question['id']} (bekleniyor {sorted(expected)}, bulundu {found})")
                rows.append({
                    "model": key,
                    "asked_in": asked_in,
                    "languages": set_name,
                    "hit@1": hit1 / len(graded),
                    "hit@4": hit4 / len(graded),
                    "misses": misses,
                })
                print(f"  soru {asked_in} | indeks {set_name:<6} hit@1 {hit1 / len(graded):.0%}"
                      f" | hit@4 {hit4 / len(graded):.0%}")

    # The best configuration must work for questions asked in EITHER language.
    def worst_case(model_key: str, set_name: str) -> tuple[float, float]:
        matching = [r for r in rows if r["model"] == model_key and r["languages"] == set_name]
        return min(r["hit@4"] for r in matching), min(r["hit@1"] for r in matching)

    configurations = {(r["model"], r["languages"]) for r in rows}
    best_key = max(configurations, key=lambda c: worst_case(*c))
    best = {"model": best_key[0], "languages": best_key[1],
            "hit@4": worst_case(*best_key)[0], "hit@1": worst_case(*best_key)[1],
            "misses": [m for r in rows if (r["model"], r["languages"]) == best_key for m in r["misses"]]}
    print(f"\nBest (worst case across question languages): {best['model']} / {best['languages']} "
          f"(hit@1 ≥ {best['hit@1']:.0%}, hit@4 ≥ {best['hit@4']:.0%})")

    lines = [
        "# Retrieval evaluation",
        "",
        f"{len(graded)} questions with a known correct article (in_scope + partial), "
        f"top-{TOP_K} after merging the two language versions.",
        "",
        "| embedding model | question asked in | languages indexed | hit@1 | hit@4 |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['model']}` | {row['asked_in']} | {row['languages']} "
            f"| {row['hit@1']:.0%} | {row['hit@4']:.0%} |"
        )
    lines += ["", f"**Best configuration (worst case across question languages):** `{best['model']}` "
                  f"with **{best['languages']}** — hit@1 ≥ {best['hit@1']:.0%}, hit@4 ≥ {best['hit@4']:.0%}.", ""]
    if best["misses"]:
        lines += ["Remaining misses (correct article not in top-4):", ""]
        lines += [f"- {miss}" for miss in best["misses"]]
    RESULTS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✓ Wrote {RESULTS_FILE}")


if __name__ == "__main__":
    main()
