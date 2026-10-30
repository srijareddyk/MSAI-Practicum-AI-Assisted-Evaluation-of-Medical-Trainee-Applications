# Rubric Template (local only)

Place your private screening workbook template in this folder as:

- `rubric/template.xlsx`

The pipeline writes **Doc A** (column D) and **Doc B** (column E) score columns. Step-1 automated scores pre-fill rows 14–18 in both columns; rows 5–12 stay blank for faculty.

Markdown reviewer briefings and agent reviews (from `python -m llm_score.cli`) are written to `briefings/`:

- `{Applicant}_brief.md` — factual extraction
- `{Applicant}_doc_a.md` / `{Applicant}_doc_b.md` — agent reviews

Prompts for all three LLM steps are in `llm_score/prompts.py`.

## Privacy

Do **not** commit real rubric workbooks with applicant/reviewer data.

## Usage

```bash
python -m llm_score.cli applications/*.pdf --template rubric/template.xlsx -o output/screening_scores.xlsx
```

Step 1 only (no LLM):

```bash
python -m application_analyzer.cli applications/*.pdf --template rubric/template.xlsx -o output/step1_scores.xlsx
```
