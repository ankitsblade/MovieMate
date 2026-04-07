from __future__ import annotations

import re
from statistics import mean
from typing import Any

from app.evals.judge import TurnJudgeResult, judge_turn
from app.rules.heuristics import answer_looks_complete


STOPWORDS = {
    "the",
    "and",
    "with",
    "from",
    "that",
    "this",
    "movies",
    "movie",
    "films",
    "film",
    "after",
    "before",
    "under",
    "over",
    "give",
    "show",
    "list",
    "some",
    "about",
    "what",
    "which",
    "into",
    "than",
}


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _score_band(score: float) -> str:
    if score >= 0.78:
        return "high"
    if score >= 0.52:
        return "medium"
    return "low"


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def _contains_person(movie: dict[str, Any], person_name: str) -> bool:
    haystack = " ".join(
        str(movie.get(key) or "")
        for key in ("people_summary", "content", "primary_title")
    ).lower()
    return person_name.lower() in haystack


def _score_movie_against_filters(movie: dict[str, Any], filters: dict[str, Any]) -> float:
    checks: list[float] = []

    person_name = filters.get("person_name")
    if person_name:
        checks.append(1.0 if _contains_person(movie, person_name) else 0.0)

    genre = filters.get("genre")
    if genre:
        genres = str(movie.get("genres") or "").lower()
        checks.append(1.0 if genre.lower() in genres else 0.0)

    min_year = filters.get("min_year")
    max_year = filters.get("max_year")
    year = movie.get("start_year")
    if min_year is not None:
        checks.append(1.0 if isinstance(year, int) and year >= min_year else 0.0)
    if max_year is not None:
        checks.append(1.0 if isinstance(year, int) and year <= max_year else 0.0)

    max_runtime = filters.get("max_runtime")
    runtime = movie.get("runtime_minutes")
    if max_runtime is not None:
        checks.append(1.0 if isinstance(runtime, int) and runtime <= max_runtime else 0.0)

    min_rating = filters.get("min_rating")
    rating = movie.get("average_rating")
    if min_rating is not None:
        checks.append(1.0 if isinstance(rating, (int, float)) and rating >= min_rating else 0.0)

    if not checks:
        return 0.72

    return mean(checks)


def _query_overlap_score(user_message: str, results: list[dict[str, Any]]) -> float:
    query_tokens = _tokenize(user_message)
    if not query_tokens or not results:
        return 0.6 if results else 0.0

    overlaps: list[float] = []
    for movie in results[:3]:
        evidence = " ".join(
            str(movie.get(key) or "")
            for key in ("primary_title", "genres", "people_summary", "content")
        )
        evidence_tokens = _tokenize(evidence)
        if not evidence_tokens:
            overlaps.append(0.0)
            continue
        overlaps.append(len(query_tokens & evidence_tokens) / len(query_tokens))

    return mean(overlaps) if overlaps else 0.0


def _extract_title_set(results: list[dict[str, Any]]) -> set[str]:
    return {
        str(movie.get("primary_title") or "").strip().lower()
        for movie in results
        if str(movie.get("primary_title") or "").strip()
    }


def _extract_answer_number(answer: str) -> int | None:
    match = re.search(r"\b(?:found|here are|here's|showing|got)\s+(\d+)\b", answer.lower())
    if match:
        return int(match.group(1))
    return None


def _response_consistency_score(
    *,
    answer: str,
    results: list[dict[str, Any]],
    show_movie_cards: bool,
) -> float:
    checks: list[float] = []

    if answer_looks_complete(answer):
        checks.append(1.0)
    else:
        checks.append(0.0)

    answer_count = _extract_answer_number(answer)
    if answer_count is not None:
        checks.append(1.0 if answer_count == len(results) else 0.0)

    if show_movie_cards:
        title_set = _extract_title_set(results)
        mentioned_titles = [
            title
            for title in title_set
            if title and title in answer.lower()
        ]
        checks.append(1.0 if not mentioned_titles else 0.0)

    if not checks:
        return 0.7

    return mean(checks)


def _build_eval_context(results: list[dict[str, Any]], limit: int = 6) -> str:
    if not results:
        return "None"

    runtimes = [
        int(movie["runtime_minutes"])
        for movie in results
        if isinstance(movie.get("runtime_minutes"), int)
    ]
    years = [
        int(movie["start_year"])
        for movie in results
        if isinstance(movie.get("start_year"), int)
    ]
    titles = [
        str(movie.get("primary_title") or "").strip()
        for movie in results
        if str(movie.get("primary_title") or "").strip()
    ]

    genre_counts: dict[str, int] = {}
    for movie in results:
        raw_genres = str(movie.get("genres") or "")
        for genre in raw_genres.split(","):
            cleaned = genre.strip()
            if cleaned:
                genre_counts[cleaned] = genre_counts.get(cleaned, 0) + 1

    top_genres = [
        genre
        for genre, _ in sorted(
            genre_counts.items(),
            key=lambda item: (-item[1], item[0].lower()),
        )[:3]
    ]

    summary_lines = [
        f"Retrieved result count: {len(results)}",
        "Retrieved titles: " + (", ".join(titles[:limit]) if titles else "None"),
        "Runtime range: "
        + (f"{min(runtimes)}-{max(runtimes)} minutes" if runtimes else "Unknown"),
        "Release year range: "
        + (f"{min(years)}-{max(years)}" if years else "Unknown"),
        "Common genres: " + (", ".join(top_genres) if top_genres else "Unknown"),
    ]

    chunks: list[str] = []
    for index, movie in enumerate(results[:limit], start=1):
        content = str(movie.get("content") or "").strip().replace("\n", " ")
        compact_content = content[:160]
        chunks.append(
            "\n".join(
                [
                    f"Evidence {index}",
                    f"Title: {movie.get('primary_title') or 'Unknown'}",
                    f"Year: {movie.get('start_year') or 'Unknown'}",
                    f"Genres: {movie.get('genres') or 'Unknown'}",
                    f"People: {movie.get('people_summary') or 'Unknown'}",
                    f"Content: {compact_content or 'Unknown'}",
                ]
            )
        )

    return "\n".join(summary_lines) + "\n\n" + "\n\n".join(chunks)


