from __future__ import annotations

from typing import Any
import requests
from langsmith import traceable

from app.config import (
    NVIDIA_API_KEY,
    NVIDIA_RERANK_MODEL,
    NVIDIA_RERANK_URL,
)


def _build_passage(movie: dict[str, Any], max_chars: int = 2200) -> str:
    parts = [
        f"Title: {movie.get('primary_title') or ''}",
        f"Type: {movie.get('title_type') or ''}",
        f"Year: {movie.get('start_year') or ''}",
        f"Runtime: {movie.get('runtime_minutes') or ''}",
        f"Genres: {movie.get('genres') or ''}",
        f"Rating: {movie.get('average_rating') or ''}",
        f"Votes: {movie.get('num_votes') or ''}",
        f"People: {movie.get('people_summary') or ''}",
        f"Content: {movie.get('content') or ''}",
    ]
    text = "\n".join(parts).strip()
    return text[:max_chars]


@traceable(run_type="chain", name="nemotron_rerank_movies")
def rerank_movies(query: str, candidates: list[dict], top_n: int = 6) -> list[dict]:
    if not candidates:
        return []

    passages = [{"text": _build_passage(movie)} for movie in candidates]

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    payload = {
        "model": NVIDIA_RERANK_MODEL,
        "query": {"text": query},
        "passages": passages,
        "truncate": "END",
    }

    try:
        response = requests.post(
            NVIDIA_RERANK_URL,
            headers=headers,
            json=payload,
            timeout=12,
        )
        response.raise_for_status()
        data = response.json()
        rankings = data.get("rankings", [])

        reranked: list[dict] = []
        for rank_item in rankings[:top_n]:
            idx = rank_item["index"]
            movie = dict(candidates[idx])
            movie["rerank_score"] = rank_item.get("logit")
            reranked.append(movie)

        if reranked:
            return reranked

    except Exception:
        pass

    fallback = []
    for i, movie in enumerate(candidates[:top_n]):
        m = dict(movie)
        m["rerank_score"] = None
        m["fallback_rank"] = i + 1
        fallback.append(m)
    return fallback
