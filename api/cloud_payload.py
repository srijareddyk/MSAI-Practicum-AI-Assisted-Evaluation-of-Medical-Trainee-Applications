"""Build the exact text that would be sent to Azure — no LLM call."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from application_analyzer.facts import extract_facts_from_text
from application_analyzer.pdf_extract import extract_text_from_pdf
from llm_score.redact import redact_application_text
from llm_score.text_strip import strip_for_llm

_PLACEHOLDERS = (
    "[APPLICANT]",
    "[EMAIL]",
    "[PHONE]",
    "[ADDRESS]",
    "[DATE]",
    "[SSN]",
    "[URL]",
    "[AAMC_ID]",
    "[APPLICANT_ID]",
    "[REDACTED]",
)


def placeholder_counts(text: str) -> dict[str, int]:
    return {tag: text.count(tag) for tag in _PLACEHOLDERS if text.count(tag)}


def cloud_payload_from_pdf(pdf: Path) -> dict[str, Any]:
    text = extract_text_from_pdf(pdf)
    facts = extract_facts_from_text(text, pdf)
    stripped = strip_for_llm(text)
    redacted, notes = redact_application_text(stripped, facts, pdf, harvest_from=text)
    return {
        "file": pdf.name,
        "kept_on_this_computer": {
            "applicant_name": facts.applicant_name,
            "source_chars": len(text),
            "stripped_chars": len(stripped),
        },
        "sent_to_azure": redacted,
        "azure_chars": len(redacted),
        "redaction_notes": notes,
        "placeholder_counts": placeholder_counts(redacted),
    }
