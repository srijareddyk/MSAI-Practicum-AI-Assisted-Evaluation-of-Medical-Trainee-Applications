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

The rubric's **2.25** P/F-only medical school rule is **not** inferred from generic PDF text (that caused false positives). Optionally add substrings under `pass_fail_only_medical_school_keywords` for schools where your committee always applies that rule.

## Privacy and data handling (important)

- These PDFs contain **identifying education and test information**. Store them on **encrypted drives**, limit access to reviewers, and follow your institution's **FERPA/HIPAA** policies.
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
- **P/F-only schools (`2.25`):** Only applied when the applicant's extracted medical school matches a substring you list in `pass_fail_only_medical_school_keywords` in the YAML config.
- **USMLE Step 1:** Assumes ERAS-style examination blocks; nonstandard score reports may require manual entry.

Later phases (narrative summaries, pool characterization, optional AI) can build on the same module boundaries.

---

## Steps 2 & 3: Integrated pipeline — `pipeline.py`

`pipeline.py` combines LLM scoring (step 2) and AI agent evaluation (step 3) into a single end-to-end run. It takes a plain-text application file as input and produces a full structured JSON output covering all three layers.

### Architecture overview

```
Layer 1 (Python rules)     →  MSQ, MSP, UQ, UP, USMLE
Layer 2 (LLM + Python)     →  SPE, SPO, PLE, PLO, SL, DT, ELW
Layer 3 (AI agents)        →  Dr. Pyatetsky + Dr. Mirza → A/B/C recommendation
```

Each layer feeds into the next. Layer 3 agents receive the numeric scores from layers 1 and 2 as input — they do not re-score the rubric dimensions.

### Layer 1: Python rule-based scoring

LLM extracts raw facts (school names, GPA, USMLE result, clinical rotation grades), then Python applies deterministic scoring rules. No judgment involved.

| Dimension | Rule |
|-----------|------|
| MSQ | Top 25 medical school → 4, otherwise 0 |
| MSP | Honors count in clinical rotations → 4/3/2/1/0; P/F-only school → 2.25 |
| UQ | Top 25 undergrad → 2, otherwise 0 |
| UP | GPA ≥ 3.8 → 4, ≥ 3.5 → 3, ≥ 3.25 → 2, ≥ 3.0 → 1, < 3.0 → 0 |
| USMLE | Passed first attempt → P, otherwise F |

### Layer 2: LLM fact extraction + Python scoring

Each of the 7 qualitative dimensions is scored by a separate focused prompt. The model extracts facts only — scoring logic is applied in Python after the model returns structured JSON.

| Code | Dimension | Max |
|------|-----------|-----|
| SPE | Scientific Pursuits – Education/Experience | 4 |
| SPO | Scientific Pursuits – Output | 4 |
| PLE | Professional Leadership – Education | 2 |
| PLO | Professional Leadership – Output | 4 |
| SL | Social Leadership & Service | 4 |
| DT | Resilience / Grit / Distance Travelled | 4 |
| ELW | Endorsement by Letter Writers | 4 |

**Layer 2 total: 26 points.**

`PLO` uses a four-call chain: three independent questions (for-profit business, large-scale public health program, technical product) followed by a self-reflection check.

### Layer 3: AI agent perspectives

Two agents each run in two steps:

**Step A** — each agent reads the raw application text and extracts the signals it specifically cares about (subjective evidence, not re-scoring).

**Step B** — each agent receives the layer 1 + 2 numeric scores alongside its step A signals and produces a final A/B/C recommendation with rationale.

#### Dr. Pyatetsky agent

**Philosophy:** structured, data-driven, rubric-anchored.

Step A extracts: trajectory pattern (upward/flat/declining), superstar signals (research excellence or entrepreneurial impact), workhorse signals (consistent broad achievement), red flags, letter quality.

Step B judgment rules:
- **WORKHORSE**: consistent high-level performance across all dimensions throughout; broad achievements; resilience evidence. ~75% of accepted residents.
- **SUPERSTAR**: genuinely exceptional in one domain AND meets minimum baseline everywhere else. ~25% of accepted residents.
- **NOT_QUALIFIED**: multiple zeros in bottom-category dimensions. Filtered out.
- **A**: SUPERSTAR, or combined score ≥ 28 with no red flags
- **B**: WORKHORSE with combined score ≥ 20, or strong in 2+ dimensions
- **C**: NOT_QUALIFIED, multiple red flags, or combined score < 15

