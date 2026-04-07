from __future__ import annotations

import re


# Routing heuristics
GREETING_MESSAGES = {
    "hi",
    "hello",
    "hey",
    "hey there",
    "hello there",
    "greetings",
}

SMALL_TALK_MESSAGES = {
    "thanks",
    "thank you",
    "thanks!",
    "thank you!",
    "ok",
    "okay",
    "cool",
    "nice",
    "bye",
    "goodbye",
    "see you",
}

MEMORY_LOOKUP_PATTERNS = (
    r"\bdo you remember\b",
    r"\bwhat did i say\b",
    r"\bwhat do you know about me\b",
    r"\bwhat do you know about my taste\b",
    r"\bwhat's my name\b",
    r"\bwhat is my name\b",
    r"\bremember my name\b",
    r"\bearlier\b",
)

FOLLOWUP_HINTS = (
    "newer",
    "older",
    "shorter",
    "longer",
    "darker",
    "lighter",
    "funnier",
    "scarier",
    "better",
    "higher rated",
    "lower rated",
    "more like",
    "less like",
    "after ",
    "before ",
    "under ",
    "over ",
)

CLARIFY_RESPONSE_HINTS = (
    "which ",
    "what kind of movie",
    "what kind of movies",
    "what should i narrow by",
    "who are you referring to",
    "give me the full name",
)

GENERIC_RECOMMENDATION_PATTERNS = (
    r"^(?:recommend|suggest)\s+(?:something|anything)\b",
    r"^(?:show me|give me)\s+(?:something|anything)\b",
    r"^(?:any|anything)\s+good\b",
    r"^(?:some|a)\s+good\s+(?:movie|movies|film|films)\b",
    r"^(?:movie|movies|film|films)\s*$",
)

AMBIGUOUS_REFERENCE_PATTERNS = (
    r"\bher movies\b",
    r"\bhis movies\b",
    r"\btheir movies\b",
    r"\bthat actor\b",
    r"\bthat actress\b",
    r"\bthat director\b",
    r"\bthat movie\b",
    r"\bthat one\b",
    r"\bthose ones\b",
    r"\bit\b",
)

SINGLE_NAME_PERSON_PATTERN = re.compile(
    r"\b(?:movies?|films?)\s+(?:with|starring|featuring|by)\s+([A-Za-z][A-Za-z'-]*)\b(?!\s+[A-Za-z][A-Za-z'-]*)",
    re.IGNORECASE,
)


# Retrieval heuristics
PERSON_QUERY_PATTERNS = (
    r"\b(?:movies?|films?)\s+(?:starring|featuring|with|by)\s+(.+?)(?=$|,|\s+(?:after|before|under|over|rated|rating|from|for|that|which|who)\b)",
    r"\b(?:starring|featuring|with|directed by|by)\s+(.+?)(?=$|,|\s+(?:after|before|under|over|rated|rating|from|for|that|which|who)\b)",
)

NAME_CONNECTORS = {"de", "da", "del", "van", "von", "la", "le", "du", "di"}

NON_NAME_TOKENS = {
    "strong",
    "visuals",
    "dark",
    "darker",
    "funny",
    "sad",
    "new",
    "newer",
    "older",
    "classic",
    "classics",
    "good",
    "great",
    "best",
    "smart",
    "mind-bending",
    "mindbending",
    "short",
    "shorter",
    "long",
    "longer",
    "space",
    "romantic",
    "action",
    "drama",
    "thriller",
    "comedy",
    "movies",
    "movie",
    "films",
    "film",
}

BARE_PERSON_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z' -]{1,60}$")

COMMON_GENRES = (
    "action",
    "comedy",
    "drama",
    "thriller",
    "romance",
    "sci-fi",
    "science fiction",
    "horror",
    "crime",
    "adventure",
    "animation",
    "fantasy",
    "mystery",
    "western",
)


# Presentation and memory heuristics
CARD_TRIGGER_PATTERNS = (
    "recommend",
    "suggest",
    "list",
    "show me",
    "give me",
    "what should i watch",
    "movies like",
    "similar to",
    "looking for",
)

TEXT_ONLY_PATTERNS = (
    "tell me about",
    "who directed",
    "who stars",
    "who is in",
    "what is",
    "explain",
    "compare",
    "difference between",
    "ending of",
    "plot of",
    "summary of",
)

PREFERENCE_PATTERNS = (
    "my name is",
    "favorite",
    "i like",
    "i love",
    "i prefer",
    "i hate",
    "i dislike",
    "not in the mood",
)

CARD_SECTION_PATTERN = re.compile(
    r"\n+\s*(?:cards?|movie cards?)\s*:\s*(?:\n\s*(?:[-*]|\d+\.).*)*$",
    re.IGNORECASE,
)
BULLET_GLYPH_PATTERN = re.compile(r"^\s*[•●▪◦]\s+", re.MULTILINE)
ORDERED_PAREN_PATTERN = re.compile(r"^(\s*)(\d+)\)\s+", re.MULTILINE)

