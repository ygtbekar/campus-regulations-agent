import json
import os
import re
import sys
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, model_validator

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")
if not api_key:
    sys.exit("NVIDIA_API_KEY is empty. Paste your key into the .env file.")

client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key, max_retries=5)
MODEL = os.getenv("LLM_MODEL")

MAX_ANSWER_CHARS = 400
MAX_ATTEMPTS = 3

# FICTIONAL sample text, only for testing the output format.
# Real regulations will be collected in Phase 3.
REGULATION = """ÖRNEK ÜNİVERSİTESİ LİSANS YÖNETMELİĞİ (KURGUSAL TEST METNİ)

MADDE 12 – Ders ekleme ve bırakma
(1) Öğrenciler, akademik takvimde belirtilen ekle-bırak haftasında ders ekleyebilir veya bırakabilir.
(2) Ekle-bırak haftasından sonra ders eklenemez.

MADDE 13 – Dersten çekilme
(1) Öğrenci, dönemin 10. haftasının sonuna kadar danışman onayıyla bir dersten çekilebilir; transkriptte W notu görünür.
(2) Bir öğrenci öğrenimi süresince en fazla 4 dersten çekilebilir.

MADDE 14 – Devam
(1) Teorik derslerin %30'undan fazlasına katılmayan öğrenci NA notu alır.
"""


# 1) SCHEMA: the exact shape we want back, written as Python code.
class RegulationAnswer(BaseModel):
    answer: str = Field(max_length=MAX_ANSWER_CHARS, description="Short answer in Turkish.")
    found_in_regulation: bool = Field(description="True only if the regulation text answers the question.")
    cited_articles: list[str] = Field(description='Articles used, e.g. ["MADDE 13"]. Empty if not found.')
    confidence: Literal["high", "medium", "low"]

    # Rules that span several fields.
    @model_validator(mode="after")
    def citations_match_found_flag(self):
        if self.found_in_regulation and not self.cited_articles:
            raise ValueError("found_in_regulation is true but cited_articles is empty; cite the articles you used")
        if not self.found_in_regulation and self.cited_articles:
            raise ValueError("found_in_regulation is false, so cited_articles must be empty")
        return self


SYSTEM_PROMPT = f"""You answer students' questions using ONLY the regulation text below.
If the text does not answer the question, set found_in_regulation to false and say so in the answer.
Never use outside knowledge.

Reply with ONLY a JSON object (no markdown, no code fences) that matches this JSON schema:
{json.dumps(RegulationAnswer.model_json_schema(), ensure_ascii=False)}

REGULATION TEXT:
{REGULATION}"""


def strip_code_fences(text: str) -> str:
    # Models often wrap JSON in ```json ... ``` even when told not to.
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())


def check_citations_exist(result: RegulationAnswer) -> None:
    # 2) VALIDATION that needs the source text: catch invented citations.
    for article in result.cited_articles:
        if article.strip().upper() not in REGULATION.upper():
            raise ValueError(f"cited article '{article}' does not exist in the regulation text")


def ask(question: str) -> RegulationAnswer:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    # 3) LOOP: if the output is invalid, tell the model what was wrong and let it retry.
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = client.chat.completions.create(model=MODEL, messages=messages, temperature=0)
        raw = response.choices[0].message.content or ""
        try:
            result = RegulationAnswer.model_validate_json(strip_code_fences(raw))
            check_citations_exist(result)
            print(f"  ✓ deneme {attempt}: geçerli")
            return result
        except ValueError as error:  # pydantic's ValidationError is a ValueError too
            print(f"  ✗ deneme {attempt}: reddedildi → {str(error)[:200]}")
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": f"Your previous reply was invalid: {error}\nReturn ONLY the corrected JSON object.",
            })
    raise RuntimeError(f"No valid answer after {MAX_ATTEMPTS} attempts.")


if __name__ == "__main__":
    questions = [
        "Dönemin 8. haftasındayım, bir dersten çekilebilir miyim? Transkriptimde ne görünür?",
        "Ekle-bırak haftasından sonra ders ekleyebilir miyim, ve toplamda kaç dersten çekilebilirim?",
        "Yaz okulunda en fazla kaç ders alabilirim?",  # not in the text: should NOT be answered
    ]
    for question in questions:
        print(f"\nSoru: {question}")
        try:
            result = ask(question)
        except RuntimeError as error:
            print(f"  !! {error}")
            continue
        print(f"  cevap      : {result.answer}")
        print(f"  bulundu mu : {result.found_in_regulation}")
        print(f"  kaynak     : {result.cited_articles}")
        print(f"  güven      : {result.confidence}")
