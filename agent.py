import json
import os
import sys

from dotenv import load_dotenv
from openai import APIError, OpenAI

from tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")
if not api_key:
    sys.exit("NVIDIA_API_KEY is empty. Paste your key into the .env file.")

client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key, max_retries=5)
MODEL = os.getenv("LLM_MODEL")

SYSTEM_PROMPT = (
    "You are a helpful assistant for university students. Answer in Turkish. "
    "Use the tools for dates and GPA calculations; never guess them. "
    "If a tool returns an error, fix your arguments and call it again."
)

MAX_STEPS = 6  # safety limit: stop if the model keeps asking for tools forever

# Set AGENT_DEBUG=1 to see the raw tool calls and results (for developers).
DEBUG = os.getenv("AGENT_DEBUG") == "1"

# What the student sees instead of raw tool calls.
TOOL_LABELS = {
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


def run_agent(messages: list) -> str:
    """The agent loop: ask the model; if it requests tools, run them, send results back, repeat."""
    for step in range(1, MAX_STEPS + 1):
        if step == 1 or DEBUG:
            print("  💭 Düşünüyor...")
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            temperature=0,
        )
        message = response.choices[0].message
        messages.append(message)  # the model's turn: either tool requests or the final answer

        # No tool requested -> the model is done, this is the final answer.
        if not message.tool_calls:
            if message.content:
                return message.content
            # Reasoning models sometimes put everything in their hidden "thinking" field
            # and leave the visible answer empty. Drop that empty turn and try again.
            messages.pop()
            print("  ↻ Boş cevap geldi, tekrar deneniyor...")
            continue

        # The model asked for one or more tools: run each and send the result back.
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            if DEBUG:
                print(f"  🔧 {name}({tool_call.function.arguments})")
            else:
                print(f"  {TOOL_LABELS.get(name, '🔧 Bir işlem yapılıyor...')}")
            result = run_tool(tool_call)
            if DEBUG:
                print(f"     ↳ {result}")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,  # which request this result answers
                "content": json.dumps(result, ensure_ascii=False),
            })

    # Step limit reached. Instead of throwing away the tool results we already have,
    # ask one last time with tools disabled: "answer with what you've got".
    print("  ⚠️ Adım sınırına ulaşıldı, eldeki bilgiyle cevaplanıyor...")
    for _ in range(2):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="none",  # the model may NOT request tools on this call
            temperature=0,
        )
        message = response.choices[0].message
        if message.content:
            messages.append(message)
            return message.content

    return "Üzgünüm, bu soruyu makul sayıda adımda çözemedim."


if __name__ == "__main__":
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
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
            answer = run_agent(messages)
        except APIError as error:
            print(f"  [API hatası: {error}] Tekrar dene.\n")
            del messages[turn_start:]  # drop this whole unfinished turn so history stays consistent
            continue

        print(f"\nAsistan: {answer}\n")
