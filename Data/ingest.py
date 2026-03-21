#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import Iterable, Sequence

import pandas as pd
import requests
import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

load_dotenv()

ALLOWED_DIMS = {384, 512, 768, 1024, 2048}


@dataclass
class MovieRow:
    tconst: str
    title_type: str | None
    primary_title: str | None
    is_adult: bool | None
    start_year: int | None
    runtime_minutes: int | None
    genres: str | None
    average_rating: float | None
    num_votes: int | None
    people_summary: str | None
    content: str
    embedding: list[float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest cleaned IMDb CSV into Supabase using NVIDIA embeddings."
    )
    parser.add_argument("--csv", required=True, help="Path to cleaned CSV file")
    parser.add_argument(
        "--embedding-dim",
        type=int,
        required=True,
        choices=sorted(ALLOWED_DIMS),
        help="Embedding dimension. Must match the Supabase vector column dimension.",
    )
    parser.add_argument("--batch-size", type=int, default=32, help="Texts per embedding API request")
    parser.add_argument("--insert-batch-size", type=int, default=128, help="Rows per database upsert batch")
    parser.add_argument("--create-table", action="store_true", help="Create extension/table/index if missing")
    parser.add_argument("--truncate-table", action="store_true", help="Delete all rows before inserting")
    parser.add_argument("--limit", type=int, default=None, help="Optional row limit for testing")
    return parser.parse_args()


def get_env(name: str, default: str | None = None, required: bool = True) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def batched(seq: Sequence, n: int) -> Iterable[Sequence]:
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def clean_optional_str(value):
    if pd.isna(value):
        return None
    s = str(value).strip()
    return s if s else None


def clean_optional_int(value):
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def clean_optional_float(value):
    if pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def clean_optional_bool(value):
    if pd.isna(value):
        return None
    s = str(value).strip().lower()
    if s in {"1", "true", "t", "yes"}:
        return True
    if s in {"0", "false", "f", "no"}:
        return False
    return None