#### Dr. Mirza agent

**Philosophy:** holistic, soft-skills-focused, compensatory.

Step A extracts: teamwork signals, empathy/compassion signals, communication quality, trajectory, letter soft-skill mentions (corroboration across writers), school context, volunteerism beyond checklist.

Step B judgment rules:
- **A**: strong soft-skill signals + solid scores, or exceptional upward trajectory compensating for weaker scores
- **B**: adequate soft-skill signals + decent scores, or strong scores but soft-skills unclear
- **C**: absent soft-skill signals, unrecovered decline, or multiple red flags

School quality is a threshold check, not a ranking tool. A candidate excelling at a lesser-known school can equal or exceed a mediocre candidate from a top-25 school.

#### Key differences between the two agents

| Dimension | Dr. Pyatetsky | Dr. Mirza |
|-----------|---------------|-----------|
| Framework | Workhorse / Superstar / Not Qualified | Holistic person assessment |
| Primary signal | Consistent performance + research output | Teamwork, empathy, compassion |
| School quality | Threshold (Top 25 = baseline cleared) | Compensatory (excelling at any school counts) |
| Letters | Level of praise | Specific soft-skill mentions + corroboration across writers |
| Trajectory | Declining = red flag; recovery = resilience | Same, plus burst-then-absent pattern |
| Filter logic | Zeros in multiple dimensions | Absence of all soft-skill signals |

### Run on Quest

```bash
# Upload files (from local machine)
scp pipeline.py uam1146@quest.northwestern.edu:~/resume_screening/
scp "Applicant_Name.txt" uam1146@quest.northwestern.edu:~/resume_screening/

# On Quest: update RESUME_PATH, switch run script, submit
sed -i 's/RESUME_PATH = .*/RESUME_PATH = "Applicant_Name.txt"/' pipeline.py
sed -i 's/screen\.py\|agents\.py/pipeline.py/g' run_ollama.sh
sbatch run_ollama.sh
squeue -u uam1146
```

Results appear in `logs_<jobid>.out`.

### Interpreting the output

The output prints a human-readable summary block followed by full JSON. Key fields to check:

- **combined_score**: layer 1 numeric + layer 2 LLM total
- **agreement**: whether both agents gave the same A/B/C — if false, flag for human review
- **conflict_note**: filled when agents disagree, e.g. Pyatetsky=C (weak scores) vs Mirza=B (strong soft-skill signals not captured by rubric)
- **either_filter_out**: true if either agent recommends filtering the applicant
- **rubric_blind_spots** (Mirza output): qualities the numeric rubric does not capture — review for candidates near the interview cutoff

### Known limitations

- Layer 1 MSP scoring relies on LLM extraction of rotation grades; unusual transcript formats may produce extraction errors. Spot-check the `rotation_grades` field in JSON output.
- Layer 2 SPE occasionally includes excluded role types (tutoring, scribing, interpreting) despite explicit exclusion rules. Spot-check `roles` in SPE output.
- Layer 2 DT scores 0 when the personal statement does not make an explicit, specific resilience argument. Strong candidates who undersell their challenges will be underscored here.
- Layer 3 A/B/C thresholds (combined score ≥ 28 for A, ≥ 20 for B, etc.) are initial calibration values and should be adjusted after reviewing results against faculty ground-truth scores.
- All data stays local — no applicant text is sent to any external API.

### Adding a third agent (e.g., Dr. Fulbright)

The agent pattern is modular. To add a new perspective:

1. Define `FULBRIGHT_EXTRACT_SYSTEM`, `FULBRIGHT_EXTRACT_USER`, `FULBRIGHT_JUDGE_SYSTEM`, `FULBRIGHT_JUDGE_USER` following the same structure as the existing agents.
2. Add a `run_fulbright(resume_text, layer1, layer2)` function with the same two-step pattern.
3. Call it in `__main__` alongside `run_pyatetsky` and `run_mirza`, and add its result to the final JSON output.

### Project layout (updated)

- `application_analyzer/` — step 1 PDF extraction and rule-based scoring
- `pipeline.py` — steps 2 and 3: LLM scoring + agent evaluation (single integrated run)
- `run_ollama.sh` — SLURM job script for Quest GPU nodes
