import json
import os
import re
import sys

from dotenv import load_dotenv
from openai import APIError, OpenAI
from pydantic import BaseModel, Field

from retrieval import article_title
from tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")
if not api_key:
    sys.exit("NVIDIA_API_KEY is empty. Paste your key into the .env file.")

client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key, max_retries=5)
MODEL = os.getenv("LLM_MODEL")


class AgentAnswer(BaseModel):
    answer: str = Field(description="The answer to the student, in Turkish.")
    sources: list[str] = Field(
        default_factory=list,
        description='Regulation articles the answer is based on, e.g. ["MADDE 22"]. Empty if none were used.',
    )


SYSTEM_PROMPT = f"""You are an assistant for METU Northern Cyprus Campus undergraduate students. Answer in Turkish.

Rules:
1. For ANY question about academic rules (withdrawal, add-drop, attendance, grades, probation, graduation, course load...), call search_regulations first and answer ONLY from the articles it returns. Never rely on your own knowledge of university rules.
2. Be complete. State every condition, limit, deadline, approval and exception in the cited article that affects the student's situation - for example both a per-semester limit and a total limit, or an extra requirement beyond a grade average. A rule quoted without its conditions misleads the student.
3. If the retrieved articles only partly cover the question - the regulation mentions the topic but leaves the detail to the Senate, an academic board or the academic calendar - say what the regulation does state, cite that article in sources, and say clearly that the detail is not in this regulation.
4. If nothing relevant was retrieved, say you could not find it in the regulation and leave sources empty. Never answer from your own knowledge about campus life (clubs, dormitories, cafeteria, scholarships, specific course or exam dates); those are outside this regulation.
5. Use the tools for dates and GPA calculations; never guess them. If a tool returns an error, fix your arguments and call it again.
6. Your FINAL reply must be ONLY a JSON object (no markdown, no code fences) matching this schema:
{json.dumps(AgentAnswer.model_json_schema(), ensure_ascii=False)}
"sources" may only contain articles returned by search_regulations that you actually used, written like "MADDE 22"."""

MAX_STEPS = 6  # safety limit: stop if the model keeps asking for tools forever

# Set AGENT_DEBUG=1 to see the raw tool calls and results (for developers).
DEBUG = os.getenv("AGENT_DEBUG") == "1"

# What the student sees instead of raw tool calls.
TOOL_LABELS = {
    "search_regulations": "📚 Yönetmelikte aranıyor...",
    "get_today": "📅 Bugünün tarihine bakılıyor...",
    "days_until": "📅 Kalan gün sayısı hesaplanıyor...",
    "calculate_gpa": "🧮 Not ortalaması hesaplanıyor...",
}


def run_tool(tool_call) -> dict:
    """Run the Python function the model asked for. Problems are returned as data, never raised."""
    name = tool_call.function.name
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return {"error": f"Unknown tool '{name}'."}
    try:
        arguments = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        return {"error": "Tool arguments were not valid JSON."}
    try:
        return function(**arguments)
    except TypeError as error:  # missing or unexpected arguments
        return {"error": f"Bad arguments for {name}: {error}"}


def strip_code_fences(text: str) -> str:
    # Models often wrap JSON in ```json ... ``` even when told not to.
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())


# Chinese, Japanese and Korean characters. The model sometimes leaks a stray token from another
# language mid-sentence (seen at temperature 0 too), e.g. "mevcut 규lamada".
FOREIGN_SCRIPT = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")


def parse_final_answer(text: str, retrieved: set[int]) -> AgentAnswer:
    """Validate the model's final reply. Raises ValueError with a message the model can act on."""
    result = AgentAnswer.model_validate_json(strip_code_fences(text))
    stray = FOREIGN_SCRIPT.findall(result.answer)
    if stray:
        raise ValueError(
            f"the answer contains characters from another script ({''.join(stray)}); rewrite it in Turkish only"
        )
    normalized = []
    for source in result.sources:
        match = re.fullmatch(r"MADDE\s+(\d+)", source.strip(), flags=re.IGNORECASE)
        if not match:
            raise ValueError(f"source '{source}' must be written like 'MADDE 22'")
        number = int(match.group(1))
        # The key reliability check: a citation must come from an actual search result,
        # not from the model's memory.
        if number not in retrieved:
            raise ValueError(
                f"source '{source}' was not returned by search_regulations in this conversation; "
                "cite only articles you actually retrieved"
            )
        normalized.append(f"MADDE {number}")
    result.sources = normalized
    return result


