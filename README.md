# MSAI Practicum: AI-Assisted Screening of MSAI Master's Applications

Local admissions review for Northwestern's **Master of Science in Artificial Intelligence**. A factual brief, then three readers: technical readiness, program fit, and academic record. Scores are drafts for faculty. They are not interview decisions.

## Benchmark — 28 October 2026

Twelve fictional packets, scored on this laptop with **qwen3:8b** (Ollama, Q4, thinking off) on an RTX 5060 Laptop GPU. The run took **9 minutes 35 seconds**. No call failed. Institution and cumulative GPA were read from every PDF.

**Pass** means a majority invite to interview (A). **Fail** means a majority do-not-advance (C). **Review** means a majority B: the committee should look, and the model is not willing to invite or reject.

| Outcome | Model | Written as |
| --- | ---: | ---: |
| Pass — interview (A) | 1 | 4 |
| Review — look again (B) | 10 | 4 |
| Fail — do not advance (C) | 1 | 4 |
| Exact match to the written band | 6 of 12 |  |
| Off by two bands | 0 |  |

The readers bunch in the middle. They invited only Avery Chen, and they rejected only Harper Singh. The other ten packets, including three that were written as clear invites and three that were written as clear rejections, received a majority B. No invite was rejected, and no rejection was invited.

The two packets written so the technical reader and the fit reader would disagree (Jordan Hale, Sam Okonkwo) did not disagree. The only disagreement was Quinn Alvarez: Reviewer A said C, and Reviewers B and C said B.

| Packet | Intended | A | B | C | Majority | Match | What the packet was built to show |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [Avery Chen](eval/packets/01_avery_chen.txt) | A | A | A | A | A | yes | Research, first-author workshop paper, specific plan, detailed letters |
| [Priya Shah](eval/packets/02_priya_shah.txt) | A | B | B | B | B | no | Shipped ranker, quantitative degree, no paper |
| [Marcus Hale](eval/packets/03_marcus_hale.txt) | A | B | B | B | B | no | Open-source solvers and a mathematics degree, no lab appointment |
| [Elena Vasquez](eval/packets/04_elena_vasquez.txt) | A | B | B | B | B | no | Second-author robotics paper with a stated individual part |
| [Jordan Hale](eval/packets/05_jordan_hale.txt) | B | B | B | B | B | yes | Strong demo and letters, generic statement |
| [Sam Okonkwo](eval/packets/06_sam_okonkwo.txt) | B | B | B | B | B | yes | Specific public-data statement, thin technical record |
| [Riley Nguyen](eval/packets/07_riley_nguyen.txt) | B | B | B | B | B | yes | Honest capstone, no paper |
| [Taylor Brooks](eval/packets/08_taylor_brooks.txt) | B | B | B | B | B | yes | One internship notebook and a collegial second letter |
| [Casey Morgan](eval/packets/09_casey_morgan.txt) | C | B | B | B | B | no | Tutorial projects, vague statement, generic letters |
| [Drew Patel](eval/packets/10_drew_patel.txt) | C | B | B | B | B | no | High biology grades, almost no computing |
| [Quinn Alvarez](eval/packets/11_quinn_alvarez.txt) | C | C | B | B | B | no | Short lab visit, 2.95 GPA, letters that mention missed deadlines |
| [Harper Singh](eval/packets/12_harper_singh.txt) | C | C | C | C | C | yes | Communications degree, online quiz certificate, non-technical letters |

Full machine output, including each summary, is in [`eval/benchmark_results.json`](eval/benchmark_results.json). Regenerate with:

```bash
python eval/make_packets.py
python eval/run_benchmark.py qwen3:8b
```

The twelve packet texts are also copied at the bottom of this file.

## How a packet is read

1. **Record (no model)** — prior institution and cumulative GPA, when the PDF text includes them
2. **Factual brief (1 model call)** — extraction only, no score
3. **Three readers (3 model calls)** — Reviewer A (technical readiness), Reviewer B (program fit), Reviewer C (academic record)

All model calls run **locally via Ollama**. Applicant text is not sent to a cloud API.

