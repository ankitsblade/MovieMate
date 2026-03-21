from langgraph.graph import StateGraph, START, END
from app.graph.state import MovieState
from app.graph.nodes import (
    router_node,
    greeting_node,
    small_talk_node,
    clarify_node,
    rewrite_node,
    retrieve_node,
    rerank_node,
    answer_node,
)
from app.memory.history import checkpointer


def route_after_router(state: MovieState) -> str:
    intent = state["intent"]
    if intent == "greeting":
        return "greeting"
    if intent == "small_talk":
        return "small_talk"
    if intent == "clarify":
        return "clarify"
    return "movie_branch"


builder = StateGraph(MovieState)

builder.add_node("router", router_node)
builder.add_node("greeting", greeting_node)
builder.add_node("small_talk", small_talk_node)
builder.add_node("clarify", clarify_node)
builder.add_node("rewrite", rewrite_node)
builder.add_node("retrieve", retrieve_node)
builder.add_node("rerank", rerank_node)
builder.add_node("answer", answer_node)

builder.add_edge(START, "router")
builder.add_conditional_edges(
    "router",
    route_after_router,
    {
        "greeting": "greeting",
        "small_talk": "small_talk",
        "clarify": "clarify",
        "movie_branch": "rewrite",
    },
)

builder.add_edge("rewrite", "retrieve")
builder.add_edge("retrieve", "rerank")
builder.add_edge("rerank", "answer")

builder.add_edge("greeting", END)
builder.add_edge("small_talk", END)
builder.add_edge("clarify", END)
builder.add_edge("answer", END)

graph = builder.compile(checkpointer=checkpointer)