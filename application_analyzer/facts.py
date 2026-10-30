"""Heuristic extraction of rubric-relevant facts from raw PDF text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractedFacts:
    source_path: str
    applicant_name: str | None = None
    medical_school: str | None = None
    undergraduate_institution: str | None = None
    undergraduate_cum_gpa: float | None = None
    usmle_step1_times_taken: int | None = None
    usmle_step1_result: str | None = None  # Pass | Fail | Unknown
    notes: list[str] = field(default_factory=list)


def _name_from_filename(path: Path) -> str | None:
    stem = path.stem
    # e.g. Abbass,_Nadia_AU84199_OPHTH-R_2025-26
    m = re.match(r"^([^,]+),_([^_]+)_", stem)
    if not m:
        return None
    last, first = m.group(1).strip(), m.group(2).strip()
    return f"{first} {last}".replace("_", " ")


def _find_medical_school(text: str) -> str | None:
    head = text[:16000]
    m = re.search(
        r"Medical\s+School\s*:\s*\n((?:[ \t]*[^\n]+\n?){1,5}?)\s*Medical\s+School\s+Country",
        head,
        flags=re.I | re.S,
    )
    if m:
        joined = " ".join(x.strip() for x in m.group(1).splitlines() if x.strip())
        if len(joined) > 2:
            return joined[:220]
    m2 = re.search(
        r"(?:\d{2}/\d{4}\s*-\s*\d{2}/\d{4})\s*\n\s*Medical\s+School\s*\n\s*([^\n]+)",
        head,
        flags=re.I | re.S,
    )
    if m2:
        return m2.group(1).strip()[:220]
    candidates: list[str] = []
    for m3 in re.finditer(r"Medical\s+School\s*:+\s*([^\n]+)", head, flags=re.I):
        cand = m3.group(1).strip()
        cand = re.split(r"Medical\s+School\s+Country", cand, flags=re.I)[0].strip()
        if len(cand) < 3:
            continue
        if re.search(r"matriculation|initial\s+matric|date\s+of\s+initial", cand, flags=re.I):
            continue
        candidates.append(cand)
    return (candidates[0][:220]) if candidates else None


def _find_undergrad_block(text: str) -> str:
    low = text.lower()
    m = re.search(
        r"undergraduate\s+(?:education|record)|beginning\s+of\s+undergraduate",
        low,
    )
    start = m.start() if m else 0
    slice_ = text[start:]
    low2 = slice_.lower()
    end = len(slice_)
    for k in (
        "beginning of medicine record",
        "program: doctor of medicine",
        "medicine professional",
        "end of undergraduate record",
    ):
        j = low2.find(k)
        if j != -1 and j > 150:
            end = min(end, j)
    return slice_[:end]


def _find_undergrad_institution(text: str) -> str | None:
    m = re.search(
        r"Undergraduate\s*\n\s*education\s*\n\s*([^\n]+)",
        text,
        flags=re.I,
    )
    if m:
        inst = re.sub(r"\s+", " ", m.group(1).strip())
        if len(inst) > 4:
            return inst[:200]
    block = _find_undergrad_block(text)
    m = re.search(
        r"Program:\s*Arts\s*&\s*Sciences\s+Undergraduate\s*\n\s*([^\n]+)",
        block,
        flags=re.I,
    )
    if m:
        inst = re.sub(r"\s+", " ", m.group(1).strip())
        if len(inst) > 5:
            return inst.split("Major")[0].strip()[:200]
    m = re.search(
        r"\d{2}/\d{4}\s*--\s*\d{2}/\d{4}\s+([A-Za-z][^\n]{3,120})",
        block,
    )
    if m:
        line = m.group(1).strip().split("Address")[0].strip()
        line = re.sub(r"\s+", " ", line)
        if "University" in line or "College" in line:
            return line[:200]
    return None


def _extract_undergrad_gpa(text: str) -> float | None:
    def _collect_gpas(candidate_text: str) -> list[float]:
        vals: list[float] = []
        # Transcript variants such as "Total to Date GPA: 3.667"
        for m in re.finditer(
            r"(?:Total\s+to\s+Date|Overall|Cumulative|Cum)\s+GPA\s*:?\s*([\d.]+)",
            candidate_text,
            flags=re.I,
        ):
            try:
                g = float(m.group(1))
                if 2.0 <= g <= 4.3:
                    vals.append(g)
            except ValueError:
                continue
        for m in re.finditer(r"Cum(?:ulative)?\s+GPA\s*:?\s*([\d.]+)", candidate_text, flags=re.I):
            try:
                g = float(m.group(1))
                if 2.0 <= g <= 4.3:
                    vals.append(g)
            except ValueError:
                continue
        for m in re.finditer(r"\bGPA\s*:?\s*([\d.]+)\s*$", candidate_text, flags=re.I | re.M):
            try:
                g = float(m.group(1))
                if 2.0 <= g <= 4.3:
                    vals.append(g)
            except ValueError:
                continue
        return vals

    # Primary: undergraduate-focused block.
    block = _find_undergrad_block(text)
    gpas = _collect_gpas(block)
    if gpas:
        # Prefer final cumulative GPA (usually last in undergrad transcript block)
        return gpas[-1]

    # Fallback 1: explicit "Beginning/End of Undergraduate Record" span across full PDF.
    m = re.search(
        r"Beginning of Undergraduate Record(.*?)End of Undergraduate Record",
        text,
        flags=re.I | re.S,
    )
    if m:
        gpas = _collect_gpas(m.group(1))
        if gpas:
            return gpas[-1]

    # Fallback 2: search entire PDF (covers cases where undergrad block detection misses layout).
    gpas = _collect_gpas(text)
    if gpas:
        return gpas[-1]
    return None


def _extract_usmle_step1(text: str) -> tuple[int | None, str | None]:
    """
    Parse USMLE Step 1 date / times taken / Pass|Fail (single-line or stacked ERAS table).
    """
    m = re.search(
        r"Step\s*1\s*\n\s*(\d{1,2}/\d{1,2}/\d{4})\s*\n\s*(\d+)\s*\n\s*(Pass|Fail)",
        text,
        flags=re.I | re.S,
    )
    if m:
        return int(m.group(2)), m.group(3).capitalize()
    m = re.search(
        r"Step\s*1\s+\d{1,2}/\d{1,2}/\d{4}\s+(?:\d{3}\s+)?(\d+)\s+(Pass|Fail)",
        text,
        flags=re.I,
    )
    if m:
        return int(m.group(1)), m.group(2).capitalize()
    m = re.search(
        r"Step\s*1\s+\d{1,2}/\d{1,2}/\d{4}\s+Pass\b",
        text,
        flags=re.I,
    )
    if m:
        return 1, "Pass"
    return None, None


def _applicant_from_pdf(text: str) -> str | None:
    m = re.search(r"Applicant'?s?\s+Name\s*:?\s*([^\n]+)", text, flags=re.I)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:120]
    return None


def extract_facts_from_text(text: str, source: Path) -> ExtractedFacts:
    facts = ExtractedFacts(source_path=str(source))
    facts.applicant_name = _applicant_from_pdf(text) or _name_from_filename(source)
    facts.medical_school = _find_medical_school(text)
    facts.undergraduate_institution = _find_undergrad_institution(text)
    facts.undergraduate_cum_gpa = _extract_undergrad_gpa(text)
    t, r = _extract_usmle_step1(text)
    facts.usmle_step1_times_taken = t
    facts.usmle_step1_result = r
    if facts.medical_school is None:
        facts.notes.append("Medical school not detected from coversheet; check PDF.")
    if facts.undergraduate_cum_gpa is None:
        facts.notes.append("Undergraduate cumulative GPA not detected; check transcript layout.")
    if facts.usmle_step1_result is None:
        facts.notes.append("USMLE Step 1 line not detected; check examinations section.")
    return facts
