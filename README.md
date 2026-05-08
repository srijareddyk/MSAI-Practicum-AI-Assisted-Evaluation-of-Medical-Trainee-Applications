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

---

## Step 2: LLM scoring — `screen.py`

Step 2 uses a local Qwen3-32B model (via Ollama) to score the seven qualitative rubric dimensions that rule-based parsing cannot reliably handle.

### Rubric fields (step 2)

| Code | Dimension | Max |
|------|-----------|-----|
| SPE | Scientific Pursuits – Education/Experience | 4 |
| SPO | Scientific Pursuits – Output | 4 |
| PLE | Professional Leadership – Education | 2 |
| PLO | Professional Leadership – Output | 4 |
| SL | Social Leadership & Service | 4 |
| DT | Resilience / Grit / Distance Travelled | 4 |
| ELW | Endorsement by Letter Writers | 4 |

**Total step 2 score: 26 points.**

### How it works

Each dimension is scored by a separate, focused prompt. The model is instructed to extract facts only (no scoring language in the prompt), and scoring logic is applied in Python after the model returns structured JSON. This separation reduces hallucination on boundary cases.

`PLO` uses a four-call chain: three independent questions (for-profit business, large-scale public health program, technical product) followed by a self-reflection check. The final score depends on which combination triggers.

### Run on Quest

```bash
# Upload application text file
scp "Applicant_Name.txt" uam1146@quest.northwestern.edu:~/resume_screening/

# On Quest: set RESUME_PATH in screen.py, then submit
sed -i 's/RESUME_PATH = .*/RESUME_PATH = "Applicant_Name.txt"/' screen.py
sbatch run_ollama.sh
```

Results appear in `logs_<jobid>.out`.

### Known limitations

- The model occasionally includes excluded role types (tutoring, medical assistant, interpreter) in SPE research role extraction despite explicit exclusion rules in the prompt. SPE scores should be spot-checked against the raw JSON in the detailed output.
- DT (resilience) scores 0 when the personal statement does not make an explicit, specific argument. Generic phrases do not count by design, but this means strong candidates who undersell their challenges will be underscored.
- All data stays local — no applicant text is sent to any external API.

---

## Step 3: AI agent perspectives — `agents.py`

Step 3 runs two independent AI agents, each representing a distinct faculty reviewer perspective. The agents read the same application text and produce structured assessments that complement the numeric rubric scores from steps 1 and 2.

### Agent design

Both agents use Qwen3-32B via Ollama with a detailed system prompt encoding each reviewer's known evaluation philosophy. The prompts were derived from two recorded faculty meetings (April and May 2026) in which Dr. Pyatetsky and Dr. Mirza described their evaluation frameworks in their own words.

#### Dr. Pyatetsky agent

**Philosophy:** structured, data-driven, rubric-anchored.

Key behaviors:
- Classifies every applicant as `WORKHORSE`, `SUPERSTAR`, or `NOT_QUALIFIED`
- **WORKHORSE** (~75% of accepted residents): consistent high-level performance across all domains throughout the entire application, not just in one phase; broad achievements; evidence of resilience
- **SUPERSTAR** (~25%): genuinely exceptional in one specific domain (most commonly research output, occasionally entrepreneurial leadership); must still meet a minimum baseline everywhere else — no evidence of failure in other areas
- **NOT_QUALIFIED**: zeros across multiple bottom-category dimensions; filtered out without further review
- Reads the transcript grading legend before scoring Medical School Performance; applies the 2.25 default for P/F-only schools
- Flags letter quality mismatches (strong CV + weak letters = significant concern)
- Trajectory is a primary signal: declining trajectory is an explicit red flag; a setback followed by recovery is resilience, not a red flag

Output includes: classification, per-dimension scores with evidence, trajectory pattern, filter recommendation, and a one-sentence committee note.

#### Dr. Mirza agent

**Philosophy:** holistic, soft-skills-focused, compensatory.