def load_csv(path: str, limit: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(path)

    required_cols = {
        "tconst",
        "title_type",
        "primary_title",
        "is_adult",
        "start_year",
        "runtime_minutes",
        "genres",
        "average_rating",
        "num_votes",
        "people_summary",
        "content",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {sorted(missing)}")

    df["tconst"] = df["tconst"].astype(str).str.strip()
    df["content"] = df["content"].fillna("").astype(str).str.strip()

    df = df[df["tconst"] != ""]
    df = df[df["content"] != ""]
    df = df.drop_duplicates(subset=["tconst"], keep="first").reset_index(drop=True)

    if limit is not None:
        df = df.head(limit).copy()

    return df


def get_nvidia_embeddings(
    texts: list[str],
    api_key: str,
    model: str,
    base_url: str,
    embedding_dim: int,
    input_type: str = "passage",
    timeout: int = 120,
    max_retries: int = 6,
) -> list[list[float]]:
    url = f"{base_url.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": texts,
        "input_type": input_type,
        "dimensions": embedding_dim,
        "encoding_format": "float",
        "truncate": "NONE",
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)

            if resp.status_code == 400:
                raise RuntimeError(f"NVIDIA 400 error: {resp.text}")

            if resp.status_code in {429, 500, 502, 503, 504}:
                wait = min(2 ** attempt, 30)
                print(f"[warn] NVIDIA API {resp.status_code}; retrying in {wait}s")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            data = resp.json()

            if "data" not in data:
                raise RuntimeError(f"Unexpected NVIDIA response: {data}")

            items = sorted(data["data"], key=lambda x: x["index"])
            embeddings = [item["embedding"] for item in items]

            if len(embeddings) != len(texts):
                raise RuntimeError(
                    f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                )

            for emb in embeddings:
                if len(emb) != embedding_dim:
                    raise RuntimeError(
                        f"Embedding length mismatch: expected {embedding_dim}, got {len(emb)}"
                    )

            return embeddings

        except Exception as exc:
            last_error = exc
            if "NVIDIA 400 error:" in str(exc):
                raise
            wait = min(2 ** attempt, 30)
            print(f"[warn] Embedding request failed ({exc}); retrying in {wait}s")
            time.sleep(wait)

    raise RuntimeError(f"NVIDIA embedding request failed after retries: {last_error}")


def ensure_schema(conn: psycopg.Connection, embedding_dim: int) -> None:
    ddl = f"""
    create extension if not exists vector with schema extensions;

    create table if not exists movies (
      id bigint generated always as identity primary key,
      tconst text unique not null,
      title_type text,
      primary_title text,
      is_adult boolean,
      start_year int,
      runtime_minutes int,
      genres text,
      average_rating double precision,
      num_votes int,
      people_summary text,
      content text not null,
      embedding extensions.vector({embedding_dim})
    );
    """

    index_sql = """
    create index if not exists movies_embedding_hnsw
    on movies
    using hnsw (embedding vector_ip_ops);
    """

    with conn.cursor() as cur:
        cur.execute(ddl)
        cur.execute(index_sql)
    conn.commit()


def truncate_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("truncate table movies restart identity;")
    conn.commit()


def upsert_rows(conn: psycopg.Connection, rows: list[MovieRow]) -> None:
    sql = """
    insert into movies (
        tconst,
        title_type,
        primary_title,
        is_adult,
        start_year,
        runtime_minutes,
        genres,
        average_rating,
        num_votes,
        people_summary,
        content,
        embedding
    )
    values (
        %(tconst)s,
        %(title_type)s,
        %(primary_title)s,
        %(is_adult)s,
        %(start_year)s,
        %(runtime_minutes)s,
        %(genres)s,
        %(average_rating)s,
        %(num_votes)s,
        %(people_summary)s,
        %(content)s,
        %(embedding)s
    )
    on conflict (tconst) do update set
        title_type      = excluded.title_type,
        primary_title   = excluded.primary_title,
        is_adult        = excluded.is_adult,
        start_year      = excluded.start_year,
        runtime_minutes = excluded.runtime_minutes,
        genres          = excluded.genres,
        average_rating  = excluded.average_rating,
        num_votes       = excluded.num_votes,
        people_summary  = excluded.people_summary,
        content         = excluded.content,
        embedding       = excluded.embedding;
    """

    payload = [
        {
            "tconst": r.tconst,
            "title_type": r.title_type,
            "primary_title": r.primary_title,
            "is_adult": r.is_adult,
            "start_year": r.start_year,
            "runtime_minutes": r.runtime_minutes,
            "genres": r.genres,
            "average_rating": r.average_rating,
            "num_votes": r.num_votes,
            "people_summary": r.people_summary,
            "content": r.content,
            "embedding": r.embedding,
        }
        for r in rows
    ]

    with conn.cursor() as cur:
        cur.executemany(sql, payload)
    conn.commit()


def main() -> None:
    args = parse_args()

    nvidia_api_key = get_env("NVIDIA_API_KEY")
    db_url = get_env("SUPABASE_DB_URL")
    nvidia_model = get_env("NVIDIA_MODEL", default="nvidia/llama-nemotron-embed-1b-v2", required=False)
    nvidia_base_url = get_env("NVIDIA_BASE_URL", default="https://integrate.api.nvidia.com/v1", required=False)

    print("[info] Loading CSV...")
    df = load_csv(args.csv, limit=args.limit)
    print(f"[info] Rows to process: {len(df)}")
    print(f"[info] Embedding dimension: {args.embedding_dim}")

    print("[info] Connecting to Supabase Postgres...")
    conn = psycopg.connect(db_url)
    register_vector(conn)

    try:
        if args.create_table:
            print("[info] Ensuring schema exists...")
            ensure_schema(conn, args.embedding_dim)

        if args.truncate_table:
            print("[info] Truncating table...")
            truncate_table(conn)

        total = len(df)
        processed = 0
        upsert_buffer: list[MovieRow] = []

        rows = df.to_dict(orient="records")

        for chunk in batched(rows, args.batch_size):
            texts = [str(r["content"]) for r in chunk]
            embeddings = get_nvidia_embeddings(
                texts=texts,
                api_key=nvidia_api_key,
                model=nvidia_model,
                base_url=nvidia_base_url,
                embedding_dim=args.embedding_dim,
                input_type="passage",
            )

            for rec, emb in zip(chunk, embeddings):
                upsert_buffer.append(
                    MovieRow(
                        tconst=str(rec["tconst"]).strip(),
                        title_type=clean_optional_str(rec.get("title_type")),
                        primary_title=clean_optional_str(rec.get("primary_title")),
                        is_adult=clean_optional_bool(rec.get("is_adult")),
                        start_year=clean_optional_int(rec.get("start_year")),
                        runtime_minutes=clean_optional_int(rec.get("runtime_minutes")),
                        genres=clean_optional_str(rec.get("genres")),
                        average_rating=clean_optional_float(rec.get("average_rating")),
                        num_votes=clean_optional_int(rec.get("num_votes")),
                        people_summary=clean_optional_str(rec.get("people_summary")),
                        content=str(rec["content"]).strip(),
                        embedding=emb,
                    )
                )

            if len(upsert_buffer) >= args.insert_batch_size:
                upsert_rows(conn, upsert_buffer)
                processed += len(upsert_buffer)
                print(f"[info] Upserted {processed}/{total} rows")
                upsert_buffer.clear()

        if upsert_buffer:
            upsert_rows(conn, upsert_buffer)
            processed += len(upsert_buffer)
            print(f"[info] Upserted {processed}/{total} rows")

        print("[done] Ingestion complete.")

    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[abort] Interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)