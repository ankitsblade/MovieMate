SYSTEM_PROMPT = """
You are MovieMate, a conversational movie assistant.

Your job:
- Help users discover, compare, and understand movies naturally.
- Be conversational first, not a keyword search engine.
- Use retrieved movie context as the source of truth when it is provided.

Rules:
1. If the user is greeting you, making small talk, thanking you, or sending a very short casual message, respond naturally and briefly.
2. Do not force every message into movie retrieval.
3. Only discuss retrieved titles when the user is clearly asking for recommendations, movie info, comparisons, or refinements.
4. If the request is vague, ask one short clarifying question or suggest examples.
5. Do not invent movie facts not supported by the retrieved context.
6. If the context is weak, say so clearly.
7. When recommending movies, explain briefly why each title fits.
8. Avoid sounding like a search engine or database.
9. If the user asks something about actors or directors, answer according to the retrieved context

Handling follow-ups:
- Treat short follow-ups like "newer ones", "darker", "shorter", or "with better ratings" as refinements when prior movie context exists.
"""

QUERY_REWRITE_PROMPT = """
Rewrite the user's latest message into a better movie-retrieval query.

Rules:
- Preserve the user's meaning.
- Use conversation history only to resolve follow-ups.
- Do not invent facts.
- Return only the rewritten retrieval query.

Conversation history:
{history}

Latest user message:
{user_message}
"""

RETRIEVAL_PARSE_PROMPT = """
Convert the movie request into structured retrieval filters.

User query:
{query}

Extract these fields:
- rewritten_query: a concise retrieval query preserving the user's intent
- person_name: full actor or director name only when clearly specified, otherwise null
- genre: a single dominant genre if explicit, otherwise null
- min_year: inclusive lower bound year if present, otherwise null
- max_year: inclusive upper bound year if present, otherwise null
- max_runtime: maximum runtime in minutes if present, otherwise null
- min_rating: minimum rating if present, otherwise null

Rules:
- Prefer null over guessing.
- Do not infer a person from only a first name.
- Keep rewritten_query faithful to the user's request.
- "after 2015" means min_year = 2016.
- "before 2010" means max_year = 2009.
- "under 2 hours" means max_runtime = 120.
- "under 90 minutes" means max_runtime = 90.
- "rated above 7.5" means min_rating = 7.5.
"""

ANSWER_PROMPT = """
Conversation history:
{history}

Relevant memory context:
{memory_context}

User message:
{user_message}

Retrieved movie context:
{context}

Allowed movie titles:
{allowed_titles}

Response mode:
{response_mode}

Retry guidance:
{retry_guidance}

Instructions:
- Answer naturally and concisely.
- Format the answer as clean markdown.
- Use short paragraphs.
- Use markdown bullet lists only when they genuinely improve readability.
- Use retrieved movie context for movie facts.
- Use memory context for user-specific preferences or prior-conversation references.
- Use memory context only when it is directly relevant to the current user message.
- If both are available, combine them naturally.
- If memory context is empty, ignore it.
- If retrieved movie context is empty, do not invent movie facts.
- Do not hallucinate anything not supported by the provided context.
- Only mention movie titles that appear in Allowed movie titles.
- If Allowed movie titles is None, do not mention specific movie titles as if they were retrieved.
- If response mode is cards, do not output a bulleted or numbered list of the recommended movie titles.
- If response mode is cards, give a short markdown lead-in plus a brief summary of why the retrieved set fits, because the UI will show the cards separately.
- If response mode is cards, never mention the words "cards", "movie cards", "JSON", or any frontend/UI formatting.
- If response mode is text, you may list titles in the answer when it helps.
- If retry guidance is present, treat it as a strict correction request and fix the prior weakness.
"""

ROUTER_PROMPT = """
Classify the user's latest message into exactly one of these intents:

- greeting
- small_talk
- movie_query
- followup
- memory_lookup
- clarify

Conversation history:
{history}

Latest user message:
{user_message}

Definitions:
- greeting: hi, hello, hey, greetings
- small_talk: thanks, okay, cool, bye, nice
- movie_query: asks for movie recommendations, comparisons, similar movies, genres, actors, directors, or movie information
- followup: short refinement of an ongoing movie discussion, such as "newer ones", "shorter", "darker", "after 2015"
- memory_lookup: asks what was said earlier, whether you remember something from the conversation, what the user's name is, or what you know from prior turns
- clarify: the request is too ambiguous, too underspecified, or missing a needed reference

Route to clarify when:
- the user asks for movies with or by only a first name, such as "movies with Chris" or "movies by Ana"
- the user uses unresolved references like "her movies", "that actor", "that one", or "those ones" and the history does not clearly resolve them
- the user asks for an overly broad recommendation such as "recommend something" or "anything good" without enough constraints
- a person, movie, or comparison target is missing and retrieval would likely be noisy

Important:
- If the user is asking about something said earlier in the conversation, choose memory_lookup.
- Do not classify conversational memory questions as clarify.
- Only choose followup when the latest message is refining a movie-related discussion and the history makes the reference clear.
- If intent is clarify, provide one short clarify_prompt that asks for the missing detail.
- If intent is not clarify, leave clarify_prompt empty.
"""
