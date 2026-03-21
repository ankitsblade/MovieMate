from app.db import get_connection

def search_movies(
    query_embedding,
    top_k=8,
    min_year=None,
    max_runtime=None,
    min_rating=None,
    genre=None,
):
    emb_str = "[" + ",".join(map(str, query_embedding)) + "]"

    conditions = ["coalesce(is_adult, false) = false"]
    params = []

    if min_year is not None:
        conditions.append("start_year >= %s")
        params.append(min_year)

    if max_runtime is not None:
        conditions.append("runtime_minutes <= %s")
        params.append(max_runtime)

    if min_rating is not None:
        conditions.append("average_rating >= %s")
        params.append(min_rating)

    if genre is not None:
        conditions.append("genres ilike %s")
        params.append(f"%{genre}%")

    where_clause = " and ".join(conditions)

    sql = f"""
    select
        id,
        tconst,
        primary_title,
        title_type,
        start_year,
        runtime_minutes,
        genres,
        average_rating,
        num_votes,
        people_summary,
        content,
        embedding <#> %s::vector as distance
    from public.movies
    where {where_clause}
    order by embedding <#> %s::vector
    limit %s;
    """

    final_params = [emb_str, *params, emb_str, top_k]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, final_params)
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "tconst": row[1],
            "primary_title": row[2],
            "title_type": row[3],
            "start_year": row[4],
            "runtime_minutes": row[5],
            "genres": row[6],
            "average_rating": row[7],
            "num_votes": row[8],
            "people_summary": row[9],
            "content": row[10],
            "distance": row[11],
        }
        for row in rows
    ]