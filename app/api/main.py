from time import perf_counter

from fastapi import FastAPI
from pydantic import BaseModel
from app.evals.service import evaluate_turn
from app.graph.build_graph import graph
from app.graph.nodes import prepare_input_state

app = FastAPI(title="MovieMate API")


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.get("/")
def root():
    return {"status": "ok", "service": "MovieMate API"}


@app.post("/chat")
def chat_endpoint(payload: ChatRequest):
    state = prepare_input_state(payload.session_id, payload.message)
    started_at = perf_counter()

    result = graph.invoke(
        state,
        config={
            "configurable": {"thread_id": payload.session_id},
            "tags": ["moviemate", "api"],
            "metadata": {
                "session_id": payload.session_id,
                "entrypoint": "fastapi",
            },
        },
    )
    latency_ms = int((perf_counter() - started_at) * 1000)
    intent = result.get("intent", "")
    show_movie_cards = result.get("show_movie_cards", False)
    reranked_movies = result.get("reranked_movies", [])
    card_movies = result.get("card_movies", [])

    signal = None
    if intent in {"movie_query", "followup"}:
        signal = result.get("signal")
        if signal:
            signal = {**signal, "latency_ms": latency_ms}
        else:
            signal = evaluate_turn(
                user_message=payload.message,
                intent=intent,
                answer=result.get("answer", ""),
                filters=result.get("filters", {}),
                reranked_movies=reranked_movies,
                memory_context=result.get("memory_context", ""),
                show_movie_cards=show_movie_cards,
                latency_ms=latency_ms,
            )

    return {
        "answer": result.get("answer", ""),
        "intent": intent,
        "show_movie_cards": show_movie_cards,
        "signal": signal,
        "results": [
            {
                "tconst": r["tconst"],
                "title": r["primary_title"],
                "year": r["start_year"],
                "genres": r["genres"],
                "rating": r["average_rating"],
                "runtime_minutes": r["runtime_minutes"],
                "rerank_score": r.get("rerank_score"),
            }
            for r in card_movies
        ] if show_movie_cards else [],
    }
