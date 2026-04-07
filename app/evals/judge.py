from __future__ import annotations

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.config import (
    ENABLE_LLM_EVAL,
    EVAL_CHAT_MODEL,
    EVAL_LLM_TIMEOUT_SECONDS,
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
)


class TurnJudgeResult(BaseModel):
    retrieval_relevance: int = Field(ge=1, le=5)
    evidence_alignment: int = Field(ge=1, le=5)
    groundedness: int = Field(ge=1, le=5)
    helpfulness: int = Field(ge=1, le=5)
    presentation_discipline: int = Field(ge=1, le=5)
    note: str = Field(min_length=1, max_length=160)


judge_llm = ChatOpenAI(
    model=EVAL_CHAT_MODEL,
    api_key=NVIDIA_API_KEY,
    base_url=NVIDIA_BASE_URL,
    temperature=0,
    max_tokens=256,
    timeout=EVAL_LLM_TIMEOUT_SECONDS,
).with_structured_output(TurnJudgeResult)


def judge_turn(
    *,
    user_message: str,
    answer: str,
    context: str,
    memory_context: str,
    show_movie_cards: bool,
) -> TurnJudgeResult | None:
    if not ENABLE_LLM_EVAL:
        return None

    prompt = f"""
You are evaluating one movie assistant turn.

User message:
{user_message}

Assistant answer:
{answer}

Retrieved evidence:
{context or "None"}

Memory context:
{memory_context or "None"}

Presentation mode:
{"cards" if show_movie_cards else "text"}

Important evaluation rules:
- Evaluate only this current turn.
- Treat "Retrieved result count" and "Retrieved titles" as authoritative for the full evidence set.
- The per-evidence blocks are examples from that retrieved set, not the entire set.
- In cards mode, the answer body may summarize the set without listing every movie title.
- Penalize the answer only for unsupported specifics that conflict with or go beyond the provided retrieved set summary and evidence.

Score the turn on:
- retrieval_relevance: how well the retrieved evidence matches the user request
- evidence_alignment: how well the answer uses or reflects the retrieved evidence
- groundedness: whether the answer stays faithful to the provided evidence and avoids unsupported claims
- helpfulness: whether the answer is useful and responsive to the user
- presentation_discipline: whether the response format suits the intended presentation mode

Evaluate conservatively. Penalize unsupported specifics, contradictions, weak retrieval, and response formatting that does not match the intended mode.
Return one short note under 25 words explaining the most important reason behind the scores.
"""

    try:
        return judge_llm.invoke(
            [
                ("system", "You are a strict evaluator for retrieval-augmented movie assistant turns. Be faithful to the provided evidence summary."),
                ("user", prompt),
            ]
        )
    except Exception:
        return None
