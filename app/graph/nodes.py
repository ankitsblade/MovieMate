from langchain_core.messages import HumanMessage, AIMessage
from langsmith import traceable

from app.config import TOP_K_RETRIEVE, TOP_K_FINAL
from app.graph.state import MovieState
from app.graph.router import classify_intent
from app.llm.chat_model import llm
from app.llm.prompts import SYSTEM_PROMPT, QUERY_REWRITE_PROMPT, ANSWER_PROMPT
from app.llm.embeddings import get_query_embedding
from app.retrieval.query_parser import extract_filters
from app.retrieval.retriever import search_movies
from app.retrieval.reranker import rerank_movies
from app.retrieval.formatter import format_context


@traceable(run_type="chain", name="router_node")
def router_node(state: MovieState) -> MovieState:
    intent = classify_intent(state["user_message"])
    return {"intent": intent}


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
    answer = (
        "I can help you find movies. Try asking something like:\n"
        "- Recommend mind-bending sci-fi movies\n"
        "- Movies like Interstellar\n"
        "- Dark thrillers under 2 hours"
    )
    return {
        "answer": answer,
        "messages": [AIMessage(content=answer)],
    }


@traceable(run_type="chain", name="rewrite_query")
def rewrite_node(state: MovieState) -> MovieState:
    if state["intent"] != "followup":
        return {"rewritten_query": state["user_message"]}

    history_text = "\n".join(
        f"{msg.type}: {msg.content}"
        for msg in state.get("messages", [])[-8:]
    )

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
    query = state.get("rewritten_query") or state["user_message"]
    filters = extract_filters(query)
    query_embedding = get_query_embedding(query)

    results = search_movies(
        query_embedding=query_embedding,
        top_k=TOP_K_RETRIEVE,
        min_year=filters["min_year"],
        max_year=filters["max_year"],
        max_runtime=filters["max_runtime"],
        min_rating=filters["min_rating"],
        genre=filters["genre"],
    )

    return {
        "filters": filters,
        "retrieved_movies": results,
    }


@traceable(run_type="chain", name="rerank_candidates")
def rerank_node(state: MovieState) -> MovieState:
    query = state.get("rewritten_query") or state["user_message"]
    candidates = state.get("retrieved_movies", [])
    final_results = rerank_movies(query=query, candidates=candidates, top_n=TOP_K_FINAL)
    return {"reranked_movies": final_results}


@traceable(run_type="chain", name="generate_answer")
def answer_node(state: MovieState) -> MovieState:
    context = format_context(state.get("reranked_movies", []))
    history_text = "\n".join(
        f"{msg.type}: {msg.content}"
        for msg in state.get("messages", [])[-8:]
    )

    prompt = ANSWER_PROMPT.format(
        history=history_text,
        user_message=state["user_message"],
        context=context,
    )

    answer = llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("user", prompt),
        ]
    ).content.strip()

    return {
        "answer": answer,
        "messages": [AIMessage(content=answer)],
    }


def prepare_input_state(session_id: str, user_message: str) -> MovieState:
    return {
        "session_id": session_id,
        "user_message": user_message,
        "messages": [HumanMessage(content=user_message)],
    }