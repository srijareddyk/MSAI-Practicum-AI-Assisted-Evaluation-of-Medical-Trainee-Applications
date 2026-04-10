# MSAI Practicum: AI-Assisted Evaluation of Medical Trainee Applications (Step 1)

This repository contains a Python pipeline for **step 1 rubric automation**. It reads ERAS-style application PDFs, extracts the five quantitative fields, and writes Excel worksheets that match the screening template.

This step uses **rule-based parsing only** (no LLM). Outputs are **draft scores** for faculty review and must be validated before use.

## Rubric fields (step 1)

| Field | Worksheet rows | Output |
|--------|----------------|--------|
| Medical School Quality | Top 25 vs otherwise | `4` or `0` |
| Medical School Performance | Honors / High Pass / Pass / P-F-only per rubric | `4`, `3`, `2`, `1`, `0`, or `2.25` |
| Undergraduate Quality | Top 25 vs otherwise | `2` or `0` |
| Undergraduate Performance | GPA bands | `4`–`0` |
| USMLE Step 1 | Passed first attempt vs not | `P` or `F` |

School lists are **configurable YAML** in `application_analyzer/config/school_lists.yaml`. Replace the placeholder Top 25 entries with your official lists.

The rubric’s **2.25** P/F-only medical school rule is **not** inferred from generic PDF text (that caused false positives). Optionally add substrings under `pass_fail_only_medical_school_keywords` for schools where your committee always applies that rule.

## Privacy and data handling (important)

- These PDFs contain **identifying education and test information**. Store them on **encrypted drives**, limit access to reviewers, and follow your institution’s **FERPA/HIPAA** policies.
- The tool writes **Excel summaries**; treat outputs like source PDFs. Do not commit real applicant PDFs or filled rubrics to public repositories.
- Logs: use `--json` for structured extraction details; redirect to a secure location if needed.
- This repo includes a `.gitignore` that excludes `applications/`, `rubric/`, PDFs, and generated XLSX output files by default.

## Setup

Requires Python 3.10+.

```bash
cd /path/to/MSAI-Practicum-AI-Assisted-Evaluation-of-Medical-Trainee-Applications
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Input files expected locally

To run the pipeline, your local workspace should contain:

- `applications/` with applicant PDF files (not tracked in git)
- `rubric/` with the screening workbook template (not tracked in git)

These are intentionally ignored by git for privacy.

## Run

**One applicant:**

```bash
python -m application_analyzer.cli path/to/Application.pdf \
  --template path/to/rubric_template.xlsx \
  -o output/step1_one_applicant.xlsx
```

**Batch (multiple PDFs → one workbook, one sheet per applicant):**

```bash
python -m application_analyzer.cli applications/*.pdf \
  -o output/step1_batch.xlsx
```

**Options:**

| Flag | Meaning |
|------|---------|
| `-o` / `--output` | Output `.xlsx` path |
| `--template` | Path to the screening Excel template (defaults to `rubric/template.xlsx` if present) |
| `--school-list` | Custom YAML with `medical_school_top25` and `undergraduate_top25` |
| `--json` | Print extraction/scoring details as JSON (for QA) |
| `--keep-template-sheets` | Keep original template worksheets in the output file (debugging) |

By default, **original template sheets are removed** from the output workbook so the file only contains newly generated applicant tabs.

## Excel formatting behavior (current)

- Only the **populated score cells** are highlighted in purple.
- No other cells are recolored.
- Populated purple cells:
  - `D14:D18` (five rubric rows)
  - `N8:R8` (summary band fields MSQ/MSP/UQ/UP/USMLE)

## Project layout

- `application_analyzer/pdf_extract.py` — PDF text extraction (`pypdf`)
- `application_analyzer/text_normalize.py` — light cleanup for odd glyph duplication
- `application_analyzer/facts.py` — regex heuristics for school names, GPA, USMLE Step 1
- `application_analyzer/scoring.py` — rubric mapping (clerkship parsing for Medical School Performance)
- `application_analyzer/excel_export.py` — copy template sheet, fill **only** the five score areas and the MSQ/MSP/UQ/UP/USMLE summary columns
- `application_analyzer/config/school_lists.yaml` — Top 25 lists (replace with your official lists)

## What to upload to GitHub

Commit and push:

- `application_analyzer/`
- `requirements.txt`
- `README.md`
- `.gitignore`

Do **not** commit/push:

- `applications/` (contains applicant data)
- `rubric/` (contains reviewer/applicant data)
- any `*.pdf` or `*.xlsx` outputs generated from real data
- local environment files (`.venv/`, caches)

## Limitations (step 1)

- **Layout variance:** Different schools format transcripts differently. Clerkship lines may wrap oddly; the parser merges common Internal Medicine wraps but may miss rare formats.
- **Medical School Performance:** Honors/High Pass detection depends on transcript wording (e.g., `H`, `COM`, `CCD`). Ambiguous cases need manual review.
- **P/F-only schools (`2.25`):** Only applied when the applicant’s extracted medical school matches a substring you list in `pass_fail_only_medical_school_keywords` in the YAML config.
- **USMLE Step 1:** Assumes ERAS-style examination blocks; nonstandard score reports may require manual entry.

Later phases (narrative summaries, pool characterization, optional AI) can build on the same module boundaries.
