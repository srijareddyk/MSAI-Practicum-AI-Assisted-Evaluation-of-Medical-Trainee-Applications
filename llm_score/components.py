"""One reader per part of an ophthalmology residency application.

Opinions are colors. These readers do not assign points.
"""

from __future__ import annotations

from typing import Any

from llm_score.llm_client import DEFAULT_MODEL, call_model_json, render_user_prompt

COLOR_RULES = """
Colors only. Do not assign points, ranks, letter grades, or counts.
green = this part clearly supports an interview on its own merits
yellow = mixed, thin, or incomplete: a faculty member should look again
red = this part is missing usable evidence, or actively argues against an interview
Use red when the section only lists titles with no applicant role, when letters give only empty praise with no clinical examples, or when ophthalmology commitment outside the statement is essentially absent.
Use green when this part has specific, concrete evidence that would support an interview on its own. A vivid ophthalmology story in the statement, or concrete MSPE clinical praise, should be green.
If this part is missing entirely, choose yellow and say it was not found.
Do not write GPA, USMLE scores, honors counts, or other numbers in the headline or the evidence.
""".strip()


def _prompt(title: str, focus: str) -> str:
    return f"""You are the {title} reader for the Northwestern Department of Ophthalmology residency screen.
You read only this part of the application: {focus}
You do not see the other readers' opinions.

{COLOR_RULES}
Use only what the packet states. Do not infer race, ethnicity, gender, age, disability, religion, or national origin.
Do not invent quotations.

Evidence rules:
- Return 2 or 3 evidence items.
- Each item must be a short snippet from this part of the packet: one or two sentences, as written or a close paraphrase.
- Prefer a continuous paragraph fragment over a bullet of facts.
- Put the snippet in quotation marks when it is close to the packet wording.
- Do not write your own summary as evidence.

Application excerpt:
{{application_text}}

Output JSON only:
{{{{
  "opinion": "<green|yellow|red>",
  "headline": "<one sentence with no numbers>",
  "evidence": ["<short paragraph snippet from the packet>"],
  "concern": "<one sentence, or empty>"
}}}}"""


READERS: tuple[dict[str, str], ...] = (
    {
        "id": "statement",
        "title": "Personal statement",
        "short": "Statement",
        "focus": "whether the personal statement gives a specific, credible reason for ophthalmology.",
    },
    {
        "id": "letters",
        "title": "Letters",
        "short": "Letters",
        "focus": "whether the letters give specific evidence about clinical judgment, skill, and teamwork.",
    },
    {
        "id": "research",
        "title": "Research",
        "short": "Research",
        "focus": "whether the research describes the applicant's own role, not just a list of titles.",
    },
    {
        "id": "clinical",
        "title": "Clinical record",
        "short": "Clinical",
        "focus": "what the clerkships and the MSPE say about clinical performance, including any ophthalmology rotation.",
    },
    {
        "id": "academics",
        "title": "Academic record",
        "short": "Academics",
        "focus": "whether the medical school record and Step 1, described without scores, support residency training.",
    },
    {
        "id": "commitment",
        "title": "Ophthalmology commitment",
        "short": "Commitment",
        "focus": "whether ophthalmology shows up outside the statement, in electives, mentors, or longitudinal exposure.",
    },
)

for _reader in READERS:
    _reader["template"] = _prompt(_reader["title"], _reader["focus"])

READERS_BY_ID = {reader["id"]: reader for reader in READERS}
DEFAULT_READER_IDS = ("statement", "letters", "research", "clinical")
_COLORS = frozenset({"green", "yellow", "red"})


def prompt_catalog() -> dict[str, object]:
    return {
        "rubric": COLOR_RULES,
        "prompts": [
            {
                "id": reader["id"],
                "title": reader["title"],
                "audience": reader["focus"],
                "max_tokens": 420,
                "variables": ["application_text"],
                "template": reader["template"],
            }
            for reader in READERS
        ],
    }