def run_agent(messages: list, retrieved: set[int], on_status=None) -> AgentAnswer:
    """The agent loop: ask the model; run the tools it requests; validate its final answer.

    on_status: optional callback so a user interface can show the same progress as the terminal.
    """
    def emit(text: str) -> None:
        print(f"  {text}")
        if on_status:
            on_status(text)

    for step in range(1, MAX_STEPS + 1):
        if step == 1 or DEBUG:
            emit("💭 Düşünüyor...")
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            temperature=0,
        )
        message = response.choices[0].message
        messages.append(message)  # the model's turn: either tool requests or the final answer

        # The model asked for one or more tools: run each and send the result back.
        if message.tool_calls:
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                if DEBUG:
                    emit(f"🔧 {name}({tool_call.function.arguments})")
                else:
                    emit(TOOL_LABELS.get(name, "🔧 Bir işlem yapılıyor..."))
                result = run_tool(tool_call)
                if DEBUG:
                    print(f"     ↳ {str(result)[:300]}")
                if name == "search_regulations":
                    # Remember which articles were really retrieved, to verify citations later.
                    retrieved.update(int(r["article"].split()[1]) for r in result.get("results", []))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,  # which request this result answers
                    "content": json.dumps(result, ensure_ascii=False),
                })
            continue

        # No tool requested: this should be the final answer.
        if not message.content:
            # Reasoning models sometimes put everything in their hidden "thinking" field
            # and leave the visible answer empty. Drop that empty turn and try again.
            messages.pop()
            emit("↻ Boş cevap geldi, tekrar deneniyor...")
            continue
        try:
            return parse_final_answer(message.content, retrieved)
        except ValueError as error:  # pydantic's ValidationError is a ValueError too
            emit("↻ Cevap doğrulamadan geçemedi, düzeltiliyor...")
            if DEBUG:
                print(f"     ↳ {str(error)[:300]}")
            messages.append({
                "role": "user",
                "content": f"Your final reply was invalid: {error}\nReturn ONLY the corrected JSON object.",
            })

    # Step limit reached. Instead of throwing away the tool results we already have,
    # ask one last time with tools disabled: "answer with what you've got".
    emit("⚠️ Adım sınırına ulaşıldı, eldeki bilgiyle cevaplanıyor...")
    for _ in range(2):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="none",  # the model may NOT request tools on this call
            temperature=0,
        )
        message = response.choices[0].message
        if not message.content:
            continue
        messages.append(message)
        try:
            return parse_final_answer(message.content, retrieved)
        except ValueError:
            # Unverifiable citations are dropped rather than shown to the student.
            return AgentAnswer(answer=strip_code_fences(message.content), sources=[])

    return AgentAnswer(answer="Üzgünüm, bu soruyu makul sayıda adımda çözemedim.")


if __name__ == "__main__":
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    retrieved: set[int] = set()  # articles returned by search_regulations in this conversation
    print("Asistan hazır. Çıkmak için 'q' yaz.\n")

    while True:
        user_input = input("Sen: ").strip()
        if user_input.lower() in {"q", "quit", "exit"}:
            break
        if not user_input:
            continue

        turn_start = len(messages)
        messages.append({"role": "user", "content": user_input})
        try:
            result = run_agent(messages, retrieved)
        except APIError as error:
            print(f"  [API hatası: {error}] Tekrar dene.\n")
            del messages[turn_start:]  # drop this whole unfinished turn so history stays consistent
            continue

        print(f"\nAsistan: {result.answer}")
        for source in result.sources:
            number = int(source.split()[1])
            print(f"  📄 Kaynak: {source} – {article_title(number)}")
        print()
