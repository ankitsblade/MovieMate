#set page(
  margin: (x: 1in, y: 0.9in),
  numbering: "1",
)

#set text(size: 11pt)
#set par(justify: true)

#let project-title = "MovieMate: Exploring Conversational AI for Intelligent Movie Search and Recommendation"
#let course-name = "NLP Course Assignment"
#let authors = "Fill in team members here"
#let institution = "Fill in department / university here"

#align(center)[
  #text(18pt, weight: "bold")[#project-title]
  #v(0.6em)
  #text(11pt)[#course-name]
  #linebreak()
  #text(11pt)[#authors]
  #linebreak()
  #text(11pt)[#institution]
]

#v(1.2em)

= Abstract

This project investigates how a conversational NLP system can support flexible movie search and recommendation over a large, structured movie corpus. The resulting system, MovieMate, combines official IMDb-derived metadata, dense retrieval, reranking, stateful dialogue management, retrieval-augmented response generation, and turn-level evaluation. The main objective was not to build a polished consumer interface, but to study how language models and retrieval methods can be integrated into a controllable conversational information system.

The final system accepts natural language queries such as actor-based search, genre and runtime constraints, release-year filtering, and multi-turn refinements. It uses a PostgreSQL plus pgvector store for semantic retrieval, a LangGraph workflow for conversational state transitions, and an LLM-first interpretation layer for routing and structured query parsing. Evaluation combines algorithmic checks and an LLM judge, and low-scoring answers are regenerated once with stricter guidance. The frontend is intentionally treated as a thin usability layer and is not a central part of the NLP discussion in this report.

= 1. Project Overview And Motivation

Traditional movie-search interfaces are effective when users know exactly what to type, but they struggle with conversational requests such as:

- "Feel-good movies under two hours"
- "Movies similar to Interstellar but shorter"
- "What movies feature Ana de Armas?"
- "Give me darker thrillers than the last list"

The assignment brief emphasizes conversational movie search, retrieval, preprocessing, evaluation, and architectural understanding. We therefore framed the project as an NLP system design problem: how do we convert natural language into reliable retrieval operations while preserving conversational flexibility and minimizing hallucination?

Our final answer was a retrieval-augmented architecture rather than an end-to-end generative system. The reasons were practical and methodological:

- movie titles, cast, runtime, and years are factual fields and should come from a curated source rather than be invented by the model
- user queries often contain hard constraints, such as actor name or runtime limit, which are better enforced with structured retrieval than with free-form generation
- the assignment outcomes emphasize understanding how retrieval and language models can be integrated, making a RAG-style design a stronger fit than a pure-chat baseline

= 2. Dataset Acquisition And Construction

== 2.1 Why We Chose Official IMDb Data

The project brief explicitly encouraged students to explore scraping, APIs, or existing open datasets. We considered these categories conceptually, but chose the official IMDb public datasets as the primary source.

This choice was motivated by several factors:

- Standardized identifiers. The IMDb files use stable identifiers such as `tconst` for titles and `nconst` for names. These identifiers are crucial when joining multiple tables such as titles, ratings, principals, crew, and people.
- Better reproducibility. A release-based tabular source is easier to rerun and audit than a scraper that depends on a site layout that may change without warning.
- Clearer schema design. The official files separate concerns cleanly across title metadata, ratings, principals, crew, and names. This makes dataset construction more explicit and more educational for an NLP pipeline assignment.
- Lower fragility. Scraping introduces operational and policy risks. For this assignment, scraping would add engineering overhead without improving the underlying NLP contribution.
- Better provenance than derived dumps. Kaggle datasets can be useful for rapid prototyping, but many flatten fields, rename columns, omit identifiers, or combine sources in ways that make downstream joining and validation more difficult.

In short, official IMDb data was the best choice for a controlled, reproducible, structured NLP experiment.

== 2.2 Local Dataset Artifacts

The repository currently contains:

- raw IMDb `.tsv.gz` files for titles, ratings, crew, principals, and names
- an intermediate merged movie CSV
- a large cleaned corpus for ingestion
- a smaller top-10k subset for faster iteration

