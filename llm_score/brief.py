"""Single-call LLM extraction: structured facts for reviewer agents."""

from __future__ import annotations

from typing import Any

from llm_score.llm_client import DEFAULT_MODEL, call_model_json
from llm_score.prompts import BRIEF_PROMPT


def extract_reviewer_brief(application_text: str, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    """One model call per application — returns structured briefing JSON (no scores)."""
    data = call_model_json(
        BRIEF_PROMPT,
        model=model,
        application_text=application_text,
    )
    if not data:
        return {"error": "Model returned no parseable JSON"}
    return data
