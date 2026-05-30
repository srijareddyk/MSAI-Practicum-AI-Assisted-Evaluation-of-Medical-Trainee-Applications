

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from application_analyzer.excel_export import write_multi_applicant_workbook, write_workbook
from application_analyzer.facts import ExtractedFacts, extract_facts_from_text
from application_analyzer.pdf_extract import extract_text_from_pdf
from application_analyzer.scoring import RubricScores, compute_scores


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Step 1 only (no LLM): extract quantifiable rubric fields from ERAS PDFs "
            "and write Excel worksheets with Doc A / Doc B score columns."
        )
    )
    p.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="One or more application PDF files",
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .xlsx path (default: step1_scores.xlsx in the first PDF's directory)",
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
        help="YAML with medical_school_top25 and undergraduate_top25 (default: packaged config)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print extraction/scoring details as JSON to stdout",
    )
    p.add_argument(
        "--keep-template-sheets",
        action="store_true",
        help="Do not remove original sheets from the template workbook (for debugging)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = _project_root()
    default_template = root / "rubric" / "template.xlsx"
    template = args.template or default_template
    if not template.is_file():
        print(
            f"Template not found: {template}. Pass --template /path/to/rubric_template.xlsx",
            file=sys.stderr,
        )
        return 1

    out = args.output
    if out is None:
        out = args.inputs[0].resolve().parent / "step1_scores.xlsx"

    items: list[tuple[ExtractedFacts, RubricScores]] = []
    payload: list[dict] = []

    for pdf in args.inputs:
        if not pdf.is_file():
            print(f"Missing PDF: {pdf}", file=sys.stderr)
            return 1
        text = extract_text_from_pdf(pdf)
        facts = extract_facts_from_text(text, pdf)
        scores = compute_scores(facts, text, str(args.school_list) if args.school_list else None)
        items.append((facts, scores))
        payload.append(
            {
                "file": str(pdf),
                "applicant_name": facts.applicant_name,
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

    strip = not args.keep_template_sheets
    if len(items) == 1:
        write_workbook(template, items[0][0], items[0][1], out, strip_template_sheets=strip)
    else:
        write_multi_applicant_workbook(template, items, out, strip_template_sheets=strip)

    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
