import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

# Read NVIDIA_API_KEY and LLM_MODEL from the .env file into environment variables.
load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")
if not api_key:
    sys.exit("NVIDIA_API_KEY is empty. Paste your key into the .env file.")

# NVIDIA NIM speaks the same protocol as OpenAI, so we use the OpenAI client
# and just point it at NVIDIA's server.
client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)

response = client.chat.completions.create(
    model=os.getenv("LLM_MODEL"),
    messages=[
        {"role": "system", "content": "You are a helpful assistant. Answer in Turkish, briefly."},
        {"role": "user", "content": "Merhaba! LLM API'ı nedir, tek cümleyle anlatır mısın?"},
    ],
    temperature=0.2,
)

print(response.choices[0].message.content)
print(f"\n[model: {response.model} | tokens used: {response.usage.total_tokens}]")