Key behaviors:
- Does not classify into Workhorse/Superstar buckets; evaluates who the person is, not just what they have done
- Primary lens: **teamwork, communication, compassion, empathy** — looks for explicit signals in essays and letters, not inferred from activities alone
- School quality is a **threshold check, not a ranking tool**: a candidate excelling at a lesser-known school can equal or exceed a mediocre candidate from a top-25 school
- Reads letters for corroboration (two writers independently mentioning the same soft skill = strong signal) and notable absences (e.g., no letter from a research supervisor for a heavy research applicant)
- Trajectory patterns: upward (highly positive), flat (reliable), declining (red flag), burst-then-absent (needs explanation); an unrecovered decline is a red flag; a setback that was overcome is a resilience signal
- Volunteerism beyond the checklist is a positive signal

Output includes: per-soft-skill ratings with specific quotes, trajectory pattern with evidence, school quality compensatory notes, letter quality soft-skill mentions, character impression, rubric blind spots, and a gut-reaction sentence.

### Key differences between the two agents

| Dimension | Dr. Pyatetsky | Dr. Mirza |
|-----------|---------------|-----------|
| Framework | Workhorse / Superstar / Not Qualified | Holistic person assessment |
| Primary signal | Consistent performance + research output | Teamwork, empathy, compassion |
| School quality | Threshold (Top 25 = baseline cleared) | Compensatory (excelling at any school counts) |
| Letters | Level of praise (outstanding / strong / lukewarm) | Specific soft-skill mentions + corroboration |
| Trajectory | Declining = red flag; recovery = resilience | Same, plus burst-then-absent pattern |
| Filter logic | Zeros in multiple dimensions → filter out | Absence of all soft-skill signals → filter out |
| Output focus | Numeric scores + classification + committee note | Soft-skill ratings + character impression + gut reaction |

### Run on Quest

```bash
# Upload files (from local machine)
scp agents.py uam1146@quest.northwestern.edu:~/resume_screening/
scp "Applicant_Name.txt" uam1146@quest.northwestern.edu:~/resume_screening/

# On Quest: update RESUME_PATH, switch run script to agents.py, submit
sed -i 's/RESUME_PATH = .*/RESUME_PATH = "Applicant_Name.txt"/' agents.py
sed -i 's/screen.py/agents.py/g' run_ollama.sh
sbatch run_ollama.sh
squeue -u uam1146
```

Results appear in `logs_<jobid>.out`. The output prints a human-readable summary followed by the full JSON for both agents.

### Interpreting the output

- **Agreement:** if both agents give the same recommendation (A / B / C), the case is straightforward.
- **Conflict:** if the agents disagree, the case is flagged for human review. A common pattern is Pyatetsky recommending C (weak rubric scores) while Mirza recommends B (strong soft-skill signals not captured by the rubric).
- **filter_out:** if either agent sets `filter_out: true`, the applicant is flagged for exclusion. Both filter flags and the conflict note appear in the summary block at the top of the output.
- **rubric_blind_spots** (Mirza output): qualities the numeric rubric does not capture. Review this field for candidates near the interview cutoff.

### Adding a third agent (e.g., Dr. Fulbright)

The agent pattern is modular. To add a new perspective:

1. Define `FULBRIGHT_SYSTEM` and `FULBRIGHT_USER` strings following the same structure as the existing agents.
2. Add a `run_fulbright()` function that calls `call_agent(FULBRIGHT_SYSTEM, FULBRIGHT_USER.format(resume_text=resume_text))`.
3. Add the result to `run_both_agents()` and update the summary block.

The only hard requirement is that the system prompt specifies JSON-only output matching the expected schema.

### Project layout (updated)

- `screen.py` — step 2 LLM scoring (7 qualitative dimensions, Qwen3-32B)
- `agents.py` — step 3 agent perspectives (Dr. Pyatetsky + Dr. Mirza)
- `run_ollama.sh` — SLURM job script for Quest GPU nodes