Reviewer A, B, and C use the same score scale and different emphasis. A majority A is an interview suggestion. A majority C is a suggestion not to advance. Faculty still decide.

## MSAI narrative rubric

| Field | What it now means |
|-------|-------------------|
| Technical preparation | Research or engineering time beyond coursework |
| Research and project output | Papers and substantial technical artifacts |
| Formal quantitative preparation | CS, math, statistics, or an explicit ML course sequence |
| Technical leadership | Led a product, research effort, or team |
| Collaboration and service | Teaching, mentoring, organizations |
| Statement and trajectory | Specific case for this MSAI program |
| Letters | Specific technical endorsement |
| Recommendation | A interview / B consider / C do not interview |

JSON keys in `llm_score/prompts.py` are unchanged so the API and Excel workbook keep working. The prompt text is the MSAI meaning.

Step 1 still understands older ERAS-style blocks (medical school, clerkship grades, USMLE) when that text is present. Those signals stay blank on a typical master's packet.

## Web UI

The frontend is the admissions review screen. It talks to a FastAPI backend that wraps the same pipeline as the CLI.

## Privacy and data handling (important)

- These PDFs contain **identifying education records**. Store them on **encrypted drives**, limit access to reviewers, and follow your institution's **FERPA** policies.
- The tool writes **Excel summaries**; treat outputs like source PDFs. Do not commit real applicant PDFs or filled rubrics to public repositories.
- Logs: use `--json` for structured extraction details; redirect to a secure location if needed.
- Real applicant PDFs, filled rubrics, and benchmark run folders (`eval/runs/`) stay out of git. The twelve files in `eval/packets/` are fictional test packets and are meant to be committed.

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen3:8b

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

- Upload one or more application PDFs (statement of purpose, CV, projects, letters)
- Pipeline modes: full review, briefing only, rule-based signals only
- Progress while local models run
- Side-by-side Reviewer A / Reviewer B scores, plus a flag when they disagree
- Download Excel workbook, Markdown artifacts, and a print-to-PDF report

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
| `--skip-agents` | Briefing only (1 model call); skip the three readers |
| `--model` | Ollama model name |
| `--briefings-dir` | Markdown output directory |
| `--json` | Print full JSON to stdout |

## Where the prompts live

| Agent | File | Constant |
|-------|------|----------|
| Factual briefing | `llm_score/prompts.py` | `BRIEF_PROMPT` |
| Reviewer A (technical readiness) | `llm_score/prompts.py` | `DOC_A_PROMPT` |
| Reviewer B (program fit) | `llm_score/prompts.py` | `DOC_B_PROMPT` |
| Reviewer C (academic record) | `llm_score/prompts.py` | `DOC_C_PROMPT` |

## Privacy and data handling

- PDFs contain identifying education records. Store on encrypted drives and follow institutional FERPA policies.
- Do not commit real applicant PDFs, filled rubrics, or briefings to public repositories.
- Uploaded files for the web UI are stored under `api_data/` (gitignored).

## Project layout

```
frontend/             MSAI admissions desk (Vite + React)
api/                  FastAPI server + shared pipeline runner
llm_score/            LLM briefing + Reviewer A / Reviewer B
application_analyzer/ Step-1 Python rules + Excel export
rubric/template.xlsx  Screening workbook template
```

- **Layout variance:** Different schools format transcripts differently. Clerkship lines may wrap oddly; the parser merges common Internal Medicine wraps but may miss rare formats.
- **Medical School Performance:** Honors/High Pass detection depends on transcript wording (e.g., `H`, `COM`, `CCD`). Ambiguous cases need manual review.
- **P/F-only schools (`2.25`):** Only applied when the applicant's extracted medical school matches a substring you list in `pass_fail_only_medical_school_keywords` in the YAML config.
- **USMLE Step 1:** Assumes ERAS-style examination blocks; nonstandard score reports may require manual entry.

---

## Earlier residency prototype

The notes below describe an older ophthalmology residency pipeline kept in this repo for reference. The web UI and `llm_score/prompts.py` now screen **MSAI master's** packets. Do not use the residency rubric for master's files.

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

## Packet texts

These are the fictional files scored in the benchmark. The same text is stored under `eval/packets/`.

