"""Reusable screening pipeline for the web API (mirrors llm_score.cli)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable

from application_analyzer.excel_export import write_multi_applicant_workbook, write_workbook
from application_analyzer.facts import ExtractedFacts, extract_facts_from_text
from application_analyzer.pdf_extract import extract_text_from_pdf
from application_analyzer.scoring import RubricScores, compute_scores
from llm_score.brief import extract_reviewer_brief
from llm_score.components import combine_opinions, is_synthetic_demo_packet, run_component
from llm_score.llm_client import DEFAULT_MODEL, render_user_prompt, tighten_text
from llm_score.markdown_export import briefing_to_markdown, review_to_markdown
from llm_score.redact import apply_identity_redactions, cloud_llm_enabled, redact_application_text
from llm_score.prompts import BRIEF_PROMPT, DOC_A_PROMPT, DOC_B_PROMPT, DOC_C_PROMPT
from llm_score.reviewers import AgentReview, run_doc_a, run_doc_b, run_doc_c
from llm_score.text_strip import strip_for_llm

ProgressCallback = Callable[[str, dict[str, Any]], None]


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _safe_md_filename(name: str | None, pdf: Path, suffix: str) -> str:
    base = name or pdf.stem
    cleaned = re.sub(r"[^\w\s\-().]", "", base).strip().replace(" ", "_")
    return f"{cleaned or pdf.stem}{suffix}.md"


def _agent_to_dict(review: AgentReview | None) -> dict[str, Any] | None:
    if review is None:
        return None
    return {
        "summary": review.summary,
        "scores": review.scores,
        "rationale": review.rationale,
        "error": review.error,
    }


@dataclass
class PipelineResult:
    applicants: list[dict[str, Any]]
    excel_path: Path
    briefings_dir: Path


def run_pipeline(
    pdf_paths: list[Path],
    *,
    output_dir: Path,
    template: Path | None = None,
    model: str = DEFAULT_MODEL,
    skip_llm: bool = False,
    skip_agents: bool = False,
    school_list: Path | None = None,
    on_progress: ProgressCallback | None = None,
    readers: list[dict[str, str]] | None = None,
) -> PipelineResult:
    root = project_root()
    template_path = template or (root / "rubric" / "template.xlsx")
    if not template_path.is_file():
        raise FileNotFoundError(f"Rubric template not found: {template_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    briefings_dir = output_dir / "briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)
    excel_path = output_dir / "screening_scores.xlsx"

    def emit(stage: str, **extra: Any) -> None:
        if on_progress:
            on_progress(stage, extra)

    items: list[tuple[ExtractedFacts, RubricScores]] = []
    agent_reviews: list[tuple[AgentReview | None, AgentReview | None]] = []
    applicants: list[dict[str, Any]] = []
    total = len(pdf_paths)

    for index, pdf in enumerate(pdf_paths):
        emit("extracting", index=index, total=total)
        text = extract_text_from_pdf(pdf)
        facts = extract_facts_from_text(text, pdf)
        scores = compute_scores(facts, text, str(school_list) if school_list else None)
        # The real name stays in `facts` only so redaction can find it. Everything
        # written out (UI, Excel, markdown, progress) uses an anonymous label.
        label = f"Applicant {index + 1}" if total > 1 else "Applicant"
        public_facts = replace(facts, applicant_name=label, source_path=f"{label}.pdf")
        items.append((public_facts, scores))

        brief: dict | None = None
        doc_a: AgentReview | None = None
        doc_b: AgentReview | None = None
        doc_c: AgentReview | None = None
        stripped_len = 0
        markdown_files: dict[str, str] = {}
        prompts_sent: dict[str, str] = {}
        components: list[dict[str, Any]] = []
        combined: dict[str, str] | None = None

        redaction_notes: list[str] = []

        def llm_excerpt() -> str:
            """Text for the model. Identifiers are scrubbed locally first for hosted models."""
            excerpt = tighten_text(strip_for_llm(text))
            if cloud_llm_enabled():
                emit("redacting", index=index, total=total, applicant=label)
                excerpt, notes = redact_application_text(excerpt, facts, pdf, harvest_from=text)
                redaction_notes.extend(notes)
            return excerpt

        if readers:
            excerpt = llm_excerpt()
            stripped_len = len(excerpt)
            prompts_sent["application_excerpt"] = excerpt
            name = label
            synthetic_demo = is_synthetic_demo_packet(pdf.name)
            for reader in readers:
                emit(reader["id"], index=index, total=total, applicant=name, agent=reader["short"])
                components.append(
                    run_component(
                        reader,
                        excerpt,
                        model=model,
                        prompts_sent=prompts_sent,
                        synthetic_demo=synthetic_demo,
                    )
                )
            combined = combine_opinions(components)
        elif not skip_llm:
            excerpt = llm_excerpt()
            stripped_len = len(excerpt)
            prompts_sent["application_excerpt"] = excerpt
            name = label
            emit("briefing", index=index, total=total, applicant=name)
            prompts_sent["brief"] = render_user_prompt(BRIEF_PROMPT, application_text=excerpt)
            brief = extract_reviewer_brief(excerpt, model=model)
            brief_md = briefing_to_markdown(
                label,
                brief,
                source_file=f"{label}.pdf",
            )
            brief_path = briefings_dir / _safe_md_filename(label, pdf, "_brief")
            brief_path.write_text(brief_md, encoding="utf-8")
            markdown_files["brief"] = brief_path.name

            if not skip_agents:
                briefing_json = json.dumps(brief, indent=2, ensure_ascii=False)
                if cloud_llm_enabled():
                    briefing_json, _ = apply_identity_redactions(briefing_json, facts, pdf, harvest_from=text)
                emit("doc_a", index=index, total=total, applicant=name)
                prompts_sent["doc_a"] = render_user_prompt(
                    DOC_A_PROMPT, application_text=excerpt, briefing_json=briefing_json
                )
                doc_a = run_doc_a(excerpt, briefing_json, model=model)
                doc_a_path = briefings_dir / _safe_md_filename(label, pdf, "_doc_a")
                doc_a_path.write_text(
                    review_to_markdown(label, doc_a, source_file=pdf.name),
                    encoding="utf-8",
                )
                markdown_files["doc_a"] = doc_a_path.name

                emit("doc_b", index=index, total=total, applicant=name)
                prompts_sent["doc_b"] = render_user_prompt(
                    DOC_B_PROMPT, application_text=excerpt, briefing_json=briefing_json
                )
                doc_b = run_doc_b(excerpt, briefing_json, model=model)
                doc_b_path = briefings_dir / _safe_md_filename(label, pdf, "_doc_b")
                doc_b_path.write_text(
                    review_to_markdown(label, doc_b, source_file=pdf.name),
                    encoding="utf-8",
                )
                markdown_files["doc_b"] = doc_b_path.name

                emit("doc_c", index=index, total=total, applicant=name)
                prompts_sent["doc_c"] = render_user_prompt(
                    DOC_C_PROMPT, application_text=excerpt, briefing_json=briefing_json
                )
                doc_c = run_doc_c(excerpt, briefing_json, model=model)
                doc_c_path = briefings_dir / _safe_md_filename(label, pdf, "_doc_c")
                doc_c_path.write_text(
                    review_to_markdown(label, doc_c, source_file=pdf.name),
                    encoding="utf-8",
                )
                markdown_files["doc_c"] = doc_c_path.name

        agent_reviews.append((doc_a, doc_b, doc_c))
        applicants.append(
            {
                "file": f"{label}.pdf",
                "applicant_name": label,
                "stripped_chars": stripped_len,
                "redacted_for_llm": bool(redaction_notes) or (stripped_len > 0 and cloud_llm_enabled()),
                "redaction_notes": redaction_notes,
                "briefing": brief,
                "doc_a": _agent_to_dict(doc_a),
                "doc_b": _agent_to_dict(doc_b),
                "doc_c": _agent_to_dict(doc_c),
                "facts": {
                    "undergraduate_institution": facts.undergraduate_institution,
                    "undergraduate_cum_gpa": facts.undergraduate_cum_gpa,
                    "work_experience": facts.work_experience,
                    "notes": facts.notes,
                },
                "scores": {
                    "undergraduate_quality": scores.undergraduate_quality,
                    "undergraduate_performance": scores.undergraduate_performance,
                },
                "markdown_files": markdown_files,
                "prompts_sent": prompts_sent,
                "components": components,
                "combined": combined,
            }
        )
        emit("applicant_done", index=index, total=total, applicant=label)

    emit("writing_excel", total=total)
    if len(items) == 1:
        da, db = agent_reviews[0][0], agent_reviews[0][1]
        write_workbook(
            template_path,
            items[0][0],
            items[0][1],
            excel_path,
            strip_template_sheets=True,
            doc_a=da,
            doc_b=db,
        )
    else:
        write_multi_applicant_workbook(
            template_path,
            items,
            excel_path,
            strip_template_sheets=True,
            agent_reviews=agent_reviews,
        )

    emit("complete", total=total)
    return PipelineResult(
        applicants=applicants,
        excel_path=excel_path,
        briefings_dir=briefings_dir,
    )
