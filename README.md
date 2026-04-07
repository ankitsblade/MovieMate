# MovieMate

MovieMate is a stateful retrieval-augmented movie chatbot built for an NLP course project. It combines a cleaned movie corpus, vector retrieval, LLM-based query understanding, reranking, response generation, and turn-level evaluation into a single conversational system.

The project is centered on the NLP pipeline rather than the UI. The frontend is only a thin usability layer over the backend API.

## What The System Does

- accepts natural-language movie queries such as actor, genre, runtime, year, and follow-up refinements
- keeps session-level conversational state
- retrieves grounded movie evidence from a PostgreSQL + pgvector store
- generates concise grounded responses and optional movie cards
- evaluates each retrieval turn with both deterministic checks and an LLM judge
- retries weak responses automatically when the evaluation score falls below a threshold

## High-Level Architecture

The runtime pipeline is:

1. User message arrives at the FastAPI backend.
2. A LangGraph state machine routes the turn into greeting, clarification, memory lookup, or retrieval flow.
3. For retrieval turns, the system:
   - gathers relevant memory context
   - rewrites follow-up queries when needed
   - parses structured retrieval constraints with an LLM-first parser
   - embeds the query
   - retrieves candidate movies from Supabase/Postgres with pgvector
   - reranks the candidates
4. The assistant produces a grounded answer from retrieved evidence.
5. The evaluation stack scores retrieval quality, response quality, and groundedness.
6. If the score is too low, the answer is regenerated once with stricter guidance.
7. The final response and session state are checkpointed in Postgres.

## Repository Structure

```text
app/
  api/          FastAPI entrypoint
  evals/        retrieval/response evaluation and LLM judge
  graph/        LangGraph state machine, nodes, routing, state
  llm/          chat model, embeddings, prompts
  memory/       Postgres-backed checkpointing
  retrieval/    parser, vector retrieval, reranking, context formatting
  rules/        heuristic fallback rules and deterministic response helpers
Data/
  dataprep.py   dataset cleaning and top-N selection
  ingest.py     embedding generation + Supabase ingestion
  data.ipynb    exploratory notebook / intermediate data work
frontend/       optional interface layer
tests/          regression tests for retrieval, routing, evals, and heuristics
report/         Typst project report source
```

## Why These Data Sources

We chose the official IMDb public datasets as the primary source instead of relying on scraping or a single Kaggle export.

Reasons:

- stable identifiers: official IMDb tables provide consistent title and name keys such as `tconst` and `nconst`, which makes merging ratings, crew, cast, and title metadata much cleaner
- reproducibility: a documented tabular source is easier to rerun than a scraper that depends on unstable HTML structure
- richer schema: the official files expose titles, ratings, principals, crew, and names separately, which supports more controllable dataset construction
- less noise from third-party preprocessing: many Kaggle datasets are useful, but they often flatten, rename, or drop fields and make provenance less clear
- lower operational risk: scraping introduces fragility, rate limiting, and site-policy concerns that are unnecessary when a structured source already exists

The repo currently contains:

- a cleaned full corpus for ingestion: `Data/imdb_cleaned_for_supabase.csv`
- a smaller experimental subset: `Data/imdb_top_10000_movies.csv`
- the original IMDb `.tsv.gz` files used in dataset construction

Local dataset statistics from the current artifacts:

- cleaned full corpus size: `1,305,051` movies
- year range: `1894` to `2026`
- mean rating: `6.394`
- mean runtime: `85.26` minutes
- most common genres in the full cleaned corpus: `Drama`, `Documentary`, `Comedy`, `Action`, `Romance`
- top-10k experimental subset size: `10,000` movies
- mean rating of top-10k subset: `7.627`

## Why These Models

Current default models from [`app/config.py`](/home/ankit/Development/MovieMate/app/config.py):

- chat / routing / parsing / judging: `openai/gpt-oss-120b`
- embeddings: `nvidia/llama-nemotron-embed-1b-v2`
- reranker: `nvidia/llama-nemotron-rerank-1b-v2`

Justification:

- `gpt-oss-120b` is used where instruction following and structured output matter most: routing, filter extraction, answer generation, and judging
- the NVIDIA embedding model is specialized for dense retrieval and supports separate query/passage modes
- the NVIDIA reranker gives a second-stage relevance signal after vector recall, which improves the quality of the final shortlist without having to overfit retrieval heuristics
- keeping embeddings, reranking, and chat on a compatible hosted stack reduces integration complexity during experimentation

## Why LangGraph And LangSmith

### LangGraph

LangGraph is used because the system is not a single prompt. It is a stateful workflow with explicit branching:

- greeting and small talk
- clarification turns
- memory retrieval
- follow-up rewriting
- retrieval
- reranking
- answer generation
- evaluation
- retry on weak responses

