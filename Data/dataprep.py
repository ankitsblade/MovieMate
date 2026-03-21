import pandas as pd
import numpy as np

# ---------------------------
# Load CSV
# ---------------------------
df = pd.read_csv("ImdbData.csv")

print("Original shape:", df.shape)

# ---------------------------
# Rename columns (standardize)
# ---------------------------
df.columns = [col.strip().lower() for col in df.columns]

df = df.rename(columns={
    "titletype": "title_type",
    "primarytitle": "primary_title",
    "isadult": "is_adult",
    "startyear": "start_year",
    "runtimeminutes": "runtime_minutes",
    "averagerating": "average_rating",
    "numvotes": "num_votes"
})

# ---------------------------
# Drop duplicates
# ---------------------------
df = df.drop_duplicates(subset=["tconst"])

# ---------------------------
# Clean text columns
# ---------------------------
text_cols = ["tconst", "title_type", "primary_title", "genres", "people_summary"]

for col in text_cols:
    df[col] = df[col].fillna("").astype(str).str.strip()

# ---------------------------
# Remove rows with no title
# ---------------------------
df = df[df["primary_title"] != ""]

# ---------------------------
# Convert numeric columns
# ---------------------------
df["start_year"] = pd.to_numeric(df["start_year"], errors="coerce")
df["runtime_minutes"] = pd.to_numeric(df["runtime_minutes"], errors="coerce")
df["average_rating"] = pd.to_numeric(df["average_rating"], errors="coerce")
df["num_votes"] = pd.to_numeric(df["num_votes"], errors="coerce")

# ---------------------------
# Clean is_adult
# ---------------------------
df["is_adult"] = df["is_adult"].apply(lambda x: 1 if str(x) in ["1", "True", "true"] else 0)

# ---------------------------
# Clean genres
# ---------------------------
df["genres"] = df["genres"].apply(
    lambda x: ", ".join([g.strip() for g in x.split(",") if g.strip()]) if x else ""
)

# ---------------------------
# Clean people summary
# ---------------------------
df["people_summary"] = df["people_summary"].apply(
    lambda x: " | ".join([p.strip() for p in x.split("|") if p.strip()]) if x else ""
)

# ---------------------------
# Basic sanity filtering (optional but recommended)
# ---------------------------
df.loc[(df["start_year"] < 1870) | (df["start_year"] > 2026), "start_year"] = np.nan
df.loc[df["runtime_minutes"] <= 0, "runtime_minutes"] = np.nan
df.loc[(df["average_rating"] < 0) | (df["average_rating"] > 10), "average_rating"] = np.nan
df.loc[df["num_votes"] < 0, "num_votes"] = np.nan

# ---------------------------
# OPTIONAL: remove adult content
# ---------------------------
df = df[df["is_adult"] == 0]

# ---------------------------
# Build content column (IMPORTANT for embeddings)
# ---------------------------
def build_content(row):
    parts = []

    if row["primary_title"]:
        parts.append(f"Title: {row['primary_title']}")

    if row["title_type"]:
        parts.append(f"Type: {row['title_type']}")

    if not pd.isna(row["start_year"]):
        parts.append(f"Year: {int(row['start_year'])}")

    if not pd.isna(row["runtime_minutes"]):
        parts.append(f"Runtime: {int(row['runtime_minutes'])} minutes")

    if row["genres"]:
        parts.append(f"Genres: {row['genres']}")

    if not pd.isna(row["average_rating"]):
        parts.append(f"IMDb rating: {row['average_rating']}")

    if not pd.isna(row["num_votes"]):
        parts.append(f"Votes: {int(row['num_votes'])}")

    if row["people_summary"]:
        parts.append(f"People: {row['people_summary']}")

    return "\n".join(parts)

df["content"] = df.apply(build_content, axis=1)

# ---------------------------
# Drop empty content rows
# ---------------------------
df = df[df["content"].str.strip() != ""]

print("Final shape:", df.shape)

# ---------------------------
# Save cleaned file
# ---------------------------
df.to_csv("imdb_cleaned_for_supabase.csv", index=False)

print("✅ Cleaned file saved: imdb_cleaned_for_supabase.csv")