<details>
<summary><code>01_avery_chen.txt</code></summary>

```text
FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: Avery Chen

STATEMENT OF PURPOSE

I am applying to the Master of Science in Artificial Intelligence at Northwestern because I want to train retrieval systems that clinicians can actually query. For two years I was a research assistant in a clinical natural language processing group. I built the indexing pipeline for a set of de-identified discharge summaries, and I was first author on a workshop paper about that indexer.

The paper, "Sparse Plus Dense Retrieval for Discharge Summaries," appeared in the proceedings of the Upper Midwest NLP Workshop in 2025. I designed the experiment, wrote the retrieval code, and ran the error analysis. The useful result was not a leaderboard number. Dense retrieval missed negation. A hybrid index recovered those cases, and I wrote that up with the counts.

At Northwestern I want the systems and language courses in MSAI, then a project on retrieval for notes where the label is a clinical concept rather than a web query. I have the linear algebra, probability, algorithms, and machine learning sequence from Michigan, and I have already maintained the code other students in the lab ran. I am not looking for a general tour of artificial intelligence. I want a year in which the coursework and a faculty project are the same problem.

EDUCATION

Undergraduate institution: University of Michigan
Degree: B.S. Computer Science, 2025
Cumulative GPA: 3.86

RESEARCH

Research assistant, University of Michigan, September 2023 to May 2025, about 15 hours a week during term and full time in summer 2024. Built a hybrid retrieval index over 80,000 de-identified discharge summaries. First-author workshop paper, Upper Midwest NLP Workshop, 2025. I wrote the code, the experiments, and the first draft.

PROJECTS

Discharge-summary retriever. Python, FAISS, and a small BM25 index. Other students in the lab used the repository for their own error analysis. I reviewed their pull requests.

WORK EXPERIENCE

Undergraduate research assistant, clinical NLP group, University of Michigan, 2023-2025. Teaching assistant for EECS 445, Introduction to Machine Learning, winter 2025, two discussion sections.

HONORS AND AWARDS

EECS 445 teaching award, departmental nominee, 2025. University Honors, 2023-2025.

LETTERS OF RECOMMENDATION

Letter 1. Professor Helen Park, University of Michigan. "Avery is the student I trust with the lab repository. The workshop paper is Avery's experiment, not a footnote on mine. I would fund this student in a PhD program. The retrieval work is careful, and the error analysis is the part I send to new students."

Letter 2. Dr. Omar Shah, University of Michigan. "I co-taught the machine learning course Avery assisted. Avery could explain a confusion matrix to a student who was lost, and then go back and fix a leaking index in the lab. I recommend Avery without reservation for a technical master's program."
```

</details>

<details>
<summary><code>02_priya_shah.txt</code></summary>

```text
FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: Priya Shah

STATEMENT OF PURPOSE

I am applying to Northwestern's MSAI program to move from shipping ranking models to understanding when those models fail. At an internship with a retail search team I owned the feature pipeline for a learning-to-rank model. The model went to production for a category page. I also wrote the note that said we should not launch a second page because the offline gain did not survive a holdout week.

That note is the work I want more of. I can implement a ranker. I am less sure how to design the evaluation when the click log is biased. MSAI's machine learning systems and evaluation courses are the reason I am applying here rather than to a general computer science master's. I want a year of coursework in probabilistic modeling and a project on offline evaluation, then a role building models whose failures I can explain.

My record is a computer engineering degree with linear algebra, probability, algorithms, and two machine learning courses, plus the production system above. I am applying because the production work showed me the questions I cannot answer from an internship alone.

EDUCATION

Undergraduate institution: University of Illinois Urbana-Champaign
Degree: B.S. Computer Engineering, 2024
Cumulative GPA: 3.91

RESEARCH

No university laboratory appointment. The technical research in this packet is the internship evaluation study below, which I wrote up internally. I did not publish it.

PROJECTS

Category-page ranker, summer 2024, retail search internship. I trained a LightGBM ranker, built the daily feature job, and compared it with the previous heuristic on a one-week holdout. The first page shipped. I recommended against shipping the second page. The repository is internal. My mentor can describe the design.

WORK EXPERIENCE

Machine learning engineering intern, Northline Retail, Champaign, May 2024 to August 2024. Course assistant for ECE 374, Algorithms, spring 2024.

HONORS AND AWARDS

James Scholar, University of Illinois, 2022-2024. Dean's list each semester.

LETTERS OF RECOMMENDATION

Letter 1. Maya Krishnan, staff engineer, Northline Retail. "Priya owned the ranker that we shipped. More important, Priya is the intern who told us not to ship the second page. The memo was specific, with the holdout numbers, and it was right. I would hire Priya back as an engineer."

Letter 2. Professor David Lang, University of Illinois. "Priya was among the strongest students in my algorithms course and then assisted it. The homework solutions were correct, and the explanations in office hours were precise. I recommend Priya for a technical graduate program."
```

