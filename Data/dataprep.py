from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean IMDb CSV and keep only the top-N movies."
    )
    parser.add_argument("--input", required=True, help="Path to input CSV")
    parser.add_argument(
        "--output",
        default="imdb_top_10000_movies.csv",
        help="Path to output CSV",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10000,
        help="Number of top movies to keep",
    )
    parser.add_argument(
        "--min-votes",
        type=int,
        default=1000,
        help="Minimum votes required before ranking",
    )
    return parser.parse_args()


def clean_text(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    if s.lower() in {"nan", "none", "null"}:
        return ""
    return " ".join(s.split())


def to_int(x):
    if pd.isna(x):
        return pd.NA
    try:
        return int(float(x))
    except Exception:
        return pd.NA


def to_float(x):
    if pd.isna(x):
        return np.nan
    try:
        return float(x)
    except Exception:
        return np.nan


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    rename_map = {
        "titletype": "title_type",
        "primarytitle": "primary_title",
        "isadult": "is_adult",
        "startyear": "start_year",
        "runtimeminutes": "runtime_minutes",
        "averagerating": "average_rating",
        "numvotes": "num_votes",
    }
    return df.rename(columns=rename_map)


def build_content(row: pd.Series) -> str:
    parts = []

    if clean_text(row.get("primary_title")):
        parts.append(f"Title: {clean_text(row.get('primary_title'))}")

    if clean_text(row.get("title_type")):
        parts.append(f"Type: {clean_text(row.get('title_type'))}")

    if pd.notna(row.get("start_year")):
        parts.append(f"Year: {int(row['start_year'])}")

    if pd.notna(row.get("runtime_minutes")):
        parts.append(f"Runtime: {int(row['runtime_minutes'])} minutes")

    if clean_text(row.get("genres")):
        parts.append(f"Genres: {clean_text(row.get('genres'))}")

    if pd.notna(row.get("average_rating")):
        parts.append(f"IMDb rating: {row['average_rating']}")

    if pd.notna(row.get("num_votes")):
        parts.append(f"Votes: {int(row['num_votes'])}")

    if clean_text(row.get("people_summary")):
        parts.append(f"People: {clean_text(row.get('people_summary'))}")

    return "\n".join(parts).strip()


def main() -> None:
    args = parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    df = pd.read_csv(input_path)
    df = normalize_columns(df)

    required = {
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
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    text_cols = ["tconst", "title_type", "primary_title", "genres", "people_summary"]
    for col in text_cols:
        df[col] = df[col].apply(clean_text)

    df["start_year"] = df["start_year"].apply(to_int).astype("Int64")
    df["runtime_minutes"] = df["runtime_minutes"].apply(to_int).astype("Int64")
    df["num_votes"] = df["num_votes"].apply(to_int).astype("Int64")
    df["average_rating"] = df["average_rating"].apply(to_float)
    df["is_adult"] = df["is_adult"].apply(
        lambda x: 1 if str(x).strip().lower() in {"1", "true", "yes"} else 0
    ).astype("Int64")

    df = df[df["tconst"] != ""].copy()
    df = df[df["primary_title"] != ""].copy()
    df = df.drop_duplicates(subset=["tconst"], keep="first").copy()

    # Keep only movies
    df = df[df["title_type"].str.lower() == "movie"].copy()

    # Basic quality filters
    df = df[df["average_rating"].notna()].copy()
    df = df[df["num_votes"].fillna(0) >= args.min_votes].copy()

    # Sanity cleanup
    df.loc[(df["start_year"] < 1870) | (df["start_year"] > 2100), "start_year"] = pd.NA
    df.loc[df["runtime_minutes"] <= 0, "runtime_minutes"] = pd.NA
    df.loc[(df["average_rating"] < 0) | (df["average_rating"] > 10), "average_rating"] = np.nan
    df.loc[df["num_votes"] < 0, "num_votes"] = pd.NA

    # Rank by rating first, then votes
    df = df.sort_values(
        by=["average_rating", "num_votes"],
        ascending=[False, False],
        kind="mergesort",
    ).copy()

    # Keep top N
    df = df.head(args.top_n).copy()

    # Build embedding text
    df["content"] = df.apply(build_content, axis=1)
    df = df[df["content"].str.strip() != ""].copy()

    final_cols = [
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
    ]
    df = df[final_cols]

    df.to_csv(output_path, index=False)

    print(f"Saved: {output_path}")
    print(f"Final rows: {len(df)}")
    print("\nPreview:")
    print(df[["tconst", "primary_title", "is_adult", "average_rating", "num_votes"]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()