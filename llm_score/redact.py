"""Local identifier redaction before cloud LLM calls.

Step-1 scoring still uses the original text on this machine. Only the cloud
payload is rewritten. This is strong pattern redaction, not a legal FERPA
guarantee — publications and unique career facts can still identify someone.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from application_analyzer.facts import ExtractedFacts
from llm_score.llm_client import LLM_PROVIDER

_STOP = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "from",
        "jr",
        "sr",
        "ii",
        "iii",
        "iv",
        "md",
        "phd",
        "do",
        "mba",
        "mph",
        "van",
        "von",
        "de",
        "la",
        "del",
        "st",
        "saint",
        "university",
        "college",
        "school",
        "hospital",
        "medical",
        "center",
        "applicant",
    }
)

_EMAIL = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]*)\d{3}[-.\s]*\d{4}(?!\d)"
)
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_DOB_NUMERIC = re.compile(
    r"\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b"
)
_DOB_WRITTEN = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},?\s+(?:19|20)\d{2}\b",
    re.I,
)
_AAMC = re.compile(r"\bAAMC(?:\s*ID)?\s*[:#]?\s*\d+\b", re.I)
_ERAS_ID = re.compile(r"\b(?:AAMC|ERAS|NRMP|USMLE|NBME)[#:\s\-]*[A-Z]{0,3}\d{5,}\b", re.I)
_FILENAME_ID = re.compile(r"\bAU\d{4,}\b", re.I)
_URL = re.compile(
    r"https?://[^\s]+|www\.[^\s]+|(?:linkedin\.com|github\.com)/[A-Za-z0-9\-_/]+",
    re.I,
)
_STREET = re.compile(
    r"\b\d{1,6}\s+(?:[NSEW]\.?\s+)?"
    r"[A-Za-z0-9.'\-]+(?:\s+[A-Za-z0-9.'\-]+){0,4}\s+"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|"
    r"Court|Ct|Way|Place|Pl|Circle|Cir|Parkway|Pkwy|Terrace|Ter|Trail|Trl)\.?"
    r"(?:\s+(?:Apt|Apartment|Unit|Suite|Ste|#)\.?\s*[A-Za-z0-9\-]+)?\b",
    re.I,
)
_CITY_STATE_ZIP = re.compile(
    r"\b[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){0,3},\s*"
    r"(?:[A-Z]{2}|[A-Z][a-z]+)\s+\d{5}(?:-\d{4})?\b"
)
_PO_BOX = re.compile(r"\bP\.?\s*O\.?\s*Box\s+\d+\b", re.I)
_ZIP_LINE = re.compile(r"\b\d{5}-\d{4}\b")

_NAME_LABEL = re.compile(
    r"(?im)^(?:Applicant(?:'s)?\s+Name|Preferred\s+Name|Legal\s+Name|"
    r"Full\s+Name|Name)\s*:?\s*(.+)$"
)
_ADDRESS_LABEL = re.compile(
    r"(?im)^((?:Current|Permanent|Mailing|Home|Local|Work)\s+Address|Address)\s*:?\s*(.*)$"
)
_IDENTITY_LABEL = re.compile(
    r"(?im)^("
    r"Date of Birth|DOB|Birth Date|Place of Birth|Country of Birth|"
    r"Phone(?: Number)?|Mobile|Cell(?: Phone)?|Home Phone|Work Phone|"
    r"E-?mail(?: Address)?|"
    r"AAMC\s*ID|USMLE\s*ID|NBME\s*ID|NRMP\s*(?:ID|#)?|ERAS\s*ID|"
    r"Social Security(?: Number)?|SSN|"
    r"Visa(?: Type)?|Citizenship|NPI"
    r")\s*:?\s*(.*)$"
)


def cloud_llm_enabled() -> bool:
    flag = os.getenv("REDACT_FOR_LLM", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    if flag in {"0", "false", "no", "off"}:
        return False
    return LLM_PROVIDER == "azure"


def _add_name_parts(raw: str, tokens: list[str], seen: set[str]) -> None:
    for part in re.split(r"[\s,._\-]+", raw):
        t = part.strip(" .")
        if len(t) < 2 or t.lower() in _STOP:
            continue
        if t.lower() in seen:
            continue
        if t.isdigit():
            continue
        seen.add(t.lower())
        tokens.append(t)


def _name_tokens(facts: ExtractedFacts, source: Path, harvest_from: str | None) -> list[str]:
    raw: list[str] = []
    if facts.applicant_name:
        raw.append(facts.applicant_name)
    stem = source.stem.replace("_", " ")
    m = re.match(r"^([^,]+),\s*([A-Za-z\-]+)", stem)
    if m:
        raw.append(f"{m.group(2)} {m.group(1)}")
        raw.append(m.group(1))
        raw.append(m.group(2))

    if harvest_from:
        for match in _NAME_LABEL.finditer(harvest_from[:20000]):
            raw.append(match.group(1))
        # Common ERAS last, first header near the top of the file.
        head = harvest_from[:4000]
        comma = re.search(r"^([A-Z][A-Za-z'\-]+),\s+([A-Z][A-Za-z'\-]+)(?:\s+([A-Z][A-Za-z'\-]+))?\s*$", head, re.M)
        if comma:
            raw.extend(p for p in comma.groups() if p)

    tokens: list[str] = []
    seen: set[str] = set()
    for chunk in raw:
        _add_name_parts(chunk, tokens, seen)
        # Also keep "First Last" / "Last, First" as phrases.
        cleaned = re.sub(r"\s+", " ", chunk).strip()
        if " " in cleaned and cleaned.lower() not in seen and len(cleaned) > 3:
            seen.add(cleaned.lower())
            tokens.append(cleaned)
    tokens.sort(key=len, reverse=True)
    return tokens


def _harvest_address_blobs(text: str) -> list[str]:
    blobs: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        match = _ADDRESS_LABEL.match(lines[i])
        if not match:
            i += 1
            continue
        same = (match.group(2) or "").strip()
        chunk: list[str] = []
        if same:
            chunk.append(same)
        j = i + 1
        taken = 0
        while j < len(lines) and taken < 4:
            nxt = lines[j].strip()
            if not nxt:
                break
            if _ADDRESS_LABEL.match(lines[j]) or _IDENTITY_LABEL.match(lines[j]) or _NAME_LABEL.match(lines[j]):
                break
            if re.match(r"^[A-Z][A-Z\s/&]{8,}$", nxt) and len(nxt.split()) <= 6:
                break
            chunk.append(nxt)
            taken += 1
            j += 1
        blob = "\n".join(chunk).strip()
        if len(blob) >= 6:
            blobs.append(blob)
        i = max(j, i + 1)
    blobs.sort(key=len, reverse=True)
    return blobs


def _redact_labeled_values(text: str, notes: list[str]) -> str:
    count = 0

    def repl_identity(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        label = match.group(1)
        rest = (match.group(2) or "").strip()
        if not rest:
            return match.group(0)
        return f"{label}: [REDACTED]"

    out = _IDENTITY_LABEL.sub(repl_identity, text)
    out = _NAME_LABEL.sub("Applicant Name: [APPLICANT]", out)
    if count:
        notes.append(f"labeled identity fields: {count}")
    return out


def apply_identity_redactions(
    text: str,
    facts: ExtractedFacts,
    source: Path,
    harvest_from: str | None = None,
) -> tuple[str, list[str]]:
    """Replace contact/identity strings. Notes never include the raw values."""
    notes: list[str] = []
    source_text = harvest_from if harvest_from is not None else text
    out = text

    def sub(pattern: re.Pattern[str], label: str, replacement: str) -> None:
        nonlocal out
        found = pattern.findall(out)
        if found:
            out = pattern.sub(replacement, out)
            notes.append(f"{label}: {len(found)}")

    out = _redact_labeled_values(out, notes)

    for blob in _harvest_address_blobs(source_text):
        if blob and blob in out:
            out = out.replace(blob, "[ADDRESS]")
            notes.append("address block: 1")

    sub(_EMAIL, "emails", "[EMAIL]")
    sub(_PHONE, "phones", "[PHONE]")
    sub(_SSN, "ssn", "[SSN]")
    sub(_DOB_NUMERIC, "dates_like_dob", "[DATE]")
    sub(_DOB_WRITTEN, "written_dates", "[DATE]")
    sub(_AAMC, "aamc_id", "[AAMC_ID]")
    sub(_ERAS_ID, "applicant_ids", "[APPLICANT_ID]")
    sub(_FILENAME_ID, "file_id", "[APPLICANT_ID]")
    sub(_URL, "urls", "[URL]")
    sub(_STREET, "street_addresses", "[ADDRESS]")
    sub(_CITY_STATE_ZIP, "city_state_zip", "[ADDRESS]")
    sub(_PO_BOX, "po_boxes", "[ADDRESS]")
    sub(_ZIP_LINE, "zip_plus4", "[ADDRESS]")

    name_hits = 0
    for token in _name_tokens(facts, source, source_text):
        pattern = re.compile(rf"\b{re.escape(token)}\b", re.I)
        count = len(pattern.findall(out))
        if count:
            out = pattern.sub("[APPLICANT]", out)
            name_hits += count
    if name_hits:
        notes.append(f"applicant name tokens: {name_hits}")

    return out, notes


def redact_application_text(
    text: str,
    facts: ExtractedFacts,
    source: Path,
    harvest_from: str | None = None,
) -> tuple[str, list[str]]:
    out, notes = apply_identity_redactions(text, facts, source, harvest_from=harvest_from)
    header = (
        "The applicant is referred to only as [APPLICANT]. "
        "Home addresses, emails, phones, dates of birth, and applicant IDs "
        "have been removed. Do not guess a real name or contact details.\n\n"
    )
    return header + out, notes
