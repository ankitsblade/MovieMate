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

Handling follow-ups:
- Treat short follow-ups like "newer ones", "darker", "shorter", or "with better ratings" as refinements when prior movie context exists.
"""

ROUTER_PROMPT = """
Classify the user's latest message into exactly one of these intents:

- greeting
- small_talk
- movie_query
- followup
- clarify

Guidelines:
- greeting: hi, hello, hey
- small_talk: thanks, okay, cool, bye
- movie_query: asks for recommendations, comparisons, similar movies, genres, actors, directors, or movie information
- followup: short refinement of prior movie discussion, such as "newer ones", "shorter", "darker", "after 2015"
- clarify: too vague or too short to meaningfully answer or retrieve

Return only the structured intent.
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

ANSWER_PROMPT = """
Conversation history:
{history}

Relevant memory context:
{memory_context}

User message:
{user_message}

Retrieved movie context:
{context}

Instructions:
- Answer naturally and concisely.
- Use retrieved movie context for movie facts.
- Use memory context for user-specific preferences or prior-conversation references.
- If both are available, combine them naturally.
- If memory context is empty, ignore it.
- If retrieved movie context is empty, do not invent movie facts.
- Do not hallucinate anything not supported by the provided context.
"""

ROUTER_PROMPT = """
Classify the user's latest message into exactly one of these intents:

- greeting
- small_talk
- movie_query
- followup
- memory_lookup
- clarify

Definitions:
- greeting: hi, hello, hey, greetings
- small_talk: thanks, okay, cool, bye, nice
- movie_query: asks for movie recommendations, comparisons, similar movies, genres, actors, directors, or movie information
- followup: short refinement of an ongoing movie discussion, such as "newer ones", "shorter", "darker", "after 2015"
- memory_lookup: asks what was said earlier, whether you remember something from the conversation, what the user's name is, or what you know from prior turns
- clarify: too vague or too short to answer meaningfully

Important:
- If the user is asking about something said earlier in the conversation, choose memory_lookup.
- Do not classify conversational memory questions as clarify.
- Only choose followup when the message is refining a movie-related discussion.

Return only the structured intent.
"""