</details>

<details>
<summary><code>03_marcus_hale.txt</code></summary>

```text
FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: Marcus Hale

STATEMENT OF PURPOSE

I am applying to the MSAI program to study optimization for models that do not fit on one machine. I maintain an open-source library, SmallBatch, that implements a few stochastic solvers for people who want a readable PyTorch training loop rather than a framework. About forty GitHub accounts have starred it, and I have merged patches from six outside contributors. The users are students. I do not want to overstate that.

The mathematics degree is the other half. I have had linear algebra, real analysis, probability, numerical methods, and a graduate-level convex optimization course as an undergraduate. What I do not have is a lab appointment or a paper. The library is the technical artifact. Northwestern is the program I want because the MSAI curriculum pairs the optimization coursework with systems, which is the gap between my solvers and a model someone else can train.

I hope to spend the year on distributed training and a project that turns one of the SmallBatch solvers into something a course staff could assign. I am applying for that sequence, not for a general credential.

EDUCATION

Undergraduate institution: University of Wisconsin-Madison
Degree: B.S. Mathematics and Computer Sciences, 2025
Cumulative GPA: 3.74

RESEARCH

No formal research appointment. Independent work on SmallBatch, described under projects, from June 2024 to the present.

PROJECTS

SmallBatch, an open-source PyTorch training library. I wrote the solvers, the tests, and the documentation. Six outside contributors have merged patches. The issue tracker shows students using it for class projects. Repository: a public GitHub project under my name, started June 2024.

WORK EXPERIENCE

Tutor, Madison Mathematics Learning Center, September 2023 to May 2025, eight hours a week. I ran drop-in hours for linear algebra.

HONORS AND AWARDS

Van Vleck scholarship for mathematics, 2024. Dean's list, four semesters.

LETTERS OF RECOMMENDATION

Letter 1. Professor Ruth Adler, University of Wisconsin. "Marcus took my convex optimization course and then built a library whose solvers match the algorithms in the course. I have read the documentation. It is accurate. Marcus is ready for graduate coursework in optimization, and I recommend him strongly."

Letter 2. Professor Ian Brooks, University of Wisconsin. "I supervised Marcus only as an instructor in numerical methods, not as a research advisor. Within that scope, the work was excellent. He is the student other students asked for by name in the tutoring center. I recommend him for MSAI."
```

</details>

<details>
<summary><code>04_elena_vasquez.txt</code></summary>

