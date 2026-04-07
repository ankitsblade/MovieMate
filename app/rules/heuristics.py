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

SINGLE_NAME_QUERY_PATTERN = re.compile(
    r"\b((?:movies?|films?)\s+(?:with|starring|featuring|by)\s+)([A-Za-z][A-Za-z'-]*)\b(?!\s+[A-Za-z][A-Za-z'-]*)",
    re.IGNORECASE,
)


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

    if intent == "followup":
        return True

    return contains_any_phrase(lowered, CARD_TRIGGER_PATTERNS)


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

    return cleaned
