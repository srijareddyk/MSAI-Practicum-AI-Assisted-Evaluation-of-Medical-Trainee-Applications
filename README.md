# MSAI Practicum: AI-Assisted Evaluation of Medical Trainee Applications

This repository processes ERAS-style ophthalmology residency applications in three stages:

1. **Step 1 (Python rules, no LLM)** — objective rubric fields from PDF text
2. **Factual briefing (1 LLM call)** — neutral extraction for reviewer agents
3. **Doc A & Doc B agents (2 LLM calls)** — independent AI screeners with separate prompts

All LLM inference runs **locally via Ollama** — no applicant data is sent to cloud APIs.

## Web UI

A Northwestern-branded frontend talks to a FastAPI backend that wraps the same pipeline as the CLI.

### Setup

Requires Python 3.10+, Node.js 18+, and [Ollama](https://ollama.com/) with your chosen model pulled locally (default: `qwen3:14b`).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen3:14b

cd frontend && npm install && cd ..
```

### Run (development)

Two terminals:

```bash
# Terminal 1 — API
source .venv/bin/activate
python -m uvicorn api.server:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — UI (proxies /api → :8000)
cd frontend && npm run dev
```

Or use the helper script:

```bash
source .venv/bin/activate
./scripts/dev.sh
```

Open **http://127.0.0.1:5173**

### Run (production-style)

```bash
cd frontend && npm run build && cd ..
source .venv/bin/activate
python -m uvicorn api.server:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000** (API serves the built UI).

### UI features

- Upload one or more ERAS PDFs
- Pipeline modes: Full (3 LLM calls), Briefing only, Step 1 only
- Progress while local models run
- Side-by-side Doc A / Doc B scores and rationales
- Download Excel workbook and Markdown artifacts

## CLI (unchanged)

```bash
source .venv/bin/activate
python -m llm_score.cli applications/*.pdf \
  --template rubric/template.xlsx \
  -o output/screening_scores.xlsx
```

| Flag | Meaning |
|------|---------|
| `--skip-llm` | Step-1 Excel only (0 model calls) |
| `--skip-agents` | Briefing only (1 model call); skip Doc A / Doc B |
| `--model` | Ollama model name |
| `--briefings-dir` | Markdown output directory |
| `--json` | Print full JSON to stdout |

## Where the prompts live

| Agent | File | Constant |
|-------|------|----------|
| Factual briefing | `llm_score/prompts.py` | `BRIEF_PROMPT` |
| Doc A (research-oriented reviewer) | `llm_score/prompts.py` | `DOC_A_PROMPT` |
| Doc B (clinical/leadership-oriented reviewer) | `llm_score/prompts.py` | `DOC_B_PROMPT` |

## Privacy and data handling

- PDFs contain identifying education and test information. Store on encrypted drives and follow institutional FERPA/HIPAA policies.
- Do not commit real applicant PDFs, filled rubrics, or briefings to public repositories.
- Uploaded files for the web UI are stored under `api_data/` (gitignored).

## Project layout

```
frontend/             Northwestern-branded React UI (Vite)
api/                  FastAPI server + shared pipeline runner
llm_score/            LLM briefing + Doc A / Doc B agents
application_analyzer/ Step-1 Python rules + Excel export
rubric/template.xlsx  Screening workbook template
```

## Limitations

- Agent scores are drafts for faculty validation — not final decisions.
- Score quality depends on the local model and PDF text extraction.
- Doc A and Doc B may disagree by design (independent reviewers).
