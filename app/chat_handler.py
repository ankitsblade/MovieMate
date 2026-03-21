from app.config import TOP_K
from app.prompts import SYSTEM_PROMPT
from app.memory import add_message, get_history
from app.query_parser import extract_filters
from app.retriever import search_movies
from app.chat_model import generate_chat_response

from app.embeddings import get_query_embedding
def format_context(results: list[dict]) -> str:
    chunks = []

    for i, movie in enumerate(results, start=1):
        chunks.append(
            f"""Movie {i}
Title: {movie['primary_title']}
Type: {movie['title_type']}
Year: {movie['start_year']}
Runtime: {movie['runtime_minutes']}
Genres: {movie['genres']}
Rating: {movie['average_rating']}
Votes: {movie['num_votes']}
People: {movie['people_summary']}
Content: {movie['content']}
"""
        )

    return "\n\n".join(chunks)

def chat(session_id: str, user_message: str) -> dict:
    add_message(session_id, "user", user_message)

    filters = extract_filters(user_message)
    query_embedding = get_query_embedding(user_message)
    results = search_movies(
        query_embedding=query_embedding,
        top_k=TOP_K,
        min_year=filters["min_year"],
        max_runtime=filters["max_runtime"],
        min_rating=filters["min_rating"],
        genre=filters["genre"],
    )

    history = get_history(session_id, limit=6)
    history_text = "\n".join(
        [f"{msg['role']}: {msg['content']}" for msg in history]
    )

    context = format_context(results)

    user_prompt = f"""
Conversation history:
{history_text}

User query:
{user_message}

Retrieved movie context:
{context}

Answer only using the retrieved movie context.
If the context is insufficient, say so clearly.
"""

    answer = generate_chat_response(SYSTEM_PROMPT, user_prompt)
    add_message(session_id, "assistant", answer)

    return {
        "answer": answer,
        "results": [
            {
                "tconst": r["tconst"],
                "title": r["primary_title"],
                "year": r["start_year"],
                "genres": r["genres"],
                "rating": r["average_rating"],
                "runtime_minutes": r["runtime_minutes"],
            }
            for r in results
        ]
    }