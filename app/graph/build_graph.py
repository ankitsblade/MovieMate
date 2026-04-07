from langgraph.graph import StateGraph, START, END

from app.graph.state import MovieState
from app.graph.nodes import (
    router_node,
    greeting_node,
    small_talk_node,
    clarify_node,
    memory_retrieval_node,
    rewrite_node,
    retrieve_node,
    rerank_node,
    answer_node,
    evaluate_answer_node,
    prepare_retry_node,
    finalize_answer_node,
    should_retry_answer,
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

    return "context_branch"


builder = StateGraph(MovieState)

builder.add_node("router", router_node)
builder.add_node("greeting", greeting_node)
builder.add_node("small_talk", small_talk_node)
builder.add_node("clarify", clarify_node)

builder.add_node("memory_retrieval", memory_retrieval_node)
builder.add_node("rewrite", rewrite_node)
builder.add_node("retrieve", retrieve_node)
builder.add_node("rerank", rerank_node)
builder.add_node("answer", answer_node)
builder.add_node("evaluate_answer", evaluate_answer_node)
builder.add_node("prepare_retry", prepare_retry_node)
builder.add_node("finalize_answer", finalize_answer_node)

builder.add_edge(START, "router")

builder.add_conditional_edges(
    "router",
    route_after_router,
    {
        "greeting": "greeting",
        "small_talk": "small_talk",
        "clarify": "clarify",
        "context_branch": "memory_retrieval",
    },
)

builder.add_edge("memory_retrieval", "rewrite")
builder.add_edge("rewrite", "retrieve")
builder.add_edge("retrieve", "rerank")
builder.add_edge("rerank", "answer")
builder.add_edge("answer", "evaluate_answer")

builder.add_conditional_edges(
    "evaluate_answer",
    lambda state: "retry" if should_retry_answer(state) else "finalize",
    {
        "retry": "prepare_retry",
        "finalize": "finalize_answer",
    },
)
builder.add_edge("prepare_retry", "answer")

builder.add_edge("greeting", END)
builder.add_edge("small_talk", END)
builder.add_edge("clarify", END)
builder.add_edge("finalize_answer", END)

graph = builder.compile(checkpointer=checkpointer)

with open("moviemate_graph.png", "wb") as f:
    f.write(graph.get_graph(xray=True).draw_mermaid_png())