def evaluate_retrieval(
    *,
    user_message: str,
    intent: str,
    filters: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if intent not in {"movie_query", "followup"}:
        return None

    if not results:
        return {
            "score": 0.0,
            "band": "low",
            "note": "No retrieved evidence reached the final response.",
            "result_count": 0,
            "filter_alignment": 0.0,
            "query_overlap": 0.0,
        }

    filter_alignment = mean(
        _score_movie_against_filters(movie, filters)
        for movie in results[: min(4, len(results))]
    )
    query_overlap = _query_overlap_score(user_message, results)
    score = _clamp((filter_alignment * 0.65) + (query_overlap * 0.35))

    return {
        "score": score,
        "band": _score_band(score),
        "note": "Algorithmic retrieval checks look strong." if score >= 0.7 else "Algorithmic retrieval checks show partial alignment.",
        "result_count": len(results),
        "filter_alignment": round(filter_alignment, 3),
        "query_overlap": round(query_overlap, 3),
    }


def _proxy_response_score(
    *,
    answer: str,
    retrieval_score: float,
    intent: str,
) -> tuple[float, float, str]:
    if not answer.strip():
        return 0.0, 0.0, "Model judge unavailable and answer was empty."

    if intent in {"movie_query", "followup"}:
        response_score = _clamp((retrieval_score * 0.75) + 0.2)
        grounding_score = retrieval_score
        note = "Model judge unavailable; response metrics are proxy estimates derived from retrieval quality."
        return response_score, grounding_score, note

    response_score = 0.72
    grounding_score = 0.72
    note = "Model judge unavailable; non-retrieval response metrics are proxy estimates."
    return response_score, grounding_score, note


def _judge_scores(judge: TurnJudgeResult) -> tuple[float, float, float]:
    retrieval_score = mean([judge.retrieval_relevance, judge.evidence_alignment]) / 5
    response_score = mean([judge.helpfulness, judge.presentation_discipline, judge.groundedness]) / 5
    grounding_score = judge.groundedness / 5
    return retrieval_score, response_score, grounding_score


def evaluate_turn(
    *,
    user_message: str,
    intent: str,
    answer: str,
    filters: dict[str, Any],
    reranked_movies: list[dict[str, Any]],
    memory_context: str,
    show_movie_cards: bool,
    latency_ms: int,
) -> dict[str, Any]:
    retrieval_algorithmic = evaluate_retrieval(
        user_message=user_message,
        intent=intent,
        filters=filters,
        results=reranked_movies,
    )

    context = _build_eval_context(reranked_movies)
    judge = judge_turn(
        user_message=user_message,
        answer=answer,
        context=context,
        memory_context=memory_context,
        show_movie_cards=show_movie_cards,
    )

    if judge:
        judge_retrieval_score, response_score, grounding_score = _judge_scores(judge)
        response_consistency = _response_consistency_score(
            answer=answer,
            results=reranked_movies,
            show_movie_cards=show_movie_cards,
        )
        if retrieval_algorithmic:
            retrieval_score = _clamp(
                (retrieval_algorithmic["score"] * 0.55) + (judge_retrieval_score * 0.45)
            )
        else:
            retrieval_score = judge_retrieval_score
        response_score = _clamp((response_score * 0.75) + (response_consistency * 0.25))
        grounding_score = _clamp((grounding_score * 0.7) + (response_consistency * 0.3))
        note = judge.note
    else:
        retrieval_score = retrieval_algorithmic["score"] if retrieval_algorithmic else 0.68
        response_score, grounding_score, note = _proxy_response_score(
            answer=answer,
            retrieval_score=retrieval_score,
            intent=intent,
        )

    overall = _clamp((retrieval_score * 0.45) + (response_score * 0.55))

    signals = [
        {
            "label": "Retrieval",
            "score": round(retrieval_score, 3),
            "band": _score_band(retrieval_score),
        },
        {
            "label": "Response",
            "score": round(response_score, 3),
            "band": _score_band(response_score),
        },
        {
            "label": "Grounding",
            "score": round(grounding_score, 3),
            "band": _score_band(grounding_score),
        },
    ]

    return {
        "overall_score": round(overall, 3),
        "band": _score_band(overall),
        "latency_ms": latency_ms,
        "signals": signals,
        "note": note,
        "details": {
            "retrieval_algorithmic": retrieval_algorithmic,
            "llm_judge": (
                {
                    "retrieval_relevance": judge.retrieval_relevance,
                    "evidence_alignment": judge.evidence_alignment,
                    "groundedness": judge.groundedness,
                    "helpfulness": judge.helpfulness,
                    "presentation_discipline": judge.presentation_discipline,
                    "note": judge.note,
                }
                if judge
                else None
            ),
            "result_count": len(reranked_movies),
            "show_movie_cards": show_movie_cards,
        },
    }
