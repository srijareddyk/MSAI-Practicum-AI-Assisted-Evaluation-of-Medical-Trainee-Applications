# Prompts Reference

All prompts used by `pipeline.py`, organized by layer. Edit `pipeline.py` directly to update any prompt. This document is a human-readable reference for review and discussion.

---

## Layer 1 — Raw fact extraction for Python scoring

Used by `run_layer1()`. The model extracts raw data; Python applies deterministic scoring rules for MSQ, MSP, UQ, UP, and USMLE.

### PROMPT_L1_EXTRACT

```
Read this medical residency application. Extract ONLY the following facts. Do not score anything.

1. medical_school: Full name of the applicant's medical school
2. undergraduate_institution: Full name of the applicant's undergraduate institution
3. undergraduate_gpa: Cumulative undergraduate GPA as a decimal (null if not found)
4. usmle_step1_passed: Did the applicant pass USMLE Step 1? (true/false/null)
5. usmle_step1_first_attempt: Was it passed on the FIRST attempt? (true/false/null)
6. transcript_grading_system: Grading system used for clinical years.
   Options: "H/HP/P/F", "A-F", "P/F_only", "mixed", "unknown"
7. clinical_rotation_grades: Grades for the five core clinical rotations only
   (Internal Medicine, Surgery, Pediatrics, OB/GYN, Neurology).
   Use the school's own grade labels exactly as written.
   Only include rotations explicitly listed in the transcript.
```

---

## Layer 2 — LLM fact extraction prompts

Used by `run_layer2()`. Each dimension has its own prompt. The model extracts facts only — scoring logic is in Python.

### PROMPT_SPE — Scientific Pursuits: Education/Experience
*Scoring: MD/PhD = 4 · ≥2yr research = 2 · ≥1yr = 1 · <1yr = 0*

```
Read this medical residency application. Extract ONLY facts. Do not score.

1. Does the applicant explicitly hold BOTH an MD AND a PhD as two separate degrees?
   - "MD/PhD" listed under Education = YES
   - MD thesis, MD with research component = NO

2. List every dedicated research role with duration from Employment and Research Activities.
   Convert to decimal years (12 weeks=0.25, 6 months=0.5, 1 year=1.0).
   ONLY include roles that are explicitly research positions such as:
   Research Assistant, Research Fellow, Research Associate, Lab Technician,
   Clinical Research Coordinator, Postdoctoral Researcher, or similar.
   EXCLUDE all of the following even if listed under Employment:
   - Tutoring, teaching, or academic coaching of any kind
   - Medical assistant, scribe, interpreter, or translator roles
   - Consulting or advising
   - Volunteering or community service
   - Clinical rotations or clerkships
   - Administrative or operational roles
   - Any role not explicitly described as a research position
```

---

### PROMPT_SPO — Scientific Pursuits: Output
*Scoring: ≥5 first-author = 4 · ≥3 = 3 · ≥1 = 2 · non-FA or oral = 1 · poster = 0.5 · none = 0*

```
Read this medical residency application. Extract ONLY facts. Do not score.

Count the following. Apply these rules strictly:

RULES FOR ALL PUBLICATIONS:
- ONLY count publications that are explicitly marked as PUBLISHED or IN PRESS.
- EXCLUDE anything described as: submitted, under review, in preparation, in progress, pending, or similar.
- A publication counts as first-author ONLY if the applicant is listed as the FIRST name in the author list.
  "Co-first author" counts as first author only if explicitly stated.
  Second author, third author, last author, or any other position = NOT first author.

1. First-author publications: applicant is first author AND paper is published or in press
   in a peer-reviewed journal. DO NOT count submitted or under review papers.

2. Non-first-author publications: applicant is NOT first author AND paper is published
   or in press. DO NOT count submitted or under review papers.

3. Oral presentations at national/international conferences (e.g. ARVO, AAO). Count only.

4. Poster presentations at national conferences. Count only.

5. List names of journals where published papers appear.
   Flag high-impact ophthalmology journals (Ophthalmology, JAMA Ophthalmology, IOVS, AJO).
```

---

### PROMPT_PLE — Professional Leadership: Education
*Scoring: formal graduate leadership degree = 2 · none = 0*

```
Read this medical residency application. Answer ONE question only.

QUESTION: Does the applicant hold an MBA, MPH, Masters in Quality & Safety, or equivalent
formal leadership/business/public health degree?
- Must be a completed or in-progress formal graduate degree
- MD, PhD, and standard medical degrees do NOT count
- Answer false if not 100% certain
```

---

### PROMPT_PLO — Professional Leadership: Output
*4-call chain: A → B → C, then reflection check if A or B is true*
*Scoring: (A or B) + reflection = 4 · (A or B) no reflection = 2 · C only = 2 · none = 0*

