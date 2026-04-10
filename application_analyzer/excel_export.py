"""Write screening worksheets: copy rubric template, fill only step-1 score cells."""

from __future__ import annotations

import re
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from application_analyzer.facts import ExtractedFacts
from application_analyzer.scoring import RubricScores

# Matches Kurup worksheet layout (see rubric/*.xlsx)
ROW_APPLICANT_NAME = 2
COL_APPLICANT_NAME = 2
ROW_TOTAL_BAND = 8
COL_SCORE_START = 7  # G — Scientific Pursuits block (cleared for step 1)
ROW_RUBRIC_ROWS = {
    "medical_school_quality": 14,
    "medical_school_performance": 15,
    "undergraduate_quality": 16,
    "undergraduate_performance": 17,
    "usmle_step1": 18,
}
COL_RUBRIC_SCORE = 4  # D
COL_SUMMARY = {"msq": 14, "msp": 15, "uq": 16, "up": 17, "usmle": 18}
PURPLE_FILL = PatternFill(fill_type="solid", fgColor="D9B3FF")


def _safe_sheet_title(name: str) -> str:
    bad = r'[:\\/?*\[\]]'
    t = re.sub(bad, "-", name).strip()
    return (t[:31] if len(t) > 31 else t) or "Applicant"


def _copy_sheet(wb: Workbook, source: Worksheet, title: str) -> Worksheet:
    """Duplicate a worksheet preserving cell styles (openpyxl copy_worksheet)."""
    target = wb.copy_worksheet(source)
    target.title = _safe_sheet_title(title)
    return target


def _clear_non_step1_scores(ws: Worksheet) -> None:
    """Remove reviewer-entered points from earlier rubric rows (step 1 leaves them blank)."""
    for r in range(5, 13):
        ws.cell(row=r, column=COL_RUBRIC_SCORE).value = None
    ws.cell(row=ROW_TOTAL_BAND, column=6).value = None  # F8 total
    for c in range(COL_SCORE_START, COL_SUMMARY["msq"]):
        ws.cell(row=ROW_TOTAL_BAND, column=c).value = None


def _set_score_cell(ws: Worksheet, row: int, value: int | float | str | None) -> None:
    cell = ws.cell(row=row, column=COL_RUBRIC_SCORE)
    cell.value = value
    if value is not None:
        cell.fill = PURPLE_FILL


def _set_summary_cell(
    ws: Worksheet,
    column: int,
    value: int | float | str | None,
) -> None:
    cell = ws.cell(row=ROW_TOTAL_BAND, column=column)
    cell.value = value
    if value is not None:
        cell.fill = PURPLE_FILL


def _strip_original_sheets(wb: Workbook, original_names: list[str]) -> None:
    for name in original_names:
        if name in wb.sheetnames:
            wb.remove(wb[name])


def write_workbook(
    template_path: Path,
    facts: ExtractedFacts,
    scores: RubricScores,
    output_path: Path,
    template_sheet_index: int = 0,
    strip_template_sheets: bool = True,
) -> None:
    wb = load_workbook(template_path)
    sheetnames = wb.sheetnames
    if not sheetnames:
        raise ValueError("Template workbook has no sheets")
    original_names = list(sheetnames)
    src_name = sheetnames[min(template_sheet_index, len(sheetnames) - 1)]
    source = wb[src_name]
    title = facts.applicant_name or Path(facts.source_path).stem
    ws = _copy_sheet(wb, source, title)
    _clear_non_step1_scores(ws)

    ws.cell(row=ROW_APPLICANT_NAME, column=COL_APPLICANT_NAME).value = facts.applicant_name

    _set_score_cell(ws, ROW_RUBRIC_ROWS["medical_school_quality"], scores.medical_school_quality)
    _set_score_cell(ws, ROW_RUBRIC_ROWS["medical_school_performance"], scores.medical_school_performance)
    _set_score_cell(ws, ROW_RUBRIC_ROWS["undergraduate_quality"], scores.undergraduate_quality)
    _set_score_cell(ws, ROW_RUBRIC_ROWS["undergraduate_performance"], scores.undergraduate_performance)
    _set_score_cell(ws, ROW_RUBRIC_ROWS["usmle_step1"], scores.usmle_step1)

    _set_summary_cell(ws, COL_SUMMARY["msq"], scores.medical_school_quality)
    _set_summary_cell(ws, COL_SUMMARY["msp"], scores.medical_school_performance)
    _set_summary_cell(ws, COL_SUMMARY["uq"], scores.undergraduate_quality)
    _set_summary_cell(ws, COL_SUMMARY["up"], scores.undergraduate_performance)
    _set_summary_cell(ws, COL_SUMMARY["usmle"], scores.usmle_step1)

    if strip_template_sheets:
        _strip_original_sheets(wb, original_names)
    wb.save(output_path)


def write_multi_applicant_workbook(
    template_path: Path,
    items: list[tuple[ExtractedFacts, RubricScores]],
    output_path: Path,
    template_sheet_index: int = 0,
    strip_template_sheets: bool = True,
) -> None:
    wb = load_workbook(template_path)
    sheetnames = wb.sheetnames
    if not sheetnames:
        raise ValueError("Template workbook has no sheets")
    original_names = list(sheetnames)
    src_name = sheetnames[min(template_sheet_index, len(sheetnames) - 1)]
    source = wb[src_name]

    for facts, scores in items:
        title = facts.applicant_name or Path(facts.source_path).stem
        ws = _copy_sheet(wb, source, title)
        _clear_non_step1_scores(ws)
        ws.cell(row=ROW_APPLICANT_NAME, column=COL_APPLICANT_NAME).value = facts.applicant_name
        _set_score_cell(ws, ROW_RUBRIC_ROWS["medical_school_quality"], scores.medical_school_quality)
        _set_score_cell(ws, ROW_RUBRIC_ROWS["medical_school_performance"], scores.medical_school_performance)
        _set_score_cell(ws, ROW_RUBRIC_ROWS["undergraduate_quality"], scores.undergraduate_quality)
        _set_score_cell(ws, ROW_RUBRIC_ROWS["undergraduate_performance"], scores.undergraduate_performance)
        _set_score_cell(ws, ROW_RUBRIC_ROWS["usmle_step1"], scores.usmle_step1)
        _set_summary_cell(ws, COL_SUMMARY["msq"], scores.medical_school_quality)
        _set_summary_cell(ws, COL_SUMMARY["msp"], scores.medical_school_performance)
        _set_summary_cell(ws, COL_SUMMARY["uq"], scores.undergraduate_quality)
        _set_summary_cell(ws, COL_SUMMARY["up"], scores.undergraduate_performance)
        _set_summary_cell(ws, COL_SUMMARY["usmle"], scores.usmle_step1)

    if strip_template_sheets:
        _strip_original_sheets(wb, original_names)
    wb.save(output_path)
