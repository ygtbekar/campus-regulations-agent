"""Reproducible screenshots for the README.

Start the app first:
    .venv\\Scripts\\streamlit.exe run app.py --server.port 8501 --server.headless true
Then:
    .venv\\Scripts\\python.exe docs/make_screenshots.py

Requires: pip install playwright && playwright install chromium (development only).
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "img"
APP = "http://localhost:8501"

QUESTION = "Birinci sınıftayım, bu dönem bir dersten çekilebilir miyim?"
FOLLOW_UP = "Peki notlarım 3 kredi CC, 4 kredi DD, 3 kredi CB ise mezuniyet şartını sağlıyor muyum?"


def ask(page, question: str, timeout_ms: int = 240_000) -> None:
    page.get_by_placeholder("Örneğin").fill(question)
    page.keyboard.press("Enter")
    # Wait for the work to start and then to finish. Waiting for the "answer validated" label is
    # not enough: an earlier turn's label is still in the DOM, so it matches immediately.
    busy = ("/Düşünüyor|aranıyor|hesaplanıyor|bakılıyor|düzeltiliyor|Boş cevap|Adım sınırına/"
            ".test(document.body.innerText)")
    page.wait_for_function(f"() => {busy}", timeout=60_000)
    page.wait_for_function(f"() => !({busy})", timeout=timeout_ms)
    page.wait_for_timeout(2500)  # let Streamlit drop the stale elements from the previous run


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 860},
                                device_scale_factor=2, color_scheme="dark")

        # 1. the SVG diagram, rendered as PNG for readers whose viewer dislikes SVG
        page.set_viewport_size({"width": 880, "height": 470})
        page.goto((OUT / "architecture.svg").as_uri())
        page.wait_for_timeout(800)
        page.screenshot(path=OUT / "architecture.png")
        page.set_viewport_size({"width": 1280, "height": 860})

        # 2. the app answering a regulation question, with the cited article open
        page.goto(APP, wait_until="networkidle")
        page.wait_for_timeout(2500)
        ask(page, QUESTION)
        page.locator("summary", has_text="MADDE").first.click()  # open the cited article
        page.wait_for_timeout(1200)
        page.mouse.wheel(0, 600)
        page.wait_for_timeout(500)
        page.screenshot(path=OUT / "ui-answer.png")

        # 3. a follow-up that combines the regulation with the GPA tool
        ask(page, FOLLOW_UP)
        page.mouse.wheel(0, -4000)
        page.wait_for_timeout(800)
        page.screenshot(path=OUT / "ui-conversation.png", full_page=True)

        browser.close()

    for name in ("architecture.png", "ui-answer.png", "ui-conversation.png"):
        size = (OUT / name).stat().st_size
        print(f"✓ {name} ({size / 1024:.0f} KB)")


if __name__ == "__main__":
    sys.exit(main())