```text
FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: Elena Vasquez

STATEMENT OF PURPOSE

I am applying to Northwestern MSAI to work on perception for robots that share a room with people, not on benchmark vision. In the Purdue cooperative robotics lab I was the second author on a conference paper about a gripper that uses a wrist camera. My part was the data split and the calibration code. The first author designed the policy. I can say exactly what I did not do.

I also taught a lab section of a signals course for a year. The students who struggled were usually missing linear algebra, and I started writing short notes for them. That is the teaching I want to keep doing in graduate school.

MSAI is the program I am applying to because I need the vision and learning courses next to a robotics faculty project. My plan for the year is those courses and a project on calibration under bad lighting, which is the failure mode in our paper. I have probability, linear algebra, signals, and a machine learning elective. I am applying with a specific experiment in mind.

EDUCATION

Undergraduate institution: Purdue University
Degree: B.S. Electrical Engineering, 2025
Cumulative GPA: 3.82

RESEARCH

Undergraduate researcher, Purdue cooperative robotics lab, January 2024 to May 2025. Second author: "Wrist-Camera Grasping Under Partial Occlusion," Great Lakes Robotics Meeting, 2025. I wrote the calibration code and constructed the train and test split. I did not design the policy.

PROJECTS

Calibration toolkit for the lab's wrist camera. Python and OpenCV. The current students still use the split script I wrote. It is in the lab repository, not a public project.

WORK EXPERIENCE

Laboratory teaching assistant, ECE 301 signals and systems, fall 2024 and spring 2025.

HONORS AND AWARDS

Purdue College of Engineering undergraduate research stipend, summer 2024.

LETTERS OF RECOMMENDATION

Letter 1. Professor Nina Cole, Purdue University. "Elena is the second author for a reason I can defend. She built the split that made the paper's claim measurable, and she refused to let us average away the lighting failures. I recommend her for a research master's without reservation."

Letter 2. Dr. Paul Ortega, Purdue University. "Elena taught my signals lab. Students improved, and Elena could tell me which problem set item caused it. She is organized, precise, and ready for graduate coursework. I recommend her strongly."
```

</details>

<details>
<summary><code>05_jordan_hale.txt</code></summary>

```text
FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: Jordan Hale

STATEMENT OF PURPOSE

I have always been passionate about artificial intelligence and I believe Northwestern is one of the best places in the world to study it. Ever since my first programming class I knew I wanted a career in AI. The MSAI program would help me achieve my dreams and become a leader in the field. I am a hard worker and a team player, and I love to learn new things. Northwestern's reputation and the city of Chicago are also very exciting to me.

In the future I hope to work at a top company or maybe start my own company. A master's degree from Northwestern would open those doors. I am eager to take whatever courses the program recommends and to meet other talented students. Thank you for considering my application. I would be honored to join the incoming class and contribute to the Northwestern community.

EDUCATION

Undergraduate institution: University of Michigan
Degree: B.S. Computer Science, 2025
Cumulative GPA: 3.78

RESEARCH

Research assistant, University of Michigan information retrieval group, May 2024 to April 2025. I built a retrieval demo that the lab still runs for visitors.

PROJECTS

Lab retrieval demo. I implemented dense retrieval over a professor's lecture notes, with a small web interface. Two doctoral students used it during group open houses. The code is in the lab GitHub organization. I also built a course project that finetuned a classifier on public news data. That project stayed in the course repository.

WORK EXPERIENCE

Software engineering intern, Lakeshore Analytics, summer 2024. I shipped an internal search box over support tickets. Teaching assistant for an introductory programming course, fall 2024.

HONORS AND AWARDS

Dean's list, three semesters.

LETTERS OF RECOMMENDATION

Letter 1. Professor Helen Park, University of Michigan. "Jordan's retrieval demo is the one we turn on for visitors. The engineering is solid, the code is readable, and Jordan finished it without being managed. I recommend Jordan for a technical master's program."

Letter 2. Chris Feldman, engineering manager, Lakeshore Analytics. "Jordan shipped the support-ticket search and wrote tests for it. I would hire Jordan as a junior engineer. The work was specific and on time."
```

</details>

<details>
<summary><code>06_sam_okonkwo.txt</code></summary>