From the current local artifacts:

- the cleaned full corpus contains 1,305,051 movie rows
- the year range spans from 1894 to 2026
- the mean IMDb rating is 6.394
- the mean runtime is 85.26 minutes
- the most common genres in the cleaned corpus are Drama, Documentary, Comedy, Action, and Romance

The top-10k subset was kept as a practical experimental dataset. It has:

- 10,000 rows
- mean rating 7.627
- mean runtime 115.72 minutes

This smaller subset is useful when reproducing the system quickly or when running lower-cost experiments.

== 2.3 Preprocessing Pipeline

The preprocessing logic is implemented in `Data/dataprep.py` and the ingestion logic in `Data/ingest.py`.

The preprocessing stage performs:

- column normalization
- missing-value cleanup
- title-type filtering to keep only movies
- vote-threshold filtering
- runtime, year, and rating sanity cleanup
- ranking and top-N selection
- construction of a retrieval text field called `content`

The `content` field concatenates the title, type, year, runtime, genres, IMDb rating, number of votes, and a people summary. This field is important because it becomes the text that is embedded and later searched semantically.

The ingestion stage then:

- reads the cleaned CSV
- calls the embedding model on batches of movie passages
- creates the `movies` table if needed
- stores metadata plus embeddings in PostgreSQL / Supabase

= 3. System Architecture

The final system can be viewed as the following pipeline:

User Query

-> Intent Routing

-> Memory Retrieval

-> Query Rewrite

-> Structured Retrieval Parsing

-> Query Embedding

-> Vector Retrieval + Hard Filtering

-> Reranking

-> Answer Generation

-> Evaluation

-> Retry on Weak Response

-> Final Response

== 3.1 Why We Used LangGraph

We chose LangGraph because the system is inherently stateful and branchy. A single prompt chain would have been difficult to debug and extend once the project included:

- greetings and small talk
- clarification turns
- memory lookups
- follow-up rewrites
- retrieval branches
- answer regeneration when evaluation is weak

LangGraph gave us an explicit node-and-edge representation of the conversation workflow. This was a good match for the assignment because it let us reason about each stage separately instead of hiding the entire system inside one monolithic prompt.

The graph also allowed us to checkpoint session history via PostgreSQL, which gave us persistent multi-turn state across requests.

== 3.2 Why We Used LangSmith

LangSmith was not necessary to make the chatbot "work," but it was extremely useful during development. Retrieval systems often fail for different reasons:

- the query parser may miss a person name
- the retriever may return weak candidates
- the reranker may be slow or noisy
- the answer model may over-generalize
- the evaluator may misread the evidence

Tracing each stage made these failures visible. For example, it helped diagnose person-name drift, previous-turn judge leakage, and cases where the judge saw only a partial evidence set.

== 3.3 Memory And Session Management

Each request is associated with a `session_id`, and LangGraph stores the evolving thread state in PostgreSQL through a checkpointer. This design lets the chatbot support follow-up queries like:

- "newer ones"
- "shorter"
- "something darker"

Memory is used selectively rather than injected into every query. This became an important design choice because overusing raw conversation history increased hallucination risk. We therefore limited memory use to:

- follow-up refinement turns
- explicit memory lookups
- user-preference contexts when directly relevant

= 4. Retrieval And Response Pipeline

== 4.1 LLM-First Routing And Parsing

Earlier versions of the system relied heavily on heuristics for routing and filter extraction. This worked for many common cases, but it became brittle when queries were phrased naturally or when multiple constraints appeared together.

We therefore shifted to an LLM-first design:

- routing is now LLM-first with heuristic fallback
- retrieval filter extraction is now LLM-first with heuristic fallback

This gives the model first responsibility for interpreting intent and constraints, but still retains deterministic recovery paths when the LLM fails or returns incomplete structure.

The structured retrieval parser extracts:

- rewritten query
- person name
- genre
- min and max year
- max runtime
- minimum rating

This allows us to combine flexible interpretation with reliable downstream filtering.

== 4.2 Why Retrieval Is Not Purely LLM-Based

