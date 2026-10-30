"""Remove ERAS boilerplate before LLM briefing extraction."""

from __future__ import annotations

import re

# (display name, header pattern, max body chars)
_SECTION_SPECS: list[tuple[str, re.Pattern[str], int]] = [
    ("EDUCATION", re.compile(r"^EDUCATION\s*$"), 2500),
    ("HONORS AND AWARDS", re.compile(r"^HONORS(?:\s+AND|\s*&)\s+AWARDS\s*$", re.I), 4000),
    ("PUBLICATIONS", re.compile(r"^PUBLICATIONS\s*$", re.I), 5000),
    ("RESEARCH ACTIVITIES", re.compile(r"^RESEARCH ACTIVITIES\s*$", re.I), 5000),
    ("EMPLOYMENT", re.compile(r"^EMPLOYMENT\s*$", re.I), 3500),
    ("EXPERIENCES", re.compile(r"^EXPERIENCES\s*$", re.I), 4000),
    ("PERSONAL STATEMENT", re.compile(r"^PERSONAL STATEMENT\s*$", re.I), 7000),
    ("MSPE", re.compile(r"^MSPE\s*$", re.I), 6000),
    ("LETTERS OF RECOMMENDATION", re.compile(r"^LETTERS OF RECOMMENDATION\s*$", re.I), 12000),
    ("LETTER", re.compile(r"^Letter of Recommendation\b", re.I), 8000),
    ("DEAN LETTER", re.compile(r"^Dean'?s?\s+Letter\b", re.I), 8000),
]

_PRIORITY = (
    "PERSONAL STATEMENT",
    "LETTER",
    "LETTERS OF RECOMMENDATION",
    "DEAN LETTER",
    "MSPE",
    "RESEARCH ACTIVITIES",
    "PUBLICATIONS",
    "EMPLOYMENT",
    "EXPERIENCES",
    "HONORS AND AWARDS",
    "EDUCATION",
)

_BOILERPLATE_LINE = re.compile(
    r"^(?:"
    r"Residency and Fellowship\s*$|"
    r"Matching Services\s*$|"
    r"Ophthalmology Residency(?: Application)?(?: Coversheet)?\s*$|"
    r"Applicant has waived access to\s*$|"
    r"Title:\s*$|"
    r"Department of Ophthalmology\s*$|"
    r"Credentials:\s*$|"
    r"Institution:\s*$|"
    r"Email:\s*$|"
    r"Phone:\s*$|"
    r"Address:\s*$|"
    r"DOCUMENTS INCLUDED\s*$|"
    r"Description\s*$|"
    r"Date Uploaded\s*$|"
    r"Document Source\s*$|"
    r"Course Description(?: Earned Grade)?\s*$|"
    r"Test Trans GPA:\s*|"
    r"Transfer Totals:\s*|"
    r"Term GPA\s+|"
    r"Term Earned\s+|"
    r"Dean's List\b.*|"
    r"\d{4}\s+(?:Fall|Spring|Summer|Winter)\s+Term\s*$"
    r")",
    re.I,
)

_TRANSCRIPT_LINE = re.compile(
    r"^(?:"
    r"[A-Z]{2,8}\s+\d{2,4}[A-Z]?\s|"
    r"\d+\.\d{3}\s+\d+\.\d{3}\s+[A-Z]{1,3}\s+0\.000\s*$|"
    r"Topic:\s*"
    r")",
    re.I,
)

_USMLE_REPORT = re.compile(
    r"Performance by Discipline Relative to Your Overall Step|"
    r"Score Report|"
    r"Examination History and Transcript",
    re.I,
)


def _match_section_header(line: str) -> tuple[str, re.Pattern[str], int] | None:
    stripped = line.strip()
    for name, pattern, cap in _SECTION_SPECS:
        if pattern.match(stripped):
            return name, pattern, cap
    return None


def _is_boilerplate_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _BOILERPLATE_LINE.match(stripped):
        return True
    if _TRANSCRIPT_LINE.match(stripped):
        return True
    if re.match(r"^[A-Z]{2,6}\s+\d{3,4}[A-Z]?\s+\S", stripped):
        return True
    if re.match(r"^\d{1,2}/\d{2}/\d{4}\s*$", stripped):
        return True
    return False