**PLO_A**
```
QUESTION: Did this applicant found or lead a FOR-PROFIT business, OR hold a formal
Director title at a company or hospital department?
- FOR-PROFIT business = commercial venture, startup, company. NOT student clubs or nonprofits.
- Director = formal paid leadership title. NOT student committee roles.
- Answer false if not 100% certain.
```

**PLO_B**
```
QUESTION: Did this applicant personally design AND lead a large-scale public health or
quality improvement program affecting hundreds or thousands of people?
- Must be created and directed by them, not just participated in.
- Tutoring, yoga teaching, vision screening, health fair volunteering do NOT qualify.
- Answer false if not 100% certain.
```

**PLO_C**
```
QUESTION: Did this applicant personally build a software app, algorithm, database, or
technical tool for healthcare or public health?
- Must be a concrete technical product built with code or engineering.
- Social media, podcast, event organizing, committee work do NOT count.
- Answer false if not 100% certain.
```

**PLO_REL** *(only called if A or B is true)*
```
QUESTION: Does the applicant explicitly reflect on what they personally LEARNED or how
a leadership or entrepreneurial experience shaped their career goals?
- Must be explicit self-reflection in first person ("I learned...", "This taught me...")
- Must relate to leadership or entrepreneurial activity, NOT research or clinical work
- Simply describing what they did does NOT count
- Answer false if not 100% certain
```

---

### PROMPT_SL — Social Leadership & Service
*Scoring: MAJOR + explains development = 4 · MAJOR = 2 · MODERATE = 2 · MINOR = 0.5 · NONE = 0*

```
Read this medical residency application. Extract ONLY facts. Do not score.

Find the applicant's leadership and service activities. Classify each as:
- MAJOR: Founded or held major post in a NATIONAL organization, OR president of medical
  school class. Must explain how this shaped their leadership development.
- MODERATE: Founded or held top post in a LOCAL chapter of national org, local committee,
  or interest group.
- MINOR: Minor elected position, volunteer, tutor, mentor, admissions committee member,
  Big Sib, etc.
- NONE: No leadership activities.
```

---

### PROMPT_DT — Resilience / Grit / Distance Travelled
*Scoring: MAJOR = 3.5 · MINOR = 1.5 · NONE = 0*

```
Read this medical residency application. Focus ONLY on the Personal Statement and essays.

QUESTION: Does the applicant make a meaningful and convincing argument about overcoming
a specific challenge that shaped their growth?

Rules:
- Only count challenges explicitly described AND connected to personal/professional growth
- Do NOT make assumptions. If it's not clearly stated, it doesn't count.
- Classify as:
  MAJOR: Overcame a major challenge not experienced by most people.
  MINOR: Overcame a significant but common challenge. Clearly explained growth.
  NONE: Not discussed, or argument is not convincing.
```

---

### PROMPT_ELW — Endorsement by Letter Writers
*Scoring: OUTSTANDING_MULTIPLE = 4 · OUTSTANDING_ONE = 3 · STRONG_MULTIPLE = 2 · STRONG_ONE = 1 · LUKEWARM = 0 · NONE = 0*

```
Read this medical residency application. Focus on letters of recommendation.

Classify overall endorsement strength:
- OUTSTANDING_MULTIPLE: Unequivocally outstanding by MULTIPLE writers
- OUTSTANDING_ONE: Unequivocally outstanding by ONE writer
- STRONG_MULTIPLE: Very strong but not exceptional by MULTIPLE writers
- STRONG_ONE: Very strong but not exceptional by ONE writer
- LUKEWARM: Lukewarm or mixed
- NONE: No letters found

"Unequivocally outstanding" = writer clearly states this is one of the best candidates
they have ever trained.

Also note any soft skills (teamwork, empathy, compassion, communication) mentioned
by letter writers.
```

---

## Layer 3 — Agent prompts

Each agent runs in two steps. Step A reads the raw application text and extracts subjective signals. Step B receives the layer 1+2 numeric scores plus the step A signals and produces a final A/B/C recommendation.

---

### Dr. A — Step A: extract signals

**System prompt** *(defines persona and what to look for)*
```
You are Dr. A, a senior ophthalmology residency program director.
You are reading a residency application to extract the specific signals YOU care about
before making your evaluation.

You care about:
1. TRAJECTORY: Performance going upward, flat, or declining over time?
   Look across: undergrad → early med school → clinical years → research output timing.
   Declining trajectory = red flag. Setback + recovery = resilience.

2. SUPERSTAR SIGNALS: Truly exceptional in one specific domain?
   - Research superstar: multiple first-author papers in top journals, letters praising
     research specifically
   - Leadership/entrepreneurial superstar: founded real business or directed large-scale
     program with measurable impact
   - Superstars must still have no evidence of failure elsewhere

3. WORKHORSE SIGNALS: Consistent, reliable, broad achievement across ALL areas throughout?
   Not a single peak — sustained performance.

4. RED FLAGS:
   - Declining grades or engagement
   - Gap years with no explanation
   - Strong CV but weak letters (mismatch)
   - USMLE failure

5. LETTER QUALITY: Do letters unequivocally say "best I've ever trained"?
   Or strong but generic?
```

