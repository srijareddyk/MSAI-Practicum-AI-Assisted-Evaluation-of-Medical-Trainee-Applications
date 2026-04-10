"""Normalize noisy PDF text (e.g. doubled glyphs from some generators)."""

from __future__ import annotations


def _line_doubling_score(line: str) -> float:
    if len(line) < 8:
        return 0.0
    pairs = sum(1 for i in range(0, len(line) - 1, 2) if line[i] == line[i + 1])
    return pairs * 2 / max(len(line), 1)


def normalize_pdf_line(line: str, threshold: float = 0.42) -> str:
    """
    If a line looks like every character was duplicated, collapse to single glyphs.
    Leaves normal transcript lines (including spaced-letter OCR) unchanged.
    """
    if _line_doubling_score(line) >= threshold:
        return "".join(line[i] for i in range(0, len(line), 2))
    return line


def normalize_pdf_text(text: str) -> str:
    return "\n".join(normalize_pdf_line(ln) for ln in text.splitlines())


def collapse_spaced_letters(line: str) -> str:
    """
    Turn 'C a s e   W e s t e r n' into 'Case Western' for keyword matching.
    Only applied when the line is mostly single letters separated by spaces.
    """
    if len(line) < 12:
        return line
    stripped = line.strip()
    if stripped.count(" ") < 8:
        return line
    parts = stripped.split()
    if not parts:
        return line
    if all(len(p) == 1 and p.isalpha() for p in parts[: min(len(parts), 40)]):
        return "".join(parts)
    return line
