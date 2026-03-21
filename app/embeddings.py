from openai import OpenAI
from app.config import (
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NVIDIA_EMBED_MODEL,
    EMBED_DIMENSIONS,
)

client = OpenAI(
    api_key=NVIDIA_API_KEY,
    base_url=NVIDIA_BASE_URL,
)

def _clean(text: str) -> str:
    return text.replace("\n", " ").strip()

def get_passage_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model=NVIDIA_EMBED_MODEL,
        input=[_clean(text)],
        encoding_format="float",
        extra_body={
            "input_type": "passage",
            "dimensions": EMBED_DIMENSIONS,
        },
    )
    return response.data[0].embedding

def get_query_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model=NVIDIA_EMBED_MODEL,
        input=[_clean(text)],
        encoding_format="float",
        extra_body={
            "input_type": "query",
            "dimensions": EMBED_DIMENSIONS,
        },
    )
    return response.data[0].embedding