SINGLE_NAME_QUERY_PATTERN = re.compile(
    r"\b((?:movies?|films?)\s+(?:with|starring|featuring|by)\s+)([A-Za-z][A-Za-z'-]*)\b(?!\s+[A-Za-z][A-Za-z'-]*)",
    re.IGNORECASE,
)
SENTENCE_END_PATTERN = re.compile(r"[.!?][\"')\]]?$")


def normalize_message(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def matches_any_regex(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def contains_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def extract_single_name_reference(user_message: str) -> str | None:
    match = SINGLE_NAME_PERSON_PATTERN.search(user_message.strip())
    if not match:
        return None

    name = match.group(1).strip()
    if name.lower() in {"me", "him", "her", "them", "it"}:
        return None

    return name.title()


def is_memory_lookup_message(user_message: str) -> bool:
    return matches_any_regex(normalize_message(user_message), MEMORY_LOOKUP_PATTERNS)


def is_short_followup_message(user_message: str) -> bool:
    lowered = normalize_message(user_message)
    return len(lowered.split()) <= 7 and contains_any_phrase(lowered, FOLLOWUP_HINTS)


def looks_like_clarify_response(user_message: str) -> bool:
    lowered = normalize_message(user_message)
    return len(lowered.split()) <= 8 and not lowered.endswith("?")


def is_recent_clarify_prompt(message_text: str) -> bool:
    return contains_any_phrase(normalize_message(message_text), CLARIFY_RESPONSE_HINTS)


def infer_clarify_prompt(user_message: str, has_prior_context: bool) -> str | None:
    lowered = normalize_message(user_message)

    single_name = extract_single_name_reference(user_message)
    if single_name:
        return (
            f"Which {single_name} do you mean? If you can, give me the full name of the actor or director."
        )

    if not has_prior_context and matches_any_regex(lowered, AMBIGUOUS_REFERENCE_PATTERNS):
        return "Who are you referring to there? You can name the movie, actor, or director."

    if matches_any_regex(lowered, GENERIC_RECOMMENDATION_PATTERNS):
        return (
            "What kind of movie are you in the mood for? You can give me a genre, mood, actor, director, runtime, or a movie you already like."
        )

    if lowered in {"something", "anything", "recommend", "suggest"}:
        return (
            "What kind of movie are you after? A genre, mood, actor, director, runtime, or a movie you want something similar to would help."
        )

    return None


def normalize_person_candidate(candidate: str) -> str | None:
    cleaned = re.sub(r"^[\"']|[\"'.!,?]+$", "", candidate.strip())
    cleaned = re.sub(r"\b(?:actor|actress|director)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")

    if not cleaned:
        return None

    tokens = cleaned.split()
    if not 2 <= len(tokens) <= 5:
        return None

    normalized_tokens: list[str] = []
    meaningful_token_count = 0

    for token in tokens:
        lowered = token.lower()
        bare = re.sub(r"[^a-zA-Z'-]", "", token)
        if not bare:
            return None

        if lowered in NAME_CONNECTORS:
            normalized_tokens.append(lowered)
            continue

        if lowered in NON_NAME_TOKENS:
            return None

        meaningful_token_count += 1
        normalized_tokens.append(bare.title())

    if meaningful_token_count < 2:
        return None

    return " ".join(normalized_tokens)


def person_name_tokens(person_name: str) -> list[str]:
    return [
        token.lower()
        for token in person_name.split()
        if token.lower() not in NAME_CONNECTORS and len(token) > 1
    ]


def person_name_matches_text(person_name: str, text: str) -> bool:
    lowered = str(text or "").lower()
    if not lowered.strip():
        return False

    phrase_pattern = r"\b" + r"\s+".join(re.escape(part.lower()) for part in person_name.split()) + r"\b"
    if re.search(phrase_pattern, lowered):
        return True

    tokens = person_name_tokens(person_name)
    if not tokens:
        return False

    return all(re.search(r"\b" + re.escape(token) + r"\b", lowered) for token in tokens)


def extract_person_name(query: str) -> str | None:
    for pattern in PERSON_QUERY_PATTERNS:
        match = re.search(pattern, query, flags=re.IGNORECASE)
        if not match:
            continue

        candidate = normalize_person_candidate(match.group(1))
        if candidate:
            return candidate

    if BARE_PERSON_NAME_PATTERN.fullmatch(query.strip()):
        candidate = normalize_person_candidate(query)
        if candidate:
            return candidate

    return None


def extract_genre(query: str) -> str | None:
    lowered = query.lower()
    for genre in COMMON_GENRES:
        if genre in lowered:
            return genre
    return None


def replace_single_name_query(query: str, full_name: str) -> str | None:
    match = SINGLE_NAME_QUERY_PATTERN.search(query)
    if not match:
        return None

    prefix = match.group(1)
    return SINGLE_NAME_QUERY_PATTERN.sub(f"{prefix}{full_name}", query, count=1)


def should_use_memory(user_message: str, intent: str) -> bool:
    lowered = user_message.lower()

    if intent in {"followup", "memory_lookup"}:
        return True

    return any(
        pattern in lowered
        for pattern in (
            "for me",
            "based on what i like",
            "based on my taste",
            "remember",
            "same vibe",
            "similar to what i said",
            "my favorite",
            "i like",
            "i love",
            "i hate",
            "i dislike",
            "i prefer",
        )
    )


def should_show_movie_cards(user_message: str, intent: str, has_results: bool) -> bool:
    if intent not in {"movie_query", "followup"} or not has_results:
        return False

    lowered = user_message.lower()
    if contains_any_phrase(lowered, TEXT_ONLY_PATTERNS):
        return False

    return True


def answer_looks_complete(answer: str) -> bool:
    text = answer.strip()
    if not text:
        return False

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False

    return bool(SENTENCE_END_PATTERN.search(lines[-1]))


def _join_phrases(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _request_style_phrase(user_message: str) -> str | None:
    lowered = user_message.lower()

    cue_map = (
        ("feel-good", "that feel-good mood"),
        ("feel good", "that feel-good mood"),
        ("comfort", "that comforting vibe"),
        ("dark", "that darker tone"),
        ("thriller", "that thriller mood"),
        ("sci-fi", "that sci-fi lane"),
        ("science fiction", "that sci-fi lane"),
        ("funny", "something lighter"),
        ("comedy", "something lighter"),
        ("romance", "that romantic mood"),
        ("war", "that war-drama space"),
        ("documentary", "that documentary lane"),
        ("family", "something easy to settle into"),
        ("action", "that action-heavy lane"),
    )

    for needle, phrase in cue_map:
        if needle in lowered:
            return phrase

    return None


def build_card_mode_answer(user_message: str, results: list[dict]) -> str:
    if not results:
        return "I couldn't find any strong retrieved matches for that request."

    count = len(results)
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

    genre_counts: dict[str, int] = {}
    for movie in results:
        raw_genres = str(movie.get("genres") or "")
        for genre in raw_genres.split(","):
            cleaned = genre.strip()
            if not cleaned:
                continue
            genre_counts[cleaned] = genre_counts.get(cleaned, 0) + 1

    top_genres = [
        genre
        for genre, _ in sorted(
            genre_counts.items(),
            key=lambda item: (-item[1], item[0].lower()),
        )[:2]
    ]

    style_phrase = _request_style_phrase(user_message)
    if count == 1:
        lead = "I found one option that looks like a strong fit."
    elif style_phrase:
        lead = f"I pulled together a few options that should line up nicely with {style_phrase}."
    else:
        lead = "I pulled together a few options that look like a good fit."

    details: list[str] = [f"You’ll find {count} option{'s' if count != 1 else ''} below."]

    if runtimes:
        min_runtime = min(runtimes)
        max_runtime = max(runtimes)
        if min_runtime == max_runtime:
            details.append(f"They all land around {min_runtime} minutes.")
        else:
            details.append(f"They range from {min_runtime} to {max_runtime} minutes.")

    if top_genres:
        details.append(f"Overall, the mix leans toward {_join_phrases(top_genres)}.")

    if years:
        min_year = min(years)
        max_year = max(years)
        if min_year == max_year:
            details.append(f"They all come from {min_year}.")
        else:
            details.append(f"They span releases from {min_year} to {max_year}.")

    answer = f"{lead}\n\n{' '.join(details)}"
    return normalize_markdown_answer(answer)


def normalize_markdown_answer(answer: str) -> str:
    cleaned = answer.replace("\r\n", "\n").strip()
    if not cleaned:
        return cleaned

    cleaned = BULLET_GLYPH_PATTERN.sub("- ", cleaned)
    cleaned = ORDERED_PAREN_PATTERN.sub(r"\1\2. ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    normalized_lines: list[str] = []
    previous_blank = False

    for raw_line in cleaned.split("\n"):
        line = raw_line.strip()
        if not line:
            if normalized_lines and not previous_blank:
                normalized_lines.append("")
            previous_blank = True
            continue

        if line.startswith("#"):
            line = re.sub(r"^(#{1,6})([^ #])", r"\1 \2", line)

        normalized_lines.append(line)
        previous_blank = False

    return "\n".join(normalized_lines).strip()


def is_preference_statement(text: str) -> bool:
    return contains_any_phrase(text.lower(), PREFERENCE_PATTERNS)


def sanitize_answer(answer: str, show_movie_cards: bool) -> str:
    cleaned = answer.strip()

    if show_movie_cards:
        cleaned = CARD_SECTION_PATTERN.sub("", cleaned).strip()
        cleaned = re.sub(
            r"\b(?:the )?(?:cards?|movie cards?)\b",
            "recommendations",
            cleaned,
            flags=re.IGNORECASE,
        )

    return normalize_markdown_answer(cleaned)
