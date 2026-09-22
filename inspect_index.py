"""Export the Chroma index to a readable Markdown table.

    python inspect_index.py
Then open data/chroma/index_preview.md in VS Code and press Ctrl+Shift+V for the preview.
"""
from pathlib import Path

from retrieval import get_collection

OUT = Path(__file__).parent / "data" / "chroma" / "index_preview.md"  # git-ignored with the index

collection = get_collection()
records = collection.get(include=["documents", "metadatas", "embeddings"])
rows = sorted(
    zip(records["ids"], records["metadatas"], records["documents"], records["embeddings"]),
    key=lambda row: (row[1]["article"], row[1]["language"]),
)
dimensions = len(rows[0][3]) if rows else 0

lines = [
    "# Chroma index preview",
    "",
    f"Collection `{collection.name}`: **{collection.count()} chunks**, "
    f"each stored as a vector of **{dimensions} numbers**.",
    "",
    "| id | lang | article | title | text (start) | vector (first 5 numbers) |",
    "|---|---|---|---|---|---|",
]
for chunk_id, metadata, document, vector in rows:
    body = document.split("\n", 1)[-1]  # the first line is the title
    preview = body[:90].replace("|", "\\|").replace("\n", " ") + "…"
    numbers = ", ".join(f"{float(x):+.3f}" for x in vector[:5])
    lines.append(
        f"| {chunk_id} | {metadata['language']} | {metadata['article']} | {metadata['title']} "
        f"| {preview} | [{numbers}, …] |"
    )

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"✓ Wrote {len(rows)} rows to {OUT}")
