from openai import OpenAI
from app.config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_CHAT_MODEL

client = OpenAI(
    api_key=NVIDIA_API_KEY,
    base_url=NVIDIA_BASE_URL,
)

def generate_chat_response(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model=NVIDIA_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=700,
    )
    return response.choices[0].message.content