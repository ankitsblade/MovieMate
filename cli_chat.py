import uuid
from app.graph.build_graph import graph
from app.graph.nodes import prepare_input_state


def main():
    session_id = str(uuid.uuid4())
    print("MovieMate CLI Chat")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        state = prepare_input_state(session_id, user_input)

        result = graph.invoke(
            state,
            config={
                "configurable": {"thread_id": session_id},
                "tags": ["moviemate", "cli"],
                "metadata": {
                    "session_id": session_id,
                    "entrypoint": "cli",
                },
            },
        )

        print(f"\nIntent: {result.get('intent')}")
        print(f"Bot: {result.get('answer')}")

        reranked = result.get("reranked_movies", [])
        if reranked:
            print("\nTop retrieved movies:")
            for movie in reranked:
                print(
                    f"- {movie['primary_title']} ({movie['start_year']}) | "
                    f"{movie['genres']} | Rating: {movie['average_rating']} | "
                    f"{movie['runtime_minutes']} min | rerank={movie.get('rerank_score')}"
                )
        print()


if __name__ == "__main__":
    main()