```text
FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: Sam Okonkwo

STATEMENT OF PURPOSE

I am applying to Northwestern MSAI to learn the modeling I need for a project I have already started and cannot finish honestly. I work as an analyst in a city budget office. We publish spending tables. Residents ask which department grew, and I answer with spreadsheets. I want a model that can flag a line item that changed for a reason the table does not state, and I want to know when that model is wrong.

Since 2024 I have taken linear algebra, probability, and an introductory machine learning course through a university extension program, at night. I have not held a research job. My one project is a small classifier on ten years of public budget rows. It overfits. I can show the learning curve. I cannot yet fix it.

MSAI is the program I want because the coursework is the thing I am missing, and because I can keep the budget data as the project. I am not claiming a research record I do not have. I am applying so the first-year sequence, especially probability and machine learning, is the job I do next. If the committee wants a student who already ships models, I am not that student. If it wants a student with a defined public-data question and the start of the mathematics, I am.

EDUCATION

Undergraduate institution: DePaul University
Degree: B.A. Economics, 2023
Cumulative GPA: 3.45

RESEARCH

No research appointment. Independent study of public budget data, evenings, 2024 to the present, described under projects. I have not published.

PROJECTS

Budget-line classifier. A scikit-learn model on publicly posted city expenditure rows, ten years, one city. I held out the last year. Training accuracy was high and the holdout was near chance. I wrote a short memo about the leak, which was a feature that included the label. The code is in a public repository.

WORK EXPERIENCE

Budget analyst, City of Evanston finance department, July 2023 to the present. I prepare the quarterly spending tables. This is not a machine learning role. Extension coursework at night: linear algebra (A), probability (A-), introduction to machine learning (B+), 2024-2025.

HONORS AND AWARDS

Departmental honor in economics, DePaul, 2023.

LETTERS OF RECOMMENDATION

Letter 1. Director June Alvarez, City of Evanston. "Sam is the analyst I ask to explain a table to a resident. The writing is clear and the numbers are checked. Sam told me about the machine learning courses. I cannot evaluate that work. I can say the analyst work is reliable, and I support this application."

Letter 2. Dr. Robert Klein, university extension instructor. "Sam took my linear algebra and probability courses after work. The homework was complete and the exam grades were A and A-. I do not know Sam's research. I recommend Sam for further quantitative study."
```

</details>

<details>
<summary><code>07_riley_nguyen.txt</code></summary>

```text
FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: Riley Nguyen

STATEMENT OF PURPOSE

I am applying to Northwestern MSAI to go past the capstone I just finished. The capstone was a classifier for campus club event attendance, built with two classmates. I cleaned the registration table, another student trained the model, and I wrote the report. It was a good class project. It is not a system anyone maintained after the term.

I want the MSAI year for the core machine learning sequence and a project that lasts longer than a semester. I am interested in how universities schedule events, which is a small version of a recommendation problem. I have had linear algebra, statistics, a machine learning course, and a databases course. I have not worked in a research group.

I am applying because the program is in the city where I already go to school, and because I want a master's that assumes I will take the foundational courses rather than skip them. I can start from the core. I do not have a paper or an internship model to bring.

EDUCATION

Undergraduate institution: Loyola University Chicago
Degree: B.S. Data Science, 2025
Cumulative GPA: 3.62

RESEARCH

No research appointment.

PROJECTS

Senior capstone, fall 2024, with two classmates. We predicted whether a student would attend a club event from the registration form. I cleaned the data and wrote the final report. I did not train the model. The code is in a course GitHub classroom and was not used after the class ended.

WORK EXPERIENCE

Peer tutor, Loyola data science help room, spring 2024 and fall 2024, four hours a week. Front desk assistant, campus recreation, 2022-2023.

HONORS AND AWARDS

Dean's list, two semesters.

LETTERS OF RECOMMENDATION

Letter 1. Professor Amy Walsh, Loyola University Chicago. "Riley wrote the clearest capstone report in the section. The modeling was a group effort, and Riley's piece was the data and the writing. Riley is ready for a master's core, and I recommend Riley."

Letter 2. Professor Chris Bell, Loyola University Chicago. "Riley tutored in my help room and was patient and prepared. I recommend Riley for graduate study. I have not supervised research."
```

</details>

<details>
<summary><code>08_taylor_brooks.txt</code></summary>

