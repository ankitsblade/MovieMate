import re

from langchain_core.messages import HumanMessage, AIMessage
from langsmith import traceable

from app.config import TOP_K_RETRIEVE, TOP_K_FINAL
from app.graph.state import MovieState
from app.graph.router import classify_intent, infer_clarify_prompt
from app.llm.chat_model import llm
from app.llm.prompts import SYSTEM_PROMPT, QUERY_REWRITE_PROMPT, ANSWER_PROMPT
from app.llm.embeddings import get_query_embedding
from app.retrieval.query_parser import extract_filters, extract_person_name
from app.retrieval.retriever import search_movies
from app.retrieval.reranker import rerank_movies
from app.retrieval.formatter import format_context
from app.rules.heuristics import (
    is_preference_statement,
    replace_single_name_query,
    sanitize_answer,
    should_show_movie_cards,
    should_use_memory,
)


def _get_prior_messages(state: MovieState) -> list:
    messages = list(state.get("messages", []))
    current_message = state["user_message"].strip()

    if not messages:
        return messages

    last_message = messages[-1]
    if (
        getattr(last_message, "type", "") == "human"
        and isinstance(getattr(last_message, "content", ""), str)
        and last_message.content.strip() == current_message
    ):
        return messages[:-1]

    return messages


def _format_history(messages: list, max_messages: int) -> str:
    prompt_messages = [
        msg for msg in messages
        if isinstance(getattr(msg, "content", ""), str) and msg.content.strip()
    ]
    return "\n".join(
        f"{msg.type}: {msg.content.strip()}"
        for msg in prompt_messages[-max_messages:]
    )


def _extract_preference_lines(messages: list, limit: int = 3) -> list[str]:
    seen: set[str] = set()
    extracted: list[str] = []

    for msg in reversed(messages):
        if getattr(msg, "type", "") != "human":
            continue

        content = getattr(msg, "content", "").strip()
        if not content:
            continue

        lowered = content.lower()
        if not is_preference_statement(content):
            continue

        if lowered in seen:
            continue

        seen.add(lowered)
        extracted.append(content)

        if len(extracted) >= limit:
            break

    extracted.reverse()
    return extracted


def _recent_human_texts(messages: list, limit: int = 3) -> list[str]:
    human_messages = [
        msg.content.strip()
        for msg in messages
        if getattr(msg, "type", "") == "human"
        and isinstance(getattr(msg, "content", ""), str)
        and msg.content.strip()
    ]
    return human_messages[-limit:]


def _rewrite_clarify_followup(messages: list, user_message: str) -> str | None:
    person_name = extract_person_name(user_message)
    if not person_name:
        return None

    for previous_text in reversed(_recent_human_texts(messages, limit=4)):
        rewritten = replace_single_name_query(previous_text, person_name)
        if rewritten:
            return rewritten

    return f"Movies with {person_name}"


@traceable(run_type="chain", name="router_node")
def router_node(state: MovieState) -> MovieState:
    intent, clarify_prompt = classify_intent(
        state["user_message"],
        state.get("messages", []),
    )

    if intent in {"movie_query", "followup"}:
        return {
            "intent": intent,
            "needs_memory": should_use_memory(state["user_message"], intent),
            "needs_retrieval": True,
            "clarify_prompt": "",
        }

    if intent == "memory_lookup":
        return {
            "intent": intent,
            "needs_memory": True,
            "needs_retrieval": False,
            "clarify_prompt": "",
        }

    if intent == "clarify":
        return {
            "intent": intent,
            "needs_memory": False,
            "needs_retrieval": False,
            "clarify_prompt": clarify_prompt or "",
        }

    return {
        "intent": intent,
        "needs_memory": False,
        "needs_retrieval": False,
        "clarify_prompt": "",
    }


def greeting_node(state: MovieState) -> MovieState:
    answer = (
        "Hey! I’m MovieMate 🎬 Tell me what kind of movie you’re in the mood for — "
        "genre, vibe, actor, director, or a movie you already like."
    )
    return {
        "answer": answer,
        "messages": [AIMessage(content=answer)],
    }


def small_talk_node(state: MovieState) -> MovieState:
    answer = "Anytime — ask me for a movie recommendation whenever you’re ready."
    return {
        "answer": answer,
        "messages": [AIMessage(content=answer)],
    }


def clarify_node(state: MovieState) -> MovieState:
    answer = state.get("clarify_prompt") or infer_clarify_prompt(
        state["user_message"],
        state.get("messages", []),
    ) or (
        "What should I narrow by for you: genre, mood, actor, director, runtime, or a movie you want something similar to?"
    )
    return {
        "answer": answer,
        "messages": [AIMessage(content=answer)],
    }


