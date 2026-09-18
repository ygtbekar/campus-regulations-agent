import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

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

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2,
    )
    reply = response.choices[0].message.content

    # Save the model's answer too, so the next turn "remembers" it.
    messages.append({"role": "assistant", "content": reply})

    print(f"\nModel: {reply}")
    # prompt_tokens = size of everything we SENT this turn. Watch it grow.
    print(f"[gönderilen mesaj: {len(messages) - 1} | gönderilen token: {response.usage.prompt_tokens}]\n")
