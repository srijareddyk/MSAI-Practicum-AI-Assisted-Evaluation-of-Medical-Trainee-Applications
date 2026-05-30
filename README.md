# MSAI Practicum: AI-Assisted Evaluation of Medical Trainee Applications

This repository processes ERAS-style ophthalmology residency applications in three stages:

1. **Step 1 (Python rules, no LLM)** — objective rubric fields from PDF text
2. **Factual briefing (1 LLM call)** — neutral extraction for reviewer agents
3. **Doc A & Doc B agents (2 LLM calls)** — independent AI screeners with separate prompts

All LLM inference runs **locally via Ollama** — no applicant data is sent to cloud APIs.

## Where the prompts live

| Agent | File | Constant |
|-------|------|----------|
| Factual briefing | `llm_score/prompts.py` | `BRIEF_PROMPT` |
| Doc A (research-oriented reviewer) | `llm_score/prompts.py` | `DOC_A_PROMPT` |
| Doc B (clinical/leadership-oriented reviewer) | `llm_score/prompts.py` | `DOC_B_PROMPT` |

Implementation: `llm_score/brief.py`, `llm_score/reviewers.py`, shared Ollama client in `llm_score/llm_client.py`.

## Rubric fields — step 1 (automated)

| Field | Worksheet row | Output |
|--------|----------------|--------|
| Medical School Quality | 14 | `4` or `0` |
| Medical School Performance | 15 | `4`, `3`, `2`, `1`, `0`, or `2.25` |
| Undergraduate Quality | 16 | `2` or `0` |
| Undergraduate Performance | 17 | `4`–`0` |
| USMLE Step 1 | 18 | `P` or `F` |

Python rule scores pre-fill **both** Doc A (column D) and Doc B (column E), purple highlight.

## Rubric fields — Doc A & Doc B agents (rows 5–12)

Each agent independently scores subjective rows and writes to its Excel column:

| Column | Agent | Prompt |
|--------|-------|--------|
| D | Doc A | `DOC_A_PROMPT` — research/publications/letters focus |
| E | Doc B | `DOC_B_PROMPT` — leadership/service/resilience focus |

Agent scores use a blue highlight. Each agent also produces a Markdown review (`*_doc_a.md`, `*_doc_b.md`).

## Privacy and data handling

- PDFs contain identifying education and test information. Store on encrypted drives and follow institutional FERPA/HIPAA policies.
- Do not commit real applicant PDFs, filled rubrics, or briefings to public repositories.

## Setup

Requires Python 3.10+ and [Ollama](https://ollama.com/) with your chosen model pulled locally (default: `qwen3:14b`).

```bash
pip install -r requirements.txt
ollama pull qwen3:14b
```

## Run — full pipeline

```bash
python -m llm_score.cli applications/*.pdf \
  --template rubric/template.xlsx \
  -o output/screening_scores.xlsx
```

Outputs per applicant in `output/briefings/`:

- `{Applicant}_brief.md` — factual extraction (no scores)
- `{Applicant}_doc_a.md` — Doc A summary + scores + rationale
- `{Applicant}_doc_b.md` — Doc B summary + scores + rationale

**Options:**

| Flag | Meaning |
|------|---------|
| `--skip-llm` | Step-1 Excel only (0 model calls) |
| `--skip-agents` | Briefing only (1 model call); skip Doc A / Doc B |
| `--model` | Ollama model name |
| `--briefings-dir` | Markdown output directory |
| `--json` | Print full JSON to stdout |

## Model calls per applicant

| Command | Calls |
|---------|-------|
| `application_analyzer.cli` | **0** |
| `llm_score.cli --skip-agents` | **1** (briefing) |
| `llm_score.cli` (default) | **3** (briefing + Doc A + Doc B) |

## Project layout

```
llm_score/
  prompts.py          ← all LLM prompts (BRIEF, DOC_A, DOC_B)
  llm_client.py       Ollama JSON helper
  brief.py            factual extraction
  reviewers.py        Doc A / Doc B agents
  markdown_export.py  Markdown renderers
  text_strip.py       boilerplate removal
  cli.py              pipeline entry point
application_analyzer/ step-1 Python rules + Excel export
```

## Limitations

- Agent scores are drafts for faculty validation — not final decisions.
- Score quality depends on the local model and PDF text extraction.
- Doc A and Doc B may disagree by design (independent reviewers).