def _clean_body(name: str, body: str, cap: int) -> str:
    lines: list[str] = []
    for line in body.splitlines():
        if _is_boilerplate_line(line):
            continue
        if name == "MSPE" and re.search(r"CORE\s+.*Clerkship|\bClerkship\b.*\d+\.\d{3}", line, re.I):
            continue
        if _USMLE_REPORT.search(line):
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    if len(text) > cap:
        text = text[: cap - 3].rstrip() + "..."
    return text


def _find_sections(text: str) -> list[tuple[str, str, int]]:
    """Return (header, body, cap) for recognized ERAS sections."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str], int]] = []
    current_header: str | None = None
    current_cap = 0
    current_body: list[str] = []

    def flush() -> None:
        nonlocal current_header, current_body, current_cap
        if current_header and any(ln.strip() for ln in current_body):
            sections.append((current_header, current_body, current_cap))
        current_header = None
        current_body = []
        current_cap = 0

    for line in lines:
        match = _match_section_header(line)
        if match:
            flush()
            current_header, _, current_cap = match
            continue
        if current_header is not None:
            if _is_boilerplate_line(line):
                continue
            current_body.append(line)
    flush()

    out: list[tuple[str, str, int]] = []
    for header, body_lines, cap in sections:
        body = _clean_body(header, "\n".join(body_lines), cap)
        if body:
            out.append((header, body, cap))
    return out


_LETTER_START = re.compile(
    r"(?:"
    r"To Whom It May Concern|"
    r"It is (?:with|my honor|a pleasure).*recommend|"
    r"I (?:am pleased|enthusiastically|highly|strongly) (?:recommend|support)|"
    r"without reservation that I write this letter"
    r")",
    re.I,
)


def _extract_letter_excerpts(text: str, max_chars: int = 10000) -> str:
    """Pull letter-of-recommendation narrative blocks from unstructured tail content."""
    chunks: list[str] = []
    seen_starts: set[int] = set()
    for m in _LETTER_START.finditer(text):
        start = max(0, m.start() - 120)
        if any(abs(start - s) < 800 for s in seen_starts):
            continue
        seen_starts.add(start)
        chunk = text[start : start + 3500].strip()
        if len(chunk) > 200:
            chunks.append(chunk)
    combined = "\n\n---\n\n".join(chunks)
    if len(combined) > max_chars:
        combined = combined[: max_chars - 3].rstrip() + "..."
    return combined.strip()


def _assemble_sections(sections: list[tuple[str, str, int]], max_chars: int) -> str:
    by_name: dict[str, tuple[str, str, int]] = {}
    for header, body, cap in sections:
        if header not in by_name or len(body) > len(by_name[header][1]):
            by_name[header] = (header, body, cap)

    parts: list[str] = []
    total = 0
    for header_name in _PRIORITY:
        entry = by_name.get(header_name)
        if not entry:
            continue
        header, body, _cap = entry
        chunk = f"=== {header} ===\n{body}"
        if total + len(chunk) > max_chars:
            remaining = max_chars - total
            if remaining > 400:
                parts.append(chunk[:remaining])
            return "\n\n".join(parts).strip()
        parts.append(chunk)
        total += len(chunk) + 2
    return "\n\n".join(parts).strip()


def strip_for_llm(text: str, max_chars: int = 48000) -> str:
    """
    Build a compact application excerpt for one LLM call.

    Keeps narrative ERAS sections and drops transcript tables, letter-writer
    contact blocks, and repeated coversheet headers.
    """
    sections = _find_sections(text)
    if sections:
        body = _assemble_sections(sections, max_chars)
        letters = _extract_letter_excerpts(text)
        if letters:
            letter_block = f"=== LETTER EXCERPTS ===\n{letters}"
            if body:
                combined = f"{letter_block}\n\n{body}"
                if len(combined) > max_chars:
                    # Prefer letter excerpts + highest-priority sections.
                    room = max_chars - len(letter_block) - 2
                    body = _assemble_sections(sections, max(0, room))
                    return f"{letter_block}\n\n{body}".strip() if body else letter_block[:max_chars]
                return combined.strip()
            return letter_block[:max_chars]
        if body:
            return body

    cleaned: list[str] = []
    for line in text.splitlines():
        if not _is_boilerplate_line(line):
            cleaned.append(line)
    return "\n".join(cleaned).strip()[:max_chars]