```text
FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: Taylor Brooks

STATEMENT OF PURPOSE

I am applying to MSAI because my statistics degree taught me to fit a model and my internship taught me that fitting it is the easy part. At an insurance internship I rebuilt a churn notebook that a team had been copying forward. I put the split in the right place and wrote down the features. The team used the notebook the rest of the summer. I did not design a new model.

I want Northwestern's program for the machine learning core and for a project with more consequence than a summer notebook. I am interested in how claims models get checked, not in a particular lab. I have had probability, mathematical statistics, regression, and one applied machine learning course. My grades in the theory courses were B's. I am straightforward about that.

I will need the first-year courses. I am applying because I want them, and because I can already do a careful split. I do not have a publication.

EDUCATION

Undergraduate institution: University of Iowa
Degree: B.S. Statistics, 2024
Cumulative GPA: 3.51

RESEARCH

No university research appointment. Internship analysis described under work experience.

PROJECTS

Churn notebook, internship, summer 2023. I replaced a random split that had leaked the renewal month. I documented the features in a README the team kept. I did not deploy a model.

WORK EXPERIENCE

Actuarial intern, Prairie Mutual, Iowa City, May 2023 to August 2023. After graduation, data coordinator at the same office, September 2024 to the present. I check monthly reports. It is not a modeling job.

HONORS AND AWARDS

None beyond the degree.

LETTERS OF RECOMMENDATION

Letter 1. Supervisor Erin Walsh, Prairie Mutual. "Taylor fixed a notebook the team had been copying, wrote down what it did, and left it in a state we still open. I recommend Taylor for further study. Taylor was reliable this summer."

Letter 2. Supervisor Mark Dalton, Prairie Mutual. "Taylor has been on time and pleasant since joining the reporting team. The monthly checks are accurate. I do not have a view of Taylor's technical research. Taylor is a fine colleague."
```

</details>

<details>
<summary><code>09_casey_morgan.txt</code></summary>

```text
FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: Casey Morgan

STATEMENT OF PURPOSE

Artificial intelligence is the future, and I want to be part of that future at Northwestern. I have always loved technology and I think MSAI would be an amazing experience. I am a people person and I work hard. In my classes I did several projects with AI, including a to-do app and a digit recognizer, and I learned a lot from them.

I believe I would contribute to the Northwestern community and make the most of every opportunity. My dream is to work in tech and use AI to help businesses. I am open to any specialization the faculty think is best. Thank you for your time and for considering me for this prestigious program. I know I can succeed if I am given the chance.

EDUCATION

Undergraduate institution: Illinois State University
Degree: B.S. Information Systems, 2025
Cumulative GPA: 3.20

RESEARCH

No research experience.

PROJECTS

Course project, fall 2024: a to-do list web app for an information systems class. It stores tasks in a database. It does not use a learned model. Course project, spring 2025: a digit recognizer using a tutorial neural network on the MNIST images supplied by the instructor. I followed the tutorial and submitted the notebook.

WORK EXPERIENCE

Help desk student employee, Illinois State technology support, 2023-2025. I reset passwords and imaged laptops.

HONORS AND AWARDS

None.

LETTERS OF RECOMMENDATION

Letter 1. Supervisor Pat Nolan, campus help desk. "Casey is a hard worker and a pleasure to have on the desk. Students like Casey. I recommend Casey."

Letter 2. Instructor Jamie Cole, Illinois State. "Casey completed the required projects and attended class. Casey is a hardworking student. I am happy to support the application."
```

</details>

<details>
<summary><code>10_drew_patel.txt</code></summary>

```text
FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: Drew Patel

STATEMENT OF PURPOSE

I hope to study artificial intelligence at Northwestern so I can bring AI to medicine. Biology has been my whole education, and I have done well in it. I believe the next generation of doctors will need AI, and I want to be ready. MSAI is a famous program and Boston has shown me that I can handle hard classes. I am sure I can handle these classes too.

I have not taken a machine learning course. I took one introduction to Python as an elective in my junior year and I enjoyed it. I learn quickly. My plan is to arrive and take the courses, then apply AI to cancer or maybe medical images. I do not have a specific project yet. I am excited to find one with a professor. I know my grades show that I am serious, and I hope the committee will see that potential.

EDUCATION

Undergraduate institution: Boston University
Degree: B.S. Biology, 2025
Cumulative GPA: 3.88

RESEARCH

No computational research. I volunteered in a wet lab for one semester washing glassware, fall 2023. I did not design an experiment.

PROJECTS

Introduction to Python, spring 2024, course assignments only. The final assignment was a script that plotted a CSV of heart rates from the instructor. I have no other programming projects.

WORK EXPERIENCE

Peer tutor for introductory biology, Boston University, 2023-2025.

HONORS AND AWARDS

College of Arts and Sciences prize for biology coursework, 2025. Dean's list every semester.

LETTERS OF RECOMMENDATION

Letter 1. Professor Laura Kim, Boston University. "Drew earned an A in both of my biology courses and tutored students who were failing the first exam. Drew is diligent and kind. I have not seen Drew write research code. On the academic record I do have, I recommend Drew."

Letter 2. Dr. Steven Cho, Boston University. "Drew was reliable in my laboratory as a volunteer. The tasks were preparatory. Drew followed instructions. I support Drew's interest in further study and I cannot speak to preparation in computer science."
```

