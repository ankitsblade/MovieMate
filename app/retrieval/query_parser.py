import re

from app.rules.heuristics import extract_genre, extract_person_name


def extract_filters(query: str) -> dict:
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
