import os
import sys

from dotenv import load_dotenv
from openai import APIError, OpenAI

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")
if not api_key:
    sys.exit("NVIDIA_API_KEY is empty. Paste your key into the .env file.")

client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
MODEL = os.getenv("LLM_MODEL")

# The API has no memory. This list IS the memory:
# every turn we append to it and send the WHOLE list again.
messages = [
    {"role": "system", "content": "You are a helpful assistant. Answer in Turkish, briefly."},
]

print("Sohbet başladı. Çıkmak için 'q' yaz.\n")

while True:
    user_input = input("Sen: ").strip()
    if user_input.lower() in {"q", "quit", "exit"}:
        break
    if not user_input:
        continue

    messages.append({"role": "user", "content": user_input})

    print("\nModel: ", end="", flush=True)
    reply = ""
    usage = None
    try:
        # stream=True: the server sends the answer in small pieces (chunks)
        # as it generates them, instead of one big response at the end.
        stream = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.2,
            stream=True,
            stream_options={"include_usage": True},  # token counts arrive in the last chunk
        )
        for chunk in stream:
            if chunk.usage:
                usage = chunk.usage
            if not chunk.choices:
                continue
            # Reasoning models also stream their "thinking" in a separate field;
            # we only print the actual answer (delta.content).
            piece = chunk.choices[0].delta.content
            if piece:
                print(piece, end="", flush=True)  # flush: show it NOW, don't buffer
                reply += piece
    except APIError as error:
        print(f"\n[API hatası: {error}] Tekrar dene.\n")
        messages.pop()  # forget the unanswered question so history stays consistent
        continue

    # Save the model's answer too, so the next turn "remembers" it.
    messages.append({"role": "assistant", "content": reply})

    # prompt_tokens = size of everything we SENT this turn. Watch it grow.
    sent_tokens = usage.prompt_tokens if usage else "?"
    print(f"\n[gönderilen mesaj: {len(messages) - 1} | gönderilen token: {sent_tokens}]\n")