Although the project now uses LLMs first for interpretation, the actual retrieval stage is still database-driven rather than purely generative. This was a deliberate choice.

A purely LLM-based retriever would be weaker for this task because:

- it may hallucinate titles or metadata
- it does not enforce hard constraints reliably
- it is harder to debug
- it is more expensive and less reproducible

Instead, MovieMate uses LLMs for query understanding and then applies:

- embedding-based semantic retrieval
- SQL filters for hard constraints
- strict person-name checks
- reranking over the retrieved candidate set

This hybrid retrieval design proved much more reliable than free-form title generation.

== 4.3 Person Queries As A Special Case

One of the most difficult failure modes involved person-name queries, especially ambiguous names such as `Ana`, or full names that were partially lost during rewriting.

We found that person queries require stricter handling than generic semantic retrieval. The main fixes were:

- preserving person constraints from the original user message even if a rewrite drops them
- using strict person-name validation rather than loose substring matching
- post-filtering candidates so unrelated movies are discarded before they become cards

This is a good example of why a "less heuristics, more LLM" philosophy still needs exact constraints at the retrieval boundary. The LLM is strong at interpreting the request; the database and validation logic are stronger at enforcing factual matching.

== 4.4 Response Generation

The answer generator uses retrieved movie context as the source of truth. We explicitly restrict title mentions to titles that appear in the retrieved set.

An important design change was making card-mode summaries deterministic. Earlier, the answer model produced both text and cards, which caused duplicated lists and sometimes hallucinated titles in the prose. The final design instead uses:

- deterministic, grounded summaries for card mode
- model-generated grounded prose for text-only mode

This improved both correctness and user experience.

= 5. Evaluation Methodology

The assignment calls for reflection and performance analysis. In this project, evaluation was treated as a first-class system component rather than a final afterthought.

== 5.1 Hybrid Evaluation Design

We used a hybrid evaluation framework with three layers.

First, we used algorithmic retrieval checks:

- filter alignment: whether returned movies satisfy extracted constraints such as actor, genre, runtime, or year
- lexical query overlap: whether retrieved evidence overlaps meaningfully with the query terms

Second, we used response consistency checks:

- whether the answer is complete rather than cut off
- whether explicit counts in the answer match the retrieved set
- whether card-mode text avoids repeating movie titles unnecessarily

Third, we used an LLM judge that scores:

- retrieval relevance
- evidence alignment
- groundedness
- helpfulness
- presentation discipline

== 5.2 Why Pure LLM Evaluation Was Not Enough

We originally experimented with more judge-heavy evaluation, but the judge itself sometimes hallucinated. A representative failure case was when the judge saw only a small sample of retrieved evidence and incorrectly concluded that the answer was unsupported, even though the frontend showed more cards.

This led to two important insights:

- evaluation models can hallucinate too
- an LLM judge should not be trusted without a carefully designed evidence payload

We corrected this by giving the judge:

- the retrieved result count
- the retrieved title list
- aggregated runtime and year ranges
- compact evidence summaries

We also kept deterministic checks in the evaluation loop. This gave us a more trustworthy hybrid evaluator than either heuristics alone or LLM judgment alone.

== 5.3 Low-Signal Regeneration

If a retrieval turn receives a low score, the graph performs one retry with stricter guidance. This mechanism was useful when the response was incomplete, weakly grounded, or not well aligned with the retrieved evidence.

This regeneration step is important because it turns evaluation into an active correction mechanism rather than a passive dashboard.

= 6. Findings And Iterative Improvements

During development, several findings emerged.

== 6.1 Conversation State Helps, But Only When Controlled

Session memory is useful for follow-up refinements, but too much raw history can make the model overconfident and hallucinate. Selective memory retrieval was therefore better than dumping the entire conversation into every prompt.

== 6.2 LLM-First Interpretation Improves Flexibility

Moving routing and filter extraction to structured LLM calls improved handling of natural phrasing and multi-constraint queries. The model is better than regexes at understanding intent, but only when paired with good fallback logic.

== 6.3 Deterministic Guards Remain Necessary

Despite the shift toward LLM-first design, purely model-driven behavior was not sufficient in production-like settings. We still needed deterministic safety layers for:

