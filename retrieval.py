"""Semantic search over the regulation (the "R" in RAG).

Build the index once:   python retrieval.py --rebuild
Try some searches:      python retrieval.py
"""
import json
import os
import sys
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ROOT = Path(__file__).parent
REGULATION_DIR = ROOT / "data" / "regulations"
CHROMA_DIR = ROOT / "data" / "chroma"  # git-ignored: it can always be rebuilt from the JSON files

EMBED_MODEL = "nvidia/llama-nemotron-embed-vl-1b-v2"  # chosen in notes/02-embedding-model-choice.md
COLLECTION = "metu_ncc_undergrad_2026"
DOCUMENTS = {  # language -> file produced by ingest.py
    "tr": "metu-ncc-undergrad-2026-tr.json",
    "en": "metu-ncc-undergrad-2026-en.json",
}
AUTHORITATIVE_LANGUAGE = "tr"  # the Turkish text is the one published in the Official Gazette

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1", api_key=os.getenv("NVIDIA_API_KEY"), max_retries=5
)


def load_articles(language: str) -> list[dict]:
    return json.loads((REGULATION_DIR / DOCUMENTS[language]).read_text(encoding="utf-8"))


def embed(texts: list[str], input_type: str, model: str = EMBED_MODEL) -> list[list[float]]:
    """input_type is "passage" for documents and "query" for questions (the model treats them differently)."""
    vectors = []
    for start in range(0, len(texts), 16):  # small batches keep us under the free-tier rate limit
        response = client.embeddings.create(
            model=model,
            input=texts[start:start + 16],
            extra_body={"input_type": input_type, "truncate": "END"},
        )
        vectors += [item.embedding for item in response.data]
    return vectors


def get_collection():
    db = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # cosine distance: 0 = same meaning, 2 = opposite
    return db.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def build_index() -> None:
    db = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if COLLECTION in [c.name for c in db.list_collections()]:
        db.delete_collection(COLLECTION)
    collection = get_collection()

    for language in DOCUMENTS:
        articles = load_articles(language)
        texts = [f"{a['title']}\n{a['text']}" for a in articles]
        print(f"Embedding {len(texts)} {language.upper()} articles...")
        collection.add(
            ids=[f"{language}-{a['number']}" for a in articles],
            embeddings=embed(texts, "passage"),
            documents=texts,
            metadatas=[{"language": language, "article": a["number"], "title": a["title"]} for a in articles],
        )
    print(f"✓ Index built: {collection.count()} chunks in {CHROMA_DIR}")


_authoritative = {a["number"]: a for a in load_articles(AUTHORITATIVE_LANGUAGE)}


def article_title(number: int) -> str:
    return _authoritative[number]["title"]


def article_text(number: int) -> str:
    return _authoritative[number]["text"]


def search_regulations(query: str, k: int = 4) -> list[dict]:
    """Return the k most relevant articles. Both languages are searched, but each article
    appears once and always with its authoritative Turkish text."""
    collection = get_collection()
    if collection.count() == 0:
        raise RuntimeError("The index is empty. Run: python retrieval.py --rebuild")

    hits = collection.query(query_embeddings=embed([query], "query"), n_results=k * 2)

    best = {}  # article number -> best similarity found in either language
    for metadata, distance in zip(hits["metadatas"][0], hits["distances"][0]):
        number, similarity = metadata["article"], 1 - distance
        if similarity > best.get(number, -1):
            best[number] = similarity

    results = []
    for number, similarity in sorted(best.items(), key=lambda item: -item[1])[:k]:
        article = _authoritative[number]
        results.append({
            "article": f"MADDE {number}",
            "title": article["title"],
            "text": article["text"],
            "similarity": round(similarity, 3),
        })
    return results


if __name__ == "__main__":
    if "--rebuild" in sys.argv:
        build_index()

    for question in [
        "Bir dönemde kaç dersi bırakabilirim?",
        "Mezun olmak için not ortalamam en az kaç olmalı?",
        "Sınamalı öğrenci ne demek?",
        "Derslere devam zorunlu mu?",
        "Yemekhane saat kaçta açılıyor?",  # not in the regulation
    ]:
        print(f"\nSoru: {question}")
        for result in search_regulations(question, k=3):
            print(f"  {result['similarity']:.3f}  {result['article']} – {result['title']}")
