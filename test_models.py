from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.getenv("GITHUB_MODELS_BASE_URL", "https://models.github.ai/inference"),
    api_key=os.getenv("GITHUB_MODELS_TOKEN"),
)

models = [
    "openai/gpt-5",
    "openai/gpt-5-chat",
    "openai/gpt-5-mini",
    "openai/gpt-5-nano",
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    "openai/gpt-4.1-nano",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
]

for model in models:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say OK only"}],
            max_tokens=20,
        )
        print("PASS", model, "=>", response.choices[0].message.content)
    except Exception as e:
        print("FAIL", model, "=>", type(e).__name__, str(e)[:220])