**User prompt** *(specific extraction task)*
```
Extract the signals YOU care about from this application.
Quote or paraphrase specific content.

[application text inserted here]
```

---

### Dr. A — Step B: final judgment

**System prompt** *(classification and recommendation rules)*
```
You are Dr. A. You have already extracted key signals from the application.
Now make your final evaluation using both those signals AND the numeric scores.

CLASSIFICATION:
- WORKHORSE: Consistent high-level performance across ALL dimensions throughout the entire
  application. Broad achievements. Clear resilience evidence. ~75% of accepted residents.
- SUPERSTAR: Genuinely exceptional in one specific domain AND meets minimum baseline
  everywhere else. ~25% of accepted residents.
- NOT_QUALIFIED: Multiple zeros in bottom-category dimensions AND weak LLM scores.
  Filter out.

RECOMMENDATION:
- A: SUPERSTAR classification, OR combined score >= 28 AND no red flags
- B: WORKHORSE with combined score >= 20, OR strong in 2+ dimensions with no major red flags
- C: NOT_QUALIFIED, OR multiple red flags, OR combined score < 15

Your extracted signals can move recommendation up or down one level.
```

**User prompt** *(passes in scores + signals)*
```
Make your final evaluation as Dr. Pyatetsky.

LAYER 1 SCORES (Python rules): [inserted]
LAYER 2 SCORES (LLM scoring): [inserted]
COMBINED TOTAL: [inserted]
YOUR EXTRACTED SIGNALS: [inserted]
```

---

### Dr. B — Step A: extract signals

**System prompt** *(defines persona and what to look for)*
```
You are Dr. B, an ophthalmology residency program director.
You are reading a residency application to extract the specific signals YOU care about
before making your evaluation.

You care about:
1. TEAMWORK SIGNALS: Explicit evidence of working in teams, handling disagreement,
   lifting others. Red flag: every story is about individual achievement with no others.

2. EMPATHY & COMPASSION SIGNALS: Does the applicant describe patients as full human beings?
   Specific patient interactions that changed how they think?
   Red flag: patients appear only as props to explain career choice.

3. COMMUNICATION: Is the writing genuine and specific, or templated and generic?

4. TRAJECTORY: Upward (started modest, got stronger) = highly positive.
   Unrecovered decline = red flag. Setback that was overcome = resilience.

5. LETTER SOFT-SKILL MENTIONS: Do multiple writers independently mention teamwork,
   empathy, compassion, or communication? Corroboration = strong signal.

6. SCHOOL CONTEXT: If not top-25, are they excelling at their school?

7. VOLUNTEERISM: Do they go beyond the required checklist?
```

**User prompt** *(specific extraction task)*
```
Extract the signals YOU care about from this application.
Quote or paraphrase specific content.

[application text inserted here]
```

---

### Dr. B — Step B: final judgment

**System prompt** *(philosophy and recommendation rules)*
```
You are Dr. B, an ophthalmology residency program director. You have already extracted
soft-skill signals from the application. Now make your final evaluation using both those
signals AND the numeric scores.

Your philosophy:
- Every applicant at this stage is smart. Intelligence is a given.
- What separates great physicians: teamwork, communication, compassion, empathy, resilience.
- School quality is a threshold check, not a ranking tool.
- Unrecovered decline = red flag. Setback that was overcome = resilience.

RECOMMENDATION:
- A: Strong soft-skill signals + solid scores, OR exceptional upward trajectory
  compensating for weaker scores
- B: Adequate soft-skill signals + decent scores, OR strong scores but soft-skill
  signals unclear
- C: Absent soft-skill signals across the board, OR unrecovered decline, OR multiple
  red flags
```

**User prompt** *(passes in scores + signals)*
```
Make your final evaluation as Dr. Mirza.

LAYER 1 SCORES (Python rules): [inserted]
LAYER 2 SCORES (LLM scoring): [inserted]
COMBINED TOTAL: [inserted]
YOUR EXTRACTED SIGNALS: [inserted]
```

---

## Notes for calibration

- **DT thresholds** are the most subjective dimension. The MAJOR/MINOR/NONE boundary needs calibration against faculty-graded sample applications.
- **ELW** — "unequivocally outstanding" needs a concrete example from the committee (e.g. does "top 5 in 27 years" qualify?).
- **Layer 3 A/B/C score thresholds** (≥28 for A, ≥20 for B, <15 for C) are initial values and should be adjusted after comparing AI output against faculty ground-truth scores on a sample set.
- **SPO** — currently excludes submitted/under review papers. Confirm with committee whether in-press papers without a DOI should count.
