import uuid
from app.chat_handler import chat

def main():
    session_id = str(uuid.uuid4())
    print("MovieMate CLI Chat")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        response = chat(session_id, user_input)

        print("\nBot:", response["answer"])
        print("\nTop retrieved movies:")
        for movie in response["results"]:
            print(
                f"- {movie['title']} ({movie['year']}) | "
                f"{movie['genres']} | Rating: {movie['rating']} | "
                f"{movie['runtime_minutes']} min"
            )
        print()

if __name__ == "__main__":
    main()