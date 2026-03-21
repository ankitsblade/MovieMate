from typing import Literal
from pydantic import BaseModel
from langsmith import traceable

from app.llm.chat_model import llm
from app.llm.prompts import ROUTER_PROMPT


class RouteDecision(BaseModel):
    intent: Literal[
        "greeting",
        "small_talk",
        "movie_query",
        "followup",
        "memory_lookup",
        "clarify",
    ]


router_llm = llm.with_structured_output(RouteDecision)


@traceable(run_type="chain", name="classify_intent")
def classify_intent(user_message: str) -> str:
    result = router_llm.invoke(
        [
            ("system", ROUTER_PROMPT),
            ("user", user_message),
        ]
    )
    return result.intent