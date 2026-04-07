from langchain_openai import ChatOpenAI
from app.config import NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_CHAT_MODEL

llm = ChatOpenAI(
    model=NVIDIA_CHAT_MODEL,
    api_key=NVIDIA_API_KEY,
    base_url=NVIDIA_BASE_URL,
    temperature=0.2,
    max_tokens=900,
)
