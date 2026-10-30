"""Full pipeline: step-1 Python scoring + LLM briefing + Doc A / Doc B agents."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from application_analyzer.excel_export import write_multi_applicant_workbook, write_workbook
from application_analyzer.facts import ExtractedFacts, extract_facts_from_text
from application_analyzer.pdf_extract import extract_text_from_pdf
from application_analyzer.scoring import RubricScores, compute_scores
from llm_score.brief import extract_reviewer_brief
from llm_score.llm_client import DEFAULT_MODEL
from llm_score.markdown_export import briefing_to_markdown, review_to_markdown
from llm_score.reviewers import AgentReview, run_doc_a, run_doc_b
from llm_score.text_strip import strip_for_llm


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _safe_md_filename(name: str | None, pdf: Path, suffix: str) -> str:
    base = name or pdf.stem
    cleaned = re.sub(r"[^\w\s\-().]", "", base).strip().replace(" ", "_")
    return f"{cleaned or pdf.stem}{suffix}.md"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Process ERAS PDFs: Python step-1 scores, factual briefing (1 LLM call), "
            "and independent Doc A / Doc B agent reviews (2 LLM calls)."
        )
    )
    p.add_argument("inputs", nargs="+", type=Path, help="One or more application PDF files")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .xlsx path (default: screening_scores.xlsx in the first PDF's directory)",
    )
    p.add_argument(
        "--briefings-dir",
        type=Path,
        default=None,
        help="Directory for Markdown outputs (default: briefings/ next to the Excel output)",
    )
    p.add_argument(
        "--template",
        type=Path,
        default=None,
        help="Rubric Excel template path (default: rubric/template.xlsx if present)",
    )
    p.add_argument(
        "--school-list",
        type=Path,
        default=None,
        help="YAML with medical_school_top25 and undergraduate_top25",
    )
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model name (default: {DEFAULT_MODEL})",
    )
    p.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip all LLM steps (step-1 Excel only)",
    )
    p.add_argument(
        "--skip-agents",
        action="store_true",
        help="Run factual briefing only; skip Doc A and Doc B agent calls",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print extraction details as JSON to stdout",
    )
    p.add_argument(
        "--keep-template-sheets",
        action="store_true",
        help="Do not remove original sheets from the template workbook",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = _project_root()
    template = args.template or (root / "rubric" / "template.xlsx")
    if not template.is_file():
        print(
            f"Template not found: {template}. Pass --template /path/to/rubric_template.xlsx",
            file=sys.stderr,
        )
        return 1

    out = args.output or (args.inputs[0].resolve().parent / "screening_scores.xlsx")
    briefings_dir = args.briefings_dir or (out.parent / "briefings")
    briefings_dir.mkdir(parents=True, exist_ok=True)

    items: list[tuple[ExtractedFacts, RubricScores]] = []
    agent_reviews: list[tuple[AgentReview | None, AgentReview | None]] = []
    payload: list[dict] = []

    for pdf in args.inputs:
        if not pdf.is_file():
            print(f"Missing PDF: {pdf}", file=sys.stderr)
            return 1

        text = extract_text_from_pdf(pdf)
        facts = extract_facts_from_text(text, pdf)
        scores = compute_scores(facts, text, str(args.school_list) if args.school_list else None)
        items.append((facts, scores))

        brief: dict | None = None
        doc_a: AgentReview | None = None
        doc_b: AgentReview | None = None
        stripped_len = 0

        if not args.skip_llm:
            stripped = strip_for_llm(text)
            stripped_len = len(stripped)
            name = facts.applicant_name or pdf.name
            print(f"Briefing {name} ({stripped_len} chars)...")
            brief = extract_reviewer_brief(stripped, model=args.model)
            brief_md = briefing_to_markdown(
                facts.applicant_name or pdf.stem,
                brief,
                source_file=pdf.name,
            )
            brief_path = briefings_dir / _safe_md_filename(facts.applicant_name, pdf, "_brief")
            brief_path.write_text(brief_md, encoding="utf-8")
            print(f"  Wrote {brief_path}")

            if not args.skip_agents:
                briefing_json = json.dumps(brief, indent=2, ensure_ascii=False)
                print(f"  Doc A reviewing {name}...")
                doc_a = run_doc_a(stripped, briefing_json, model=args.model)
                doc_a_path = briefings_dir / _safe_md_filename(facts.applicant_name, pdf, "_doc_a")
                doc_a_path.write_text(
                    review_to_markdown(facts.applicant_name or pdf.stem, doc_a, source_file=pdf.name),
                    encoding="utf-8",
                )
                print(f"  Wrote {doc_a_path}")

                print(f"  Doc B reviewing {name}...")
                doc_b = run_doc_b(stripped, briefing_json, model=args.model)
                doc_b_path = briefings_dir / _safe_md_filename(facts.applicant_name, pdf, "_doc_b")
                doc_b_path.write_text(
                    review_to_markdown(facts.applicant_name or pdf.stem, doc_b, source_file=pdf.name),
                    encoding="utf-8",
                )
                print(f"  Wrote {doc_b_path}")

        agent_reviews.append((doc_a, doc_b))
        payload.append(
            {
                "file": str(pdf),
                "applicant_name": facts.applicant_name,
                "stripped_chars": stripped_len,
                "briefing": brief,
                "doc_a": None if doc_a is None else {
                    "summary": doc_a.summary,
                    "scores": doc_a.scores,
                    "rationale": doc_a.rationale,
                    "error": doc_a.error,
                },
                "doc_b": None if doc_b is None else {
                    "summary": doc_b.summary,
                    "scores": doc_b.scores,
                    "rationale": doc_b.rationale,
                    "error": doc_b.error,
                },
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
            }
        )

    if args.json:
        print(json.dumps(payload, indent=2))

    strip_sheets = not args.keep_template_sheets
    if len(items) == 1:
        da, db = agent_reviews[0] if agent_reviews else (None, None)
        write_workbook(
            template,
            items[0][0],
            items[0][1],
            out,
            strip_template_sheets=strip_sheets,
            doc_a=da,
            doc_b=db,
        )
    else:
        write_multi_applicant_workbook(
            template,
            items,
            out,
            strip_template_sheets=strip_sheets,
            agent_reviews=agent_reviews or None,
        )

    print(f"Wrote {out}")
    if not args.skip_llm:
        print(f"Markdown outputs in {briefings_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
