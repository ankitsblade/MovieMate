from typing import Any, Literal

from pydantic import BaseModel, Field
from langsmith import traceable

from app.llm.chat_model import llm
from app.llm.prompts import ROUTER_PROMPT
from app.rules.heuristics import (
    GREETING_MESSAGES,
    SMALL_TALK_MESSAGES,
    infer_clarify_prompt,
    is_memory_lookup_message,
    is_recent_clarify_prompt,
    is_short_followup_message,
    looks_like_clarify_response,
    normalize_message,
)


class RouteDecision(BaseModel):
    intent: Literal[
        "greeting",
        "small_talk",
        "movie_query",
        "followup",
        "memory_lookup",
        "clarify",
    ]
    clarify_prompt: str | None = Field(
        default=None,
        description="Only when intent is clarify: one short clarification question to ask the user.",
    )


router_llm = llm.with_structured_output(RouteDecision)


def _strip_current_message(messages: list[Any] | None, user_message: str) -> list[Any]:
    if not messages:
        return []

    copied = list(messages)
    last_message = copied[-1]
    if (
        getattr(last_message, "type", "") == "human"
        and isinstance(getattr(last_message, "content", ""), str)
        and last_message.content.strip() == user_message.strip()
    ):
        return copied[:-1]

    return copied


def _format_history(messages: list[Any], max_messages: int = 4) -> str:
    prompt_messages = [
        msg for msg in messages
        if isinstance(getattr(msg, "content", ""), str) and msg.content.strip()
    ]
    return "\n".join(
        f"{msg.type}: {msg.content.strip()}"
        for msg in prompt_messages[-max_messages:]
    )


def _last_assistant_message(messages: list[Any]) -> str:
    for msg in reversed(messages):
        if getattr(msg, "type", "") == "ai" and isinstance(getattr(msg, "content", ""), str):
            content = msg.content.strip()
            if content:
                return content
    return ""


def _heuristic_route(
    user_message: str,
    messages: list[Any] | None = None,
) -> tuple[str, str | None] | None:
    prior_messages = _strip_current_message(messages, user_message)
    lowered = normalize_message(user_message)

    if lowered in GREETING_MESSAGES:
        return "greeting", None

    if lowered in SMALL_TALK_MESSAGES:
        return "small_talk", None

    if is_memory_lookup_message(user_message):
        return "memory_lookup", None

    clarify_prompt = infer_clarify_prompt(
        user_message=user_message,
        has_prior_context=bool(prior_messages),
    )
    if clarify_prompt:
        return "clarify", clarify_prompt

    if (
        prior_messages
        and is_recent_clarify_prompt(_last_assistant_message(prior_messages))
        and looks_like_clarify_response(user_message)
    ):
        return "followup", None

    if prior_messages and is_short_followup_message(user_message):
        return "followup", None

    return None


@traceable(run_type="chain", name="classify_intent")
def classify_intent(
    user_message: str,
    messages: list[Any] | None = None,
) -> tuple[str, str | None]:
    history = _format_history(_strip_current_message(messages, user_message))
    prompt = ROUTER_PROMPT.format(
        history=history or "None",
        user_message=user_message,
    )

    try:
        result = router_llm.invoke(
            [
                ("system", "Classify the user's latest message and provide clarify_prompt only when intent is clarify."),
                ("user", prompt),
            ]
        )
    except Exception:
        heuristic_result = _heuristic_route(user_message, messages)
        if heuristic_result:
            return heuristic_result
        clarify_prompt = infer_clarify_prompt(
            user_message=user_message,
            has_prior_context=bool(_strip_current_message(messages, user_message)),
        )
        if clarify_prompt:
            return "clarify", clarify_prompt
        return "movie_query", None

    if result.intent == "clarify":
        clarify_prompt = result.clarify_prompt or infer_clarify_prompt(
            user_message=user_message,
            has_prior_context=bool(_strip_current_message(messages, user_message)),
        )
        if clarify_prompt:
            return result.intent, clarify_prompt
        heuristic_result = _heuristic_route(user_message, messages)
        if heuristic_result:
            return heuristic_result

    return result.intent, None
