"""Download the official METU NCC undergraduate regulation (EN + TR) and split it into articles.

Output (committed to the repo so results are reproducible):
  data/regulations/<id>.json   -> [{"number", "title", "part", "text"}, ...]
  data/regulations/<id>.md     -> human-readable copy
  data/regulations/sources.json -> where and when each document was fetched
"""
import hashlib
import json
import re
import urllib.request
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

OUT_DIR = Path(__file__).parent / "data" / "regulations"

SOURCES = [
    {
        "id": "metu-ncc-undergrad-2026-en",
        "title": "METU NCC Undergraduate Education Regulation (2026)",
        "language": "en",
        "url": "https://ncc.metu.edu.tr/ro/undergraduate-education-regulation",
        "article_word": "ARTICLE",
    },
    {
        "id": "metu-ncc-undergrad-2026-tr",
        "title": "ODTÜ KKK Lisans Eğitim Öğretim Yönetmeliği (2026)",
        "language": "tr",
        "url": "https://ncc.metu.edu.tr/tr/oim/lisans-yonetmeligi",
        "article_word": "MADDE",
    },
]

# "PART II" (EN) or "İKİNCİ BÖLÜM" (TR), followed by a line with the part's name.
PART_HEADER = re.compile(r"^(PART [IVXL]+|[A-ZÇĞİÖŞÜ]+ BÖLÜM)$")


def fetch_html(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (campus-regulations-agent student project)"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def extract_lines(html: bytes) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one("div.field-name-body")
    if body is None:
        raise RuntimeError("Regulation body not found; the page layout may have changed.")
    text = body.get_text("\n").replace("\xa0", " ")
    return [re.sub(r"\s+", " ", line).strip() for line in text.split("\n") if line.strip()]


def clean_article_text(fragments: list[str]) -> str:
    text = " ".join(fragments)
    text = re.sub(r"^[\s–-]+", "", text)                   # leading dash after "ARTICLE 1"
    text = re.sub(r"\s+\((\d+)\)\s*", r"\n(\1) ", text)    # each numbered paragraph on its own line
    return text.strip()


def split_articles(lines: list[str], article_word: str) -> list[dict]:
    """One chunk per article: a title line is always followed by an 'ARTICLE n' / 'MADDE n' line."""
    article_start = re.compile(rf"^{article_word}\s+(\d+)\b\s*(.*)$", re.IGNORECASE)
    articles, fragments, current, part = [], [], None, None

    def close_current():
        if current:
            current["text"] = clean_article_text(fragments)
            articles.append(current)

    i = 0
    while i < len(lines):
        line = lines[i]
        next_line = lines[i + 1] if i + 1 < len(lines) else ""
        if PART_HEADER.match(line):
            part = f"{line} – {next_line}"
            i += 2
            continue
        match = article_start.match(next_line)
        if match:  # `line` is the title of a new article
            close_current()
            current = {"number": int(match.group(1)), "title": line, "part": part}
            fragments = [match.group(2)]
            i += 2
            continue
        if current:
            fragments.append(line)
        i += 1
    close_current()

    numbers = [article["number"] for article in articles]
    if numbers != list(range(1, len(numbers) + 1)):
        raise RuntimeError(f"Articles are not numbered 1..N without gaps: {numbers}")
    return articles


def write_markdown(path: Path, source: dict, articles: list[dict], retrieved_at: str) -> None:
    lines = [f"# {source['title']}", "", f"Source: {source['url']} (retrieved {retrieved_at})", ""]
    for article in articles:
        lines += [f"## {source['article_word']} {article['number']} – {article['title']}", "", article["text"], ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    retrieved_at = date.today().isoformat()
    manifest = []
    for source in SOURCES:
        html = fetch_html(source["url"])
        articles = split_articles(extract_lines(html), source["article_word"])
        (OUT_DIR / f"{source['id']}.json").write_text(
            json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        write_markdown(OUT_DIR / f"{source['id']}.md", source, articles, retrieved_at)
        manifest.append({
            "id": source["id"],
            "title": source["title"],
            "language": source["language"],
            "url": source["url"],
            "retrieved_at": retrieved_at,
            "sha256": hashlib.sha256(html).hexdigest(),  # detect if the page changes later
            "articles": len(articles),
        })
        print(f"✓ {source['id']}: {len(articles)} articles")
    (OUT_DIR / "sources.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
