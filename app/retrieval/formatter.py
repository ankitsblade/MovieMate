def format_context(results: list[dict]) -> str:
    if not results:
        return "No relevant movies retrieved."

    chunks = []
    for i, movie in enumerate(results, start=1):
        chunks.append(
            f"""Movie {i}
Title: {movie.get('primary_title')}
Type: {movie.get('title_type')}
Year: {movie.get('start_year')}
Runtime: {movie.get('runtime_minutes')}
Genres: {movie.get('genres')}
Rating: {movie.get('average_rating')}
Votes: {movie.get('num_votes')}
People: {movie.get('people_summary')}
Content: {movie.get('content')}
"""
        )
    return "\n\n".join(chunks)