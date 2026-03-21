from fastapi import FastAPI
from pydantic import BaseModel
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

    return {
        "answer": result.get("answer", ""),
        "intent": result.get("intent", ""),
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
            for r in result.get("reranked_movies", [])
        ],
    }