This is easier to reason about as a graph than as a single chain. The graph definition lives in [`app/graph/build_graph.py`](/home/ankit/Development/MovieMate/app/graph/build_graph.py), and node logic lives in [`app/graph/nodes.py`](/home/ankit/Development/MovieMate/app/graph/nodes.py).

### LangSmith

LangSmith tracing is useful because retrieval systems fail in multi-stage ways. We used tracing to inspect:

- routing mistakes
- dropped person filters
- retrieval misses
- reranker latency
- eval/judge mismatches
- low-signal retries

This was especially helpful when fixing person-name ambiguity, stale judge state, and evidence-summary issues in the evaluator.

## Why We Still Keep Some Heuristics

The system is now LLM-first in the main interpretation layers:

- routing is LLM-first with heuristic fallback
- retrieval filter extraction is LLM-first with heuristic fallback

Some heuristics are still kept intentionally because they serve as guardrails rather than the primary intelligence:

- exact or boundary-based person-name validation
- fallback query parsing when the LLM parser fails
- clarification fallback logic
- incomplete-answer detection
- deterministic card-mode summaries

The design principle is:

- use LLMs for interpretation and flexible language understanding
- use deterministic logic for hard constraints, safety checks, and recovery behavior

## Reproducing The Project

### 1. Prerequisites

- Python `3.14` or compatible with the current project configuration
- `uv`
- a PostgreSQL / Supabase instance with pgvector support
- an NVIDIA API key for embeddings and reranking
- optional LangSmith credentials for tracing
- optional Node.js if you want to run the frontend

### 2. Install Python Dependencies

```bash
uv sync
```

### 3. Create Environment Variables

Copy the example file:

```bash
cp .env.example .env
```

Then fill in the required secrets, especially:

- `NVIDIA_API_KEY`
- `SUPABASE_DB_URL`

### 4. Prepare Or Reuse The Dataset

There are two practical paths.

#### Quick Reproduction

Use the provided cleaned CSV directly:

- `Data/imdb_cleaned_for_supabase.csv` for the full cleaned corpus
- `Data/imdb_top_10000_movies.csv` for a smaller experiment

#### Dataset Rebuild Path

If you want to reconstruct the intermediate dataset from local data artifacts:

1. start from the raw IMDb TSV files in `Data/`
2. use the notebook `Data/data.ipynb` or intermediate CSV workflow to assemble movie metadata
3. run the preprocessing script:

```bash
uv run python Data/dataprep.py \
  --input Data/ImdbData.csv \
  --output Data/imdb_top_10000_movies.csv \
  --top-n 10000 \
  --min-votes 1000
```

### 5. Ingest The Dataset Into Supabase / Postgres

Example using the cleaned full corpus:

```bash
uv run python Data/ingest.py \
  --csv Data/imdb_cleaned_for_supabase.csv \
  --embedding-dim 384 \
  --batch-size 32 \
  --insert-batch-size 128 \
  --create-table
```

For a smaller experiment, replace the CSV with `Data/imdb_top_10000_movies.csv`.

### 6. Run The Backend

```bash
uv run uvicorn app.api.main:app --reload
```

Backend health check:

```bash
curl http://127.0.0.1:8000/
```

### 7. Optional Frontend

The frontend is not part of the core NLP contribution, but if you want the local interface:

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend at `http://127.0.0.1:8000`.

## Evaluation Strategy

Evaluation is implemented in [`app/evals/service.py`](/home/ankit/Development/MovieMate/app/evals/service.py) and [`app/evals/judge.py`](/home/ankit/Development/MovieMate/app/evals/judge.py).

We use a hybrid evaluation design:

- algorithmic retrieval checks:
  - filter alignment
  - lexical query overlap
- response consistency checks:
  - completeness
  - count consistency
  - card-mode discipline
- LLM judge:
  - retrieval relevance
  - evidence alignment
  - groundedness
  - helpfulness
  - presentation discipline

This hybrid design was chosen because purely heuristic evaluation was too brittle, while purely LLM-based judging sometimes hallucinated about the evidence it was given.

## Main Findings During Development

- person-name queries are a common failure mode in movie retrieval, especially with short or ambiguous names
- letting the answer model freely list titles in card mode increased hallucination risk, so card-mode summaries were made deterministic
- LLM judges can mis-evaluate a turn if they only see a partial evidence slice, so the evaluator was changed to summarize the full retrieved set
- memory improves follow-up quality, but too much raw history can increase hallucination risk, so memory usage had to be made selective
- LLM-first routing and parsing work well, but fallback rules remain important for failure recovery and exact-name safety

## Running Tests

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python -m unittest discover -s tests
```

## Report

The assignment-style Typst report lives at:

- [`report/project_report.typ`](/home/ankit/Development/MovieMate/report/project_report.typ)

Compiled Typst artifacts are ignored in Git via `.gitignore`.