def _extract_name(text: str) -> str | None:
    match = re.search(r"\bmy name is\s+([A-Za-z][A-Za-z'-]*)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip().title()
    return None


@traceable(run_type="chain", name="retrieve_memory_context")
def memory_retrieval_node(state: MovieState) -> MovieState:
    if not state.get("needs_memory", False):
        return {"memory_context": ""}

    user_message = state["user_message"].lower()
    messages = _get_prior_messages(state)

    relevant_lines: list[str] = []

    recent_human_messages = [
        msg for msg in messages
        if getattr(msg, "type", "") == "human" and isinstance(getattr(msg, "content", ""), str)
    ]

    # Targeted retrieval for memory questions
    if state.get("intent") == "memory_lookup":
        if "name" in user_message:
            for msg in reversed(recent_human_messages):
                content = msg.content.strip()
                if _extract_name(content):
                    relevant_lines.append(f"Known user detail: {content}")
                    break

        elif (
            "remember" in user_message
            or "earlier" in user_message
            or "what did i say" in user_message
            or "what do you know" in user_message
        ):
            for msg in recent_human_messages[-4:]:
                relevant_lines.append(f"Earlier user message: {msg.content.strip()}")

    if state.get("intent") == "followup":
        recent_history = _format_history(messages, max_messages=4)
        preference_lines = _extract_preference_lines(recent_human_messages, limit=3)

        if recent_history:
            relevant_lines.append("Recent conversation:\n" + recent_history)
        if preference_lines:
            relevant_lines.append(
                "Stable user preferences:\n" + "\n".join(preference_lines)
            )

    elif state.get("intent") == "movie_query":
        preference_lines = _extract_preference_lines(recent_human_messages, limit=3)
        if preference_lines:
            relevant_lines.append(
                "Stable user preferences:\n" + "\n".join(preference_lines)
            )

    memory_context = "\n\n".join(relevant_lines).strip()
    return {"memory_context": memory_context}


@traceable(run_type="chain", name="rewrite_query")
def rewrite_node(state: MovieState) -> MovieState:
    if not state.get("needs_retrieval", False):
        return {"rewritten_query": state["user_message"]}

    if state["intent"] != "followup":
        return {"rewritten_query": state["user_message"]}

    prior_messages = _get_prior_messages(state)
    rewritten_from_clarify = _rewrite_clarify_followup(prior_messages, state["user_message"])
    if rewritten_from_clarify:
        return {"rewritten_query": rewritten_from_clarify}

    history_text = _format_history(prior_messages, max_messages=4)

    prompt = QUERY_REWRITE_PROMPT.format(
        history=history_text,
        user_message=state["user_message"],
    )

    rewritten = llm.invoke(
        [
            ("system", "You rewrite movie queries for retrieval. Return only the rewritten query."),
            ("user", prompt),
        ]
    ).content.strip()

    return {"rewritten_query": rewritten or state["user_message"]}


@traceable(run_type="chain", name="retrieve_candidates")
def retrieve_node(state: MovieState) -> MovieState:
    if not state.get("needs_retrieval", False):
        return {"filters": {}, "retrieved_movies": []}

    query = state.get("rewritten_query") or state["user_message"]
    filters = extract_filters(query)
    query_embedding = get_query_embedding(query)
    top_k = TOP_K_FINAL if filters.get("person_name") else TOP_K_RETRIEVE

    results = search_movies(
        query_embedding=query_embedding,
        top_k=top_k,
        min_year=filters["min_year"],
        max_year=filters["max_year"],
        max_runtime=filters["max_runtime"],
        min_rating=filters["min_rating"],
        genre=filters["genre"],
        person_name=filters["person_name"],
    )

    return {
        "filters": filters,
        "retrieved_movies": results,
    }


@traceable(run_type="chain", name="rerank_candidates")
def rerank_node(state: MovieState) -> MovieState:
    candidates = state.get("retrieved_movies", [])
    if not candidates:
        return {"reranked_movies": [], "show_movie_cards": False}

    if state.get("filters", {}).get("person_name"):
        return {"reranked_movies": candidates[:TOP_K_FINAL]}

    query = state.get("rewritten_query") or state["user_message"]
    final_results = rerank_movies(
        query=query,
        candidates=candidates,
        top_n=TOP_K_FINAL,
    )
    return {"reranked_movies": final_results}


@traceable(run_type="chain", name="generate_answer")
def answer_node(state: MovieState) -> MovieState:
    context = format_context(state.get("reranked_movies", []))
    memory_context = state.get("memory_context", "")
    history_text = _format_history(_get_prior_messages(state), max_messages=4)
    show_movie_cards = should_show_movie_cards(
        user_message=state["user_message"],
        intent=state["intent"],
        has_results=bool(state.get("reranked_movies", [])),
    )

    prompt = ANSWER_PROMPT.format(
        history=history_text,
        memory_context=memory_context or "None",
        user_message=state["user_message"],
        context=context,
        response_mode="cards" if show_movie_cards else "text",
    )

    answer = llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("user", prompt),
        ]
    ).content.strip()
    answer = sanitize_answer(answer, show_movie_cards)

    return {
        "answer": answer,
        "show_movie_cards": show_movie_cards,
        "messages": [AIMessage(content=answer)],
    }


def prepare_input_state(session_id: str, user_message: str) -> MovieState:
    return {
        "session_id": session_id,
        "user_message": user_message,
        "messages": [HumanMessage(content=user_message)],
    }
