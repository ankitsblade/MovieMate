import os
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_EMBED_MODEL = os.getenv("NVIDIA_EMBED_MODEL", "nvidia/llama-nemotron-embed-1b-v2")
NVIDIA_CHAT_MODEL = os.getenv("NVIDIA_CHAT_MODEL", "meta/llama-3.1-70b-instruct")
NVIDIA_RERANK_MODEL = os.getenv("NVIDIA_RERANK_MODEL", "nvidia/llama-nemotron-rerank-1b-v2")
NVIDIA_RERANK_URL = os.getenv(
    "NVIDIA_RERANK_URL",
    "https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-nemotron-rerank-1b-v2/reranking",
)

EMBED_DIMENSIONS = int(os.getenv("EMBED_DIMENSIONS", "384"))

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

TOP_K_RETRIEVE = int(os.getenv("TOP_K_RETRIEVE", "30"))
TOP_K_FINAL = int(os.getenv("TOP_K_FINAL", "6"))

LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "moviemate-dev")