- exact person-name validation
- fallback parsing
- count consistency
- incomplete-answer detection
- grounding checks for card-mode summaries

This was one of the most important practical findings in the project.

== 6.4 Evaluation Must Inspect The Same Evidence The User Sees

Judge quality improved substantially once the evidence summary better reflected the actual retrieved set. This was a key systems finding: evaluation is only as good as the evidence presentation given to the evaluator.

= 7. Justification Of Major Design Choices

== 7.1 Official IMDb Instead Of Scraping Or Kaggle

We chose official IMDb-derived data because it gave us:

- standardized identifiers
- better provenance
- easier merging across metadata tables
- a more reproducible experimental setup

Scraping was rejected because it would add fragility and policy concerns. A generic Kaggle-only approach was rejected because it often obscures data lineage and makes structured joins harder.

== 7.2 Embedding And Reranking Models

We used the NVIDIA embedding and reranking models because they are retrieval-oriented and fit naturally into the retrieval stage:

- the embedding model supports query and passage modes, which is valuable for asymmetric retrieval
- the reranker adds a second-stage relevance signal that improves the final shortlist

This choice was preferable to relying on a single generative model for everything.

== 7.3 Main Chat Model

We used `openai/gpt-oss-120b` for routing, structured parsing, answer generation, and judging because it performs well on:

- instruction following
- structured output
- long-form conversational interpretation

The choice was pragmatic: we needed one strong model that could handle both reasoning and structured extraction in a stable way.

== 7.4 Heuristics As Fallback Rather Than Primary Logic

The project began with more heuristics than we wanted. Over time, we refactored toward LLM-first routing and retrieval parsing. However, we did not remove heuristics entirely. Instead, we reduced them to their strongest use cases:

- fallback behavior
- exact validation
- deterministic guards

This gave us a better balance between flexibility and reliability.

= 8. Alignment With Assignment Outcomes

The final system matches the main expected outcomes from the assignment brief.

- Working conversational prototype: yes, the system supports interactive movie exploration and multi-turn refinement.
- Natural-language movie queries: yes, the chatbot supports genre, actor, director, year, runtime, and follow-up constraints.
- Integration of retrieval and language models: yes, the architecture explicitly combines structured data, embeddings, reranking, and LLM-based response generation.
- Understanding of practical challenges: yes, the project surfaced issues around ambiguity, hallucination, evaluation reliability, state management, and evidence grounding.

The assignment also emphasized dataset exploration, preprocessing, retrieval, conversational interaction, and evaluation. All of these components are represented in the final system and codebase, even though the implementation eventually moved beyond a notebook into a modular application.

= 9. Limitations And Future Work

The system is functional, but several limitations remain.

- Import-time side effects still exist in some backend setup paths and should be cleaned up for a more production-like deployment.
- The evaluator is stronger than before, but it is still partly dependent on an LLM judge.
- The current retrieval corpus emphasizes metadata rather than rich plot summaries, which limits deeper semantic matching.
- The frontend is intentionally lightweight and not a research contribution.

Natural future directions include:

- richer plot and synopsis fields for better semantic retrieval
- ablation studies comparing LLM-first parsing against pure heuristics
- offline benchmark sets for retrieval evaluation
- stronger personalization methods beyond conversational memory
- more systematic error analysis across query types

= 10. Conclusion

MovieMate demonstrates that a conversational movie assistant can be built most effectively as a retrieval-augmented NLP system rather than as a purely generative chatbot. The project began as an exploratory chatbot concept, but evolved into a modular architecture that integrates:

- structured movie metadata
- dense retrieval
- reranking
- stateful graph-based control flow
- LLM-based interpretation
- hybrid evaluation

The most important lesson from the project is that practical conversational NLP systems benefit from combining model flexibility with deterministic control. LLMs are powerful for understanding user intent and generating helpful explanations, but factual movie retrieval still depends on structured data, explicit constraints, and carefully designed validation and evaluation layers.

This balance between language modeling and controlled retrieval is what ultimately made the system robust enough to satisfy the assignment goals.
