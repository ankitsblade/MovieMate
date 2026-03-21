from typing import Literal, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class MovieState(TypedDict, total=False):
    session_id: str
    user_message: str

    intent: Literal[
        "greeting",
        "small_talk",
        "movie_query",
        "followup",
        "memory_lookup",
        "clarify",
    ]

    needs_memory: bool
    needs_retrieval: bool

    rewritten_query: str
    filters: dict

    memory_context: str
    retrieved_movies: list[dict]
    reranked_movies: list[dict]

    answer: str

    messages: Annotated[list[AnyMessage], add_messages]