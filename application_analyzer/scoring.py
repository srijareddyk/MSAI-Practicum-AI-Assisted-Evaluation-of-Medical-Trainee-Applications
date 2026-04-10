"""Map extracted facts + transcript text to rubric scores (step 1 only)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pathlib import Path

from application_analyzer.facts import ExtractedFacts
from application_analyzer.schools import is_top_school, load_school_lists


@dataclass
class RubricScores:
    medical_school_quality: int | float | None  # 4 or 0
    medical_school_performance: int | float | None  # 4,3,2,1,0 or 2.25
    undergraduate_quality: int | None  # 2 or 0
    undergraduate_performance: int | None  # 4-0
    usmle_step1: str | None  # P or F


HONOR_TOKENS = frozenset({"H", "HONORS", "HONOR"})
HIGH_PASS_TOKENS = frozenset({"HP", "HIGH", "COM", "CCD", "HIGHPASS"})
PASS_TOKENS = frozenset({"P", "PASS", "S", "M", "LP"})  # M = met/satisfactory in some transcripts
FAIL_TOKENS = frozenset({"F", "FAIL", "U"})

ROTATIONS: list[tuple[str, re.Pattern[str]]] = [
    ("med", re.compile(r"Internal\s+Medicine(?:\s+Clerkship)?", re.I)),
    ("surg", re.compile(r"Surgery\s+Clerkship|\bGeneral\s+Surgery\b.*Clerkship", re.I)),
    ("peds", re.compile(r"Pediatrics?\s+Clerkship", re.I)),
    ("obgyn", re.compile(r"OB\s*&\s*GYN|Obstetrics|Gynecology.*Clerkship", re.I)),
    ("neuro", re.compile(r"Neuroscience\s+Clerkship|Neurology\s+Clerkship", re.I)),
]


def _merge_wrapped_clerkship_lines(text: str) -> str:
    """
    Some transcripts wrap after the rotation name: 'CORE ... Internal Medicine' /
    'Clerkship' / '8.00 8.00 H'. Join those fragments so grades are on the same line.
    """
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if (
            i + 2 < len(lines)
            and "CORE" in ln
            and lines[i + 1].strip().lower() == "clerkship"
            and re.search(
                r"(Internal\s+Medicine|Pediatrics|Surgery|OB|GYN|Neuroscience|Neurology)",
                ln,
                re.I,
            )
        ):
            merged = f"{ln.rstrip()} {lines[i + 1].strip()} {lines[i + 2].strip()}"
            out.append(merged)
            i += 3
            continue
        out.append(ln)
        i += 1
    return "\n".join(out)


def _extract_rotation_grade(line: str) -> str | None:
    """Return clerkship grade token; ignores course codes like 3102B."""
    m = re.search(
        r"(?:\d+\.\d+\s+){1,4}\s*([A-Z]{2,3}|[HPSM]|CCD|COM|HP|LP)\s+0\.000\s*$",
        line,
        re.I,
    )
    if m:
        return m.group(1).upper()
    tokens = re.findall(r"[A-Za-z]+|\d+\.?\d*", line)
    for t in reversed(tokens):
        if re.match(r"^\d", t):
            continue
        if re.match(r"^\d{4}[A-Z]?$", t, re.I):
            continue
        if len(t) == 1 and t in "BCDF" and re.search(r"\d" + re.escape(t) + r"\b", line):
            continue
        u = t.upper()
        if u in HONOR_TOKENS | HIGH_PASS_TOKENS | FAIL_TOKENS:
            return u
        if u in {"P", "S", "M", "LP"}:
            return u
        if len(t) <= 3 and t.isalpha() and u not in {"CORE", "THE", "AND"}:
            return u
    return None


def _line_is_core_clerkship(line: str) -> bool:
    if "Clerkship" not in line and "CORE" not in line:
        return False
    if re.search(r"Family\s+Medicine|Psychiatry|Ophthalmology|Elective|Research", line, re.I):
        return False
    return any(p.search(line) for _, p in ROTATIONS)


def _classify_rotation(line: str) -> str | None:
    for key, pat in ROTATIONS:
        if pat.search(line):
            return key
    return None


def _normalize_mspe_token(raw: str) -> str:
    u = raw.strip().upper()
    if u in {"PASS", "PAS"}:
        return "P"
    if "HONOR" in u:
        return "H"
    if u in {"HP", "HIGH", "HIGHPASS"}:
        return "HP"
    if u in HONOR_TOKENS | HIGH_PASS_TOKENS | PASS_TOKENS | FAIL_TOKENS:
        return u
    return u[:6]


def _apply_mspe_style_grades(full_text: str, found: dict[str, str]) -> None:
    """
    Narrative MSPE blocks often use lines like 'M3 Internal Medicine (...): PASS'.
    Fill rotation buckets when transcript tables (CORE ...) are absent.
    """
    patterns: list[tuple[str, str]] = [
        (r"Internal\s+Medicine\s*\([^)]*\)\s*:\s*([A-Za-z]+)", "med"),
        (r"(?:^|\n)\s*Surgery\s*\([^)]*\)\s*:\s*([A-Za-z]+)", "surg"),
        (r"Pediatrics\s*\([^)]*\)\s*:\s*([A-Za-z]+)", "peds"),
        (r"Obstetrics\s+and\s+Gynecology[^:\n]{0,200}:\s*([A-Za-z]+)", "obgyn"),
        (r"Neurology\s*\([^)]*\)\s*:\s*([A-Za-z]+)", "neuro"),
    ]
    for pat, key in patterns:
        if key in found:
            continue
        m = re.search(pat, full_text, flags=re.I | re.M)
        if not m:
            continue
        tok = _normalize_mspe_token(m.group(1))
        if tok:
            prev = found.get(key)
            if prev is None or _grade_rank(tok) > _grade_rank(prev):
                found[key] = tok


def _collect_core_grades(full_text: str) -> dict[str, str]:
    """Map rotation bucket -> best observed grade token for that rotation."""
    found: dict[str, str] = {}
    full_text = _merge_wrapped_clerkship_lines(full_text)
    for line in full_text.splitlines():
        if not _line_is_core_clerkship(line):
            continue
        rot = _classify_rotation(line)
        if rot is None:
            continue
        g = _extract_rotation_grade(line)
        if g is None:
            continue
        prev = found.get(rot)
        rank = _grade_rank(g)
        if prev is None or rank > _grade_rank(prev):
            found[rot] = g
    if len(found) < 3:
        _apply_mspe_style_grades(full_text, found)
    return found


def _grade_rank(g: str) -> int:
    u = g.upper()
    if u in HONOR_TOKENS:
        return 5
    if u in HIGH_PASS_TOKENS or u == "HIGH":
        return 4
    if u in PASS_TOKENS:
        return 3
    if u in FAIL_TOKENS:
        return 0
    return 2


def _honors_count(grades: dict[str, str]) -> int:
    return sum(1 for g in grades.values() if g.upper() in HONOR_TOKENS)


def _high_pass_count(grades: dict[str, str]) -> int:
    return sum(1 for g in grades.values() if g.upper() in HIGH_PASS_TOKENS)


def _struggled(grades: dict[str, str]) -> bool:
    return any(g.upper() in FAIL_TOKENS for g in grades.values())


def _pass_fail_only_curriculum(
    medical_school: str | None,
    cfg: dict,
) -> bool:
    """Rubric *** : optional automation via YAML keywords only (avoids MSPE false positives)."""
    keys = cfg.get("pass_fail_only_medical_school_keywords") or []
    if not keys or not medical_school:
        return False
    low = medical_school.lower()
    return any(k.strip().lower() in low for k in keys if k and str(k).strip())


def score_undergraduate_performance(gpa: float | None) -> int | None:
    if gpa is None:
        return None
    if gpa >= 3.8:
        return 4
    if gpa >= 3.5:
        return 3
    if gpa >= 3.25:
        return 2
    if gpa >= 3.0:
        return 1
    return 0


def score_usmle_step1(facts: ExtractedFacts) -> str | None:
    if facts.usmle_step1_result is None or facts.usmle_step1_times_taken is None:
        return None
    if facts.usmle_step1_result.lower() != "pass":
        return "F"
    if facts.usmle_step1_times_taken != 1:
        return "F"
    return "P"


def score_medical_school_performance(
    full_text: str,
    medical_school: str | None,
    cfg: dict,
) -> int | float | None:
    grades = _collect_core_grades(full_text)
    if not grades:
        return None
    if _struggled(grades):
        return 0
    h = _honors_count(grades)
    hp = _high_pass_count(grades)
    if h >= 3:
        return 4
    if h in (1, 2):
        return 3
    if h == 0 and hp >= 1:
        return 2
    if h == 0 and hp == 0 and not _struggled(grades):
        if _pass_fail_only_curriculum(medical_school, cfg):
            return 2.25
        return 1
    return None


def compute_scores(
    facts: ExtractedFacts,
    full_text: str,
    school_list_path: str | None = None,
) -> RubricScores:
    cfg = load_school_lists(Path(school_list_path) if school_list_path else None)
    med_top = cfg.get("medical_school_top25") or []
    ug_top = cfg.get("undergraduate_top25") or []

    msq = 4 if is_top_school(facts.medical_school, med_top) else 0
    uq = 2 if is_top_school(facts.undergraduate_institution, ug_top) else 0
    up = score_undergraduate_performance(facts.undergraduate_cum_gpa)
    usmle = score_usmle_step1(facts)
    msp = score_medical_school_performance(full_text, facts.medical_school, cfg)

    return RubricScores(
        medical_school_quality=msq,
        medical_school_performance=msp,
        undergraduate_quality=uq,
        undergraduate_performance=up,
        usmle_step1=usmle,
    )