def _opinion(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    for color in ("green", "yellow", "red"):
        if color in text:
            return color
    return None


def _evidence(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    lines: list[str] = []
    for item in value:
        text = " ".join(str(item).split()).strip().strip('"').strip("'")
        if text:
            lines.append(text[:420])
    return lines[:3]


# Designed outcomes for the fictional AU99999 / _SYNTHETIC demo packet so the
# UI can show green, yellow, and red with real quotes from that file.
_SYNTHETIC_DEMO: dict[str, dict[str, Any]] = {
    "statement": {
        "opinion": "green",
        "headline": "The statement gives a concrete ophthalmology reason tied to a cataract case.",
        "evidence": [
            "During my third-year surgery clerkship I scrubbed into a cataract case for a patient who had stopped driving at night.",
            "That single, visible result is why ophthalmology appeals to me: pathology you can see, and care that changes daily function.",
        ],
        "concern": "",
    },
    "letters": {
        "opinion": "yellow",
        "headline": "Letters are thin: polite support without clinical examples.",
        "evidence": [
            "I have no examples of clinical judgment, procedures, or teamwork to offer.",
            "This letter contains no assessment of skill, reliability under pressure, or teaching ability.",
        ],
        "concern": "Faculty should ask writers for specifics or weigh other parts of the file more heavily.",
    },
    "research": {
        "opinion": "red",
        "headline": "Research lists titles only; no applicant role is described.",
        "evidence": [
            "No research role is described. The applicant did not design a study, analyze data, write a manuscript, or present work.",
            "Contribution: none stated. Methods: none stated. Applicant role: unknown.",
        ],
        "concern": "This part of the file argues against a research-ready read.",
    },
    "clinical": {
        "opinion": "green",
        "headline": "The MSPE gives specific clinical praise that supports residency readiness.",
        "evidence": [
            "On Internal Medicine, evaluators noted careful differential building, clear presentations, and thoughtful follow-up on overnight events.",
            "On Surgery, faculty wrote that Jordan anticipated next steps in clinic, communicated plans to patients in plain language, and handled feedback without defensiveness.",
        ],
        "concern": "",
    },
    "academics": {
        "opinion": "yellow",
        "headline": "Academics are incomplete: school name and Step 1 Pass only.",
        "evidence": [
            "Step 1 status appears in the packet as Pass only.",
            "No school context, no comparative academic language, and no further academic narrative are included.",
        ],
        "concern": "Faculty should look at the raw transcript outside this screen.",
    },
    "commitment": {
        "opinion": "red",
        "headline": "Outside the statement, ophthalmology exposure is only a half-day of shadowing.",
        "evidence": [
            "Ophthalmology exposure outside the personal statement: one half-day of shadowing in 2024.",
            "No ophthalmology elective. No ophthalmology mentor. No vision screening, eye clinic continuity, or longitudinal eye research.",
        ],
        "concern": "Commitment to the field is not shown as a pattern in the experiences section.",
    },
}


def is_synthetic_demo_packet(name: str) -> bool:
    upper = name.upper()
    return "_SYNTHETIC" in upper or "AU99999" in upper


def run_synthetic_demo_component(
    agent_id: str,
    application_text: str,
    prompts_sent: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return the designed color for the fictional imperfect demo packet."""
    reader = READERS_BY_ID[agent_id]
    if prompts_sent is not None:
        prompts_sent[agent_id] = (
            "[SYNTHETIC DEMO] Designed color for UI calibration.\n\n"
            + render_user_prompt(reader["template"], application_text=application_text)
        )
    preset = _SYNTHETIC_DEMO.get(agent_id)
    base = {
        "id": reader["id"],
        "title": reader["title"],
        "short": reader["short"],
        "headline": None,
        "opinion": None,
        "evidence": [],
        "concern": None,
        "error": None,
    }
    if not preset:
        base["error"] = "No synthetic demo preset for this reader."
        return base
    base["opinion"] = preset["opinion"]
    base["headline"] = preset["headline"]
    base["evidence"] = list(preset["evidence"])
    base["concern"] = preset["concern"] or None
    return base


def run_component(
    agent_id: str,
    application_text: str,
    model: str = DEFAULT_MODEL,
    prompts_sent: dict[str, str] | None = None,
    *,
    synthetic_demo: bool = False,
) -> dict[str, Any]:
    if synthetic_demo:
        return run_synthetic_demo_component(agent_id, application_text, prompts_sent)
    reader = READERS_BY_ID[agent_id]
    if prompts_sent is not None:
        prompts_sent[agent_id] = render_user_prompt(
            reader["template"], application_text=application_text
        )
    raw = call_model_json(
        reader["template"],
        model=model,
        max_tokens=420,
        application_text=application_text,
    )
    base = {
        "id": reader["id"],
        "title": reader["title"],
        "short": reader["short"],
        "headline": None,
        "opinion": None,
        "evidence": [],
        "concern": None,
        "error": None,
    }
    if not raw or (raw.get("error") and not raw.get("opinion")):
        base["error"] = str((raw or {}).get("error") or "Model returned no parseable JSON")
        return base
    opinion = _opinion(raw.get("opinion"))
    headline = " ".join(str(raw.get("headline") or "").split()).strip()
    concern = " ".join(str(raw.get("concern") or "").split()).strip()
    base["opinion"] = opinion
    base["headline"] = headline or None
    base["evidence"] = _evidence(raw.get("evidence"))
    base["concern"] = concern or None
    if opinion is None:
        base["error"] = "The reader did not return green, yellow, or red."
    return base


def combine_opinions(reads: list[dict[str, Any]]) -> dict[str, str]:
    colors = [read["opinion"] for read in reads if read.get("opinion") in _COLORS]
    if not colors:
        return {
            "opinion": "split",
            "summary": "None of the selected readers returned a color.",
        }
    if len(set(colors)) == 1:
        summary = {
            "green": "The selected readers agree this file supports an interview.",
            "yellow": "The selected readers agree a faculty member should look again.",
            "red": "The selected readers agree this file should not advance.",
        }[colors[0]]
        return {"opinion": colors[0], "summary": summary}
    return {
        "opinion": "split",
        "summary": "The readers do not agree. Open each card before deciding.",
    }
