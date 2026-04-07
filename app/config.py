import os
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_EMBED_MODEL = os.getenv("NVIDIA_EMBED_MODEL", "nvidia/llama-nemotron-embed-1b-v2")
NVIDIA_CHAT_MODEL = os.getenv("NVIDIA_CHAT_MODEL", "openai/gpt-oss-120b")
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

ENABLE_LLM_EVAL = os.getenv("ENABLE_LLM_EVAL", "true").lower() in {"1", "true", "yes", "on"}
EVAL_CHAT_MODEL = os.getenv(
    "EVAL_CHAT_MODEL",
    os.getenv("NVIDIA_JUDGE_MODEL", os.getenv("NVIDIA_EVALUATOR_MODEL", "openai/gpt-oss-120b")),
)
EVAL_LLM_TIMEOUT_SECONDS = float(os.getenv("EVAL_LLM_TIMEOUT_SECONDS", "30"))

LOW_SIGNAL_RETRY_THRESHOLD = float(os.getenv("LOW_SIGNAL_RETRY_THRESHOLD", "0.5"))
LOW_SIGNAL_MAX_RETRIES = int(os.getenv("LOW_SIGNAL_MAX_RETRIES", "1"))