</details>

<details>
<summary><code>11_quinn_alvarez.txt</code></summary>

```text
FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: Quinn Alvarez

STATEMENT OF PURPOSE

I am applying to MSAI because I want a fresh start in artificial intelligence at a top school. I think Northwestern can give me the environment I need to focus. I am interested in all areas of AI, from robotics to language, and I will work harder in graduate school than I did as an undergraduate. I had some research experience and I know what labs are like.

Please consider the person I am becoming and not only my GPA. I am passionate and I will contribute. A master's degree is my path into the industry. I would be grateful for an offer and I will make the most of it.

EDUCATION

Undergraduate institution: Arizona State University
Degree: B.S. Computer Science, 2024
Cumulative GPA: 2.95

RESEARCH

Unpaid observer in a robotics lab, May 2024, about four weeks. I attended two group meetings and watched a doctoral student collect data. I did not write code for the lab and I am not on a paper.

PROJECTS

Course projects required by the degree: a socket chat program, a small web scraper, and a class assignment that trained a decision tree on a provided CSV. I do not have an independent project.

WORK EXPERIENCE

Seasonal retail associate, 2022 and 2023 summers.

HONORS AND AWARDS

None.

LETTERS OF RECOMMENDATION

Letter 1. Professor Alan Ruiz, Arizona State University. "Quinn completed my course. The project met the minimum specification. Quinn missed two deadlines and submitted the scraper a week late. I can confirm the degree progress. I do not have a stronger recommendation than that."

Letter 2. Graduate student Morgan Lee, Arizona State University. "Quinn visited our lab for a few weeks. Quinn was polite. Quinn did not take on a task. I cannot recommend Quinn for a research program on the basis of that visit."
```

</details>

<details>
<summary><code>12_harper_singh.txt</code></summary>

```text
FICTIONAL TEST PACKET. Not a real application.

Applicant's Name: Harper Singh

STATEMENT OF PURPOSE

I am writing to apply for the MSAI program because artificial intelligence is changing communication and I want to be at the center of that change. I have a communications degree and I completed an online certificate in AI for everyone. The videos were inspiring. I believe my background in writing and presentations is exactly what technical teams are missing, and Northwestern is where I want to learn the technical side.

I do not have programming courses beyond the certificate quizzes. I am a fast learner and a strong communicator, and I know I can pick up the coding once I am in the classroom. My goal is to lead AI product teams. I would bring energy and storytelling to the cohort. I hope you will give me the chance to show that a nontraditional student belongs in this program. I will not waste it.

EDUCATION

Undergraduate institution: University of Iowa
Degree: B.A. Communications, 2024
Cumulative GPA: 3.10

RESEARCH

No research experience.

PROJECTS

Online certificate, "AI for Everyone," 2025, with short quizzes. I did not write code. Class presentation project in a communications course: a slide deck about how chatbots change customer service, based on news articles.

WORK EXPERIENCE

Social media assistant, a campus arts series, 2023-2024. I wrote posts and a newsletter. Intern, a local radio station, summer 2023, where I booked guests.

HONORS AND AWARDS

Student radio volunteer of the semester, fall 2023.

LETTERS OF RECOMMENDATION

Letter 1. Station manager Robin Blake. "Harper booked guests and wrote clear introductions. Harper is articulate and reliable in a newsroom. I recommend Harper for work that uses those skills. I have not seen technical or quantitative work."

Letter 2. Instructor Caroline Weiss, University of Iowa. "Harper writes well and spoke confidently in my course. The chatbot presentation was polished. It was not a technical analysis. Harper is a strong communications student, and that is the basis of this letter."
```

</details>
