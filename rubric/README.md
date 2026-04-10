# Rubric Template (local only)

Place your private screening workbook template in this folder as:

- `rubric/template.xlsx`

This file should contain the worksheet layout used by the pipeline.

## Privacy

Do **not** commit real rubric workbooks with applicant/reviewer data.
This repository is configured to keep rubric Excel files out of git.

## Usage

If your template is named differently, pass it explicitly:

```bash
python -m application_analyzer.cli applications/*.pdf --template /absolute/path/to/your_template.xlsx -o step1_output.xlsx
```
