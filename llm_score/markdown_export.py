"""Render reviewer briefing JSON as a one-page Markdown document."""

from __future__ import annotations

from datetime import date
from typing import Any


def _bullets(items: list[str], limit: int = 4) -> list[str]:
    out: list[str] = []
    for item in items[:limit]:
        text = str(item).strip()
        if text:
            out.append(f"- {text}")
    return out


def _section(title: str, summary: str, bullets: list[str]) -> str:
    lines = [f"## {title}", "", summary.strip() or "_Not found in application._", ""]
    lines.extend(bullets)
    lines.append("")
    return "\n".join(lines)


def briefing_to_markdown(
    applicant_name: str,
    brief: dict[str, Any],
    *,
    source_file: str | None = None,
) -> str:
    spe = brief.get("scientific_pursuits_education") or {}
    spo = brief.get("scientific_pursuits_output") or {}
    ple = brief.get("professional_leadership_education") or {}
    plo = brief.get("professional_leadership_output") or {}
    sl = brief.get("social_leadership_service") or {}
    dt = brief.get("resilience") or {}
    elw = brief.get("endorsements") or {}

    header = [
        f"# Reviewer Brief — {applicant_name or 'Applicant'}",
        "",
        f"_Generated {date.today().isoformat()}. Factual extraction only — not scored._",
    ]
    if source_file:
        header.append(f"_Source: {source_file}_")
    header.extend(["", "---", ""])

    spe_bullets = _bullets(spe.get("evidence") or [])
    if spe.get("md_phd") is True:
        spe_bullets.insert(0, "- Holds MD/PhD (per application)")
    for role in (spe.get("research_roles") or [])[:3]:
        if isinstance(role, dict):
            spe_bullets.append(f"- {role.get('role', 'Research')}: {role.get('duration', '?')}")

    spo_bullets = _bullets(spo.get("highlights") or [])
    spo_bullets.insert(
        0,
        "- Counts: "
        f"1st-author pubs {spo.get('first_author_pubs', '?')}, "
        f"other pubs {spo.get('non_first_author_pubs', '?')}, "
        f"oral {spo.get('oral_presentations', '?')}, "
        f"poster {spo.get('poster_presentations', '?')}",
    )

    ple_bullets = _bullets(ple.get("evidence") or [])
    if ple.get("mba_mph_or_equivalent"):
        ple_bullets.insert(0, "- MBA/MPH or equivalent leadership degree noted")

    plo_bullets = _bullets(plo.get("evidence") or [])
    for label, key in (
        ("For-profit/director", "for_profit_or_director_roles"),
        ("Large-scale QI/public health", "large_scale_qi_or_public_health"),
        ("Technical health tools", "technical_health_tools"),
    ):
        for item in (plo.get(key) or [])[:2]:
            plo_bullets.append(f"- {label}: {item}")

    sl_bullets = _bullets(sl.get("evidence") or [])
    for act in (sl.get("notable_activities") or [])[:3]:
        if isinstance(act, dict):
            sl_bullets.append(f"- {act.get('activity', 'Activity')} ({act.get('scope', 'scope n/a')})")

    dt_bullets = _bullets(dt.get("evidence") or [])
    if dt.get("growth_connection"):
        dt_bullets.insert(0, f"- Growth connection: {dt['growth_connection']}")

    elw_bullets = _bullets(elw.get("standout_quotes") or [])
    elw_bullets.insert(
        0,
        f"- Letters: {elw.get('letter_count', '?')} | Tone: {elw.get('overall_tone', 'n/a')}",
    )

    body = [
        _section("Scientific Pursuits — Education/Experience", spe.get("summary", ""), spe_bullets),
        _section("Scientific Pursuits — Output", spo.get("summary", ""), spo_bullets),
        _section("Professional Leadership — Education", ple.get("summary", ""), ple_bullets),
        _section("Professional Leadership — Output", plo.get("summary", ""), plo_bullets),
        _section("Social Leadership & Service", sl.get("summary", ""), sl_bullets),
        _section("Resilience / Grit / Distance Travelled", dt.get("summary", ""), dt_bullets),
        _section("Endorsement by Letter Writers", elw.get("summary", ""), elw_bullets),
    ]

    if brief.get("error"):
        body.append(f"_Warning: {brief['error']}_\n")

    return "\n".join(header + body).strip() + "\n"


def review_to_markdown(
    applicant_name: str,
    review: Any,
    *,
    source_file: str | None = None,
) -> str:
    """Render a Doc A / Doc B agent review as a one-page Markdown document."""
    from llm_score.reviewers import SCORE_KEYS

    header = [
        f"# {review.agent_name} Review — {applicant_name or 'Applicant'}",
        "",
        f"_Generated {date.today().isoformat()}. AI agent scores — validate before use._",
    ]
    if source_file:
        header.append(f"_Source: {source_file}_")
    header.extend(["", "---", ""])

    lines = header + ["## Summary", "", review.summary or "_No summary returned._", "", "## Scores", ""]
    labels = {
        "scientific_pursuits_education": "Scientific Pursuits — Education/Experience (row 5)",
        "scientific_pursuits_output": "Scientific Pursuits — Output (row 6)",
        "professional_leadership_education": "Professional Leadership — Education (row 7)",
        "professional_leadership_output": "Professional Leadership — Output (row 8)",
        "social_leadership": "Social Leadership & Service (row 9)",
        "resilience": "Resilience / Grit (row 10)",
        "endorsement": "Endorsement by Letter Writers (row 11)",
        "reviewer_recommendation": "Recommendation (row 12)",
    }
    for key in SCORE_KEYS:
        score = review.scores.get(key)
        label = labels.get(key, key)
        lines.append(f"- **{label}:** {score if score is not None else '—'}")
        note = review.rationale.get(key)
        if note:
            lines.append(f"  - _{note}_")
    lines.extend(["", "## Rationale", ""])
    if review.rationale:
        for key in SCORE_KEYS:
            if key in review.rationale:
                lines.append(f"- **{labels.get(key, key)}:** {review.rationale[key]}")
    else:
        lines.append("_No rationale returned._")
    if review.error:
        lines.extend(["", f"_Warning: {review.error}_"])
    lines.append("")
    return "\n".join(lines)
