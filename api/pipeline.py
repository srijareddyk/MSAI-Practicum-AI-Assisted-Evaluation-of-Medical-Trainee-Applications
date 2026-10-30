"""Reusable screening pipeline for the web API (mirrors llm_score.cli)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from application_analyzer.excel_export import write_multi_applicant_workbook, write_workbook
from application_analyzer.facts import ExtractedFacts, extract_facts_from_text
from application_analyzer.pdf_extract import extract_text_from_pdf
from application_analyzer.scoring import RubricScores, compute_scores
from llm_score.brief import extract_reviewer_brief
from llm_score.llm_client import DEFAULT_MODEL
from llm_score.markdown_export import briefing_to_markdown, review_to_markdown
from llm_score.reviewers import AgentReview, run_doc_a, run_doc_b
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
        emit("extracting", index=index, total=total, file=pdf.name)
        text = extract_text_from_pdf(pdf)
        facts = extract_facts_from_text(text, pdf)
        scores = compute_scores(facts, text, str(school_list) if school_list else None)
        items.append((facts, scores))

        brief: dict | None = None
        doc_a: AgentReview | None = None
        doc_b: AgentReview | None = None
        stripped_len = 0
        markdown_files: dict[str, str] = {}

        if not skip_llm:
            stripped = strip_for_llm(text)
            stripped_len = len(stripped)
            name = facts.applicant_name or pdf.name
            emit("briefing", index=index, total=total, applicant=name)
            brief = extract_reviewer_brief(stripped, model=model)
            brief_md = briefing_to_markdown(
                facts.applicant_name or pdf.stem,
                brief,
                source_file=pdf.name,
            )
            brief_path = briefings_dir / _safe_md_filename(facts.applicant_name, pdf, "_brief")
            brief_path.write_text(brief_md, encoding="utf-8")
            markdown_files["brief"] = brief_path.name

            if not skip_agents:
                briefing_json = json.dumps(brief, indent=2, ensure_ascii=False)
                emit("doc_a", index=index, total=total, applicant=name)
                doc_a = run_doc_a(stripped, briefing_json, model=model)
                doc_a_path = briefings_dir / _safe_md_filename(facts.applicant_name, pdf, "_doc_a")
                doc_a_path.write_text(
                    review_to_markdown(facts.applicant_name or pdf.stem, doc_a, source_file=pdf.name),
                    encoding="utf-8",
                )
                markdown_files["doc_a"] = doc_a_path.name

                emit("doc_b", index=index, total=total, applicant=name)
                doc_b = run_doc_b(stripped, briefing_json, model=model)
                doc_b_path = briefings_dir / _safe_md_filename(facts.applicant_name, pdf, "_doc_b")
                doc_b_path.write_text(
                    review_to_markdown(facts.applicant_name or pdf.stem, doc_b, source_file=pdf.name),
                    encoding="utf-8",
                )
                markdown_files["doc_b"] = doc_b_path.name

        agent_reviews.append((doc_a, doc_b))
        applicants.append(
            {
                "file": pdf.name,
                "applicant_name": facts.applicant_name,
                "stripped_chars": stripped_len,
                "briefing": brief,
                "doc_a": _agent_to_dict(doc_a),
                "doc_b": _agent_to_dict(doc_b),
                "facts": {
                    "medical_school": facts.medical_school,
                    "undergraduate_institution": facts.undergraduate_institution,
                    "undergraduate_cum_gpa": facts.undergraduate_cum_gpa,
                    "usmle_step1_times_taken": facts.usmle_step1_times_taken,
                    "usmle_step1_result": facts.usmle_step1_result,
                    "notes": facts.notes,
                },
                "scores": {
                    "medical_school_quality": scores.medical_school_quality,
                    "medical_school_performance": scores.medical_school_performance,
                    "undergraduate_quality": scores.undergraduate_quality,
                    "undergraduate_performance": scores.undergraduate_performance,
                    "usmle_step1": scores.usmle_step1,
                },
                "markdown_files": markdown_files,
            }
        )
        emit("applicant_done", index=index, total=total, applicant=facts.applicant_name or pdf.name)

    emit("writing_excel", total=total)
    if len(items) == 1:
        da, db = agent_reviews[0]
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
