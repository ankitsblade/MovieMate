from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.llm.chat_model import llm
from app.llm.prompts import RETRIEVAL_PARSE_PROMPT
from app.rules.heuristics import extract_genre, extract_person_name, normalize_person_candidate


class RetrievalParseResult(BaseModel):
    rewritten_query: str = Field(min_length=1)
    person_name: str | None = None
    genre: str | None = None
    min_year: int | None = Field(default=None, ge=1870, le=2100)
    max_year: int | None = Field(default=None, ge=1870, le=2100)
    max_runtime: int | None = Field(default=None, ge=1, le=600)
    min_rating: float | None = Field(default=None, ge=0.0, le=10.0)


retrieval_parser_llm = llm.with_structured_output(RetrievalParseResult)


def _heuristic_filters(query: str) -> dict:
    q = query.lower()

    filters = {
        "min_year": None,
        "max_year": None,
        "max_runtime": None,
        "min_rating": None,
        "genre": extract_genre(query),
        "person_name": extract_person_name(query),
    }

    after_year = re.search(r"after\s+(\d{4})", q)
    if after_year:
        filters["min_year"] = int(after_year.group(1)) + 1

    before_year = re.search(r"before\s+(\d{4})", q)
    if before_year:
        filters["max_year"] = int(before_year.group(1)) - 1

    under_minutes = re.search(r"(under|less than)\s+(\d+)\s*(minutes|min)?", q)
    if under_minutes:
        filters["max_runtime"] = int(under_minutes.group(2))

    under_hours = re.search(r"(under|less than)\s+(\d+)\s*hours?", q)
    if under_hours:
        filters["max_runtime"] = int(under_hours.group(2)) * 60

    rating_match = re.search(r"(rated above|rating above|above)\s+(\d+(\.\d+)?)", q)
    if rating_match:
        filters["min_rating"] = float(rating_match.group(2))

    return filters


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _merge_with_fallback(primary: dict, fallback: dict) -> dict:
    merged = dict(primary)
    for key, value in fallback.items():
        if merged.get(key) is None:
            merged[key] = value
    return merged


def extract_filters(query: str) -> dict:
    fallback = _heuristic_filters(query)

    prompt = RETRIEVAL_PARSE_PROMPT.format(query=query)
    try:
        parsed = retrieval_parser_llm.invoke(
            [
                ("system", "Extract structured retrieval filters for a movie database query. Prefer null over guessing."),
                ("user", prompt),
            ]
        )
    except Exception:
        return fallback

    person_name = _clean_text(parsed.person_name)
    normalized_person = normalize_person_candidate(person_name) if person_name else None

    llm_filters = {
        "min_year": parsed.min_year,
        "max_year": parsed.max_year,
        "max_runtime": parsed.max_runtime,
        "min_rating": parsed.min_rating,
        "genre": _clean_text(parsed.genre),
        "person_name": normalized_person,
    }

    if (
        llm_filters["min_year"] is not None
        and llm_filters["max_year"] is not None
        and llm_filters["min_year"] > llm_filters["max_year"]
    ):
        return fallback

    return _merge_with_fallback(llm_filters, fallback)
