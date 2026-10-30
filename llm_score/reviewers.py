"""Doc A and Doc B — independent LLM screening agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from llm_score.llm_client import DEFAULT_MODEL, call_model_json
from llm_score.prompts import DOC_A_PROMPT, DOC_B_PROMPT

SCORE_KEYS = (
    "scientific_pursuits_education",
    "scientific_pursuits_output",
    "professional_leadership_education",
    "professional_leadership_output",
    "social_leadership",
    "resilience",
    "endorsement",
    "reviewer_recommendation",
)

ALLOWED_NUMERIC: dict[str, set[int | float]] = {
    "scientific_pursuits_education": {0, 1, 2, 4},
    "scientific_pursuits_output": {0, 0.5, 1, 2, 3, 4},
    "professional_leadership_education": {0, 2},
    "professional_leadership_output": {0, 2, 4},
    "social_leadership": {0, 0.5, 2, 4},
    "resilience": {0, 1.5, 3.5},
    "endorsement": {0, 1, 2, 3, 4},
}

ALLOWED_RECOMMENDATIONS = frozenset({"A", "B", "C"})


@dataclass
class AgentReview:
    agent_name: str
    summary: str | None = None
    scores: dict[str, int | float | str | None] = field(default_factory=dict)
    rationale: dict[str, str] = field(default_factory=dict)
    error: str | None = None


def _coerce_numeric(key: str, value: Any) -> int | float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num.is_integer():
        num = int(num)
    allowed = ALLOWED_NUMERIC.get(key)
    if allowed and num not in allowed:
        return None
    return num


def _coerce_recommendation(value: Any) -> str | None:
    if value is None:
        return None
    letter = str(value).strip().upper()[:1]
    return letter if letter in ALLOWED_RECOMMENDATIONS else None


def _normalize_review(agent_name: str, raw: dict[str, Any]) -> AgentReview:
    if not raw:
        return AgentReview(agent_name=agent_name, error="Model returned no parseable JSON")

    scores_in = raw.get("scores") or {}
    rationale = {k: str(v) for k, v in (raw.get("rationale") or {}).items() if v}
    scores: dict[str, int | float | str | None] = {}

    for key in SCORE_KEYS:
        if key == "reviewer_recommendation":
            scores[key] = _coerce_recommendation(scores_in.get(key))
        else:
            scores[key] = _coerce_numeric(key, scores_in.get(key))

    return AgentReview(
        agent_name=agent_name,
        summary=str(raw.get("summary") or "").strip() or None,
        scores=scores,
        rationale=rationale,
    )


def run_doc_a(
    application_text: str,
    briefing_json: str,
    model: str = DEFAULT_MODEL,
) -> AgentReview:
    raw = call_model_json(
        DOC_A_PROMPT,
        model=model,
        application_text=application_text,
        briefing_json=briefing_json,
    )
    return _normalize_review("Doc A", raw)


def run_doc_b(
    application_text: str,
    briefing_json: str,
    model: str = DEFAULT_MODEL,
) -> AgentReview:
    raw = call_model_json(
        DOC_B_PROMPT,
        model=model,
        application_text=application_text,
        briefing_json=briefing_json,
    )
    return _normalize_review("Doc B", raw)
