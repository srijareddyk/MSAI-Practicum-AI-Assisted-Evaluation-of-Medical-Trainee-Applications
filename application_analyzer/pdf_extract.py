"""Extract plain text from application PDFs."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from application_analyzer.text_normalize import collapse_spaced_letters, normalize_pdf_text


def _collapse_adjacent_duplicate_lines(text: str) -> str:
    """
    Many ERAS PDFs repeat each label/value line. Keep a single copy when two
    consecutive stripped lines are identical.
    """
    lines = text.splitlines()
    out: list[str] = []
    prev_norm: str | None = None
    for ln in lines:
        n = ln.strip()
        if n and n == prev_norm:
            continue
        out.append(ln)
        prev_norm = n if n else prev_norm
    return "\n".join(out)


def extract_text_from_pdf(path: Path) -> str:
   
    reader = PdfReader(str(path))
    chunks: list[str] = []
    for page in reader.pages:
        raw = page.extract_text() or ""
        norm = normalize_pdf_text(raw)
        lines_out: list[str] = []
        for ln in norm.splitlines():
            lines_out.append(collapse_spaced_letters(ln))
        chunks.append("\n".join(lines_out))
    merged = "\n\n".join(chunks)
    return _collapse_adjacent_duplicate_lines(merged)
