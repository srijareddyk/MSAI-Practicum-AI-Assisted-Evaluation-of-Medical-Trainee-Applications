import ollama
import json

RESUME_PATH = "Liang,_Alvina_AU83956_OPHTH-R_2025-26.txt"
MODEL = "qwen3:32b"


# ═════════════════════════════════════════════════════════════════════════════
# SHARED UTILITIES
# ═════════════════════════════════════════════════════════════════════════════

def call_model(prompt: str, resume_text: str) -> dict:
    """Layers 1 and 2: plain user prompt, model extracts facts only."""
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt.format(resume_text=resume_text)}],
        options={"temperature": 0.1},
        think=True,
    )
    raw = response["message"]["content"].strip()
    try:
        return json.loads(raw[raw.find("{"):raw.rfind("}")+1])
    except Exception:
        return {}


def call_agent(system_prompt: str, user_content: str) -> dict:
    """Layer 3: system prompt gives the model a physician persona."""
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
        options={"temperature": 0.1},
        think=True,
    )
    raw = response["message"]["content"].strip()
    try:
        return json.loads(raw[raw.find("{"):raw.rfind("}")+1])
    except Exception:
        return {"raw_output": raw}


# ═════════════════════════════════════════════════════════════════════════════
# LAYER 1: Python rule-based scoring (LLM extracts raw data, Python scores)
# Dimensions: MSQ, MSP, UQ, UP, USMLE
# ═════════════════════════════════════════════════════════════════════════════

TOP25_MEDICAL = {
    "harvard", "johns hopkins", "ucsf", "stanford", "mayo clinic",
    "university of pennsylvania", "columbia", "yale", "duke", "vanderbilt",
    "university of chicago", "washington university", "cornell", "michigan",
    "northwestern", "emory", "pittsburgh", "usc", "ucsd", "ucla",
    "new york university", "mount sinai", "baylor", "tufts", "dartmouth",
}

TOP25_UNDERGRAD = {
    "mit", "harvard", "stanford", "princeton", "yale", "columbia",
    "university of chicago", "university of pennsylvania", "duke", "northwestern",
    "dartmouth", "brown", "vanderbilt", "rice", "notre dame", "cornell",
    "johns hopkins", "georgetown", "emory", "carnegie mellon",
    "uc berkeley", "ucla", "university of michigan", "university of virginia",
    "wake forest",
}



HONOR_TOKENS = {"h", "honors", "honor"}
HP_TOKENS    = {"hp", "high pass", "highpass", "com", "ccd"}
PASS_TOKENS  = {"p", "pass", "s", "m", "lp"}
FAIL_TOKENS  = {"f", "fail", "u"}


def _is_top_school(name, top_set):
    if not name:
        return False
    low = name.lower()
    return any(t in low for t in top_set)


def _score_msp(grades, grading_system):
    if not grades:
        return None
    if grading_system == "P/F_only":
        return 2.25
    vals = list(grades.values())
    if any(v.strip().lower() in FAIL_TOKENS for v in vals):
        return 0
    honors    = sum(1 for v in vals if v.strip().lower() in HONOR_TOKENS)
    high_pass = sum(1 for v in vals if v.strip().lower() in HP_TOKENS)
    if honors >= 3:    return 4
    if honors >= 1:    return 3
    if high_pass >= 1: return 2
    return 1


def _extract_l1_facts(text):
    """Pure regex extraction of Layer 1 fields. No LLM."""
    import re

    # Medical school
    med_school = None
    for pat in [
        r"(?:Medical Education|Medical School|School of Medicine)[:\s]*\n?\s*([A-Z][^\n]{5,80})",
        r"((?:University|College|School|Institute|Mayo Clinic)[^\n]{5,70}(?:School of Medicine|Medical School|Medicine))",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            med_school = m.group(1).strip().rstrip(",")
            break

    # Undergraduate
    undergrad = None
    for pat in [
        r"(?:Undergraduate Education|Undergraduate Institution|Bachelor)[:\s]*\n?\s*([A-Z][^\n]{5,80})",
        r"(?:B\.?S\.?|B\.?A\.?|Bachelor)[^\n]*\n\s*([A-Z][^\n]{5,70}(?:University|College|Institute))",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            undergrad = m.group(1).strip().rstrip(",")
            break

    # GPA
    gpa = None
    for pat in [
        r"(?:Cumulative GPA|Overall GPA|GPA)[:\s]+([0-9]\.[0-9]{1,3})",
        r"([0-9]\.[0-9]{1,3})\s*/\s*4\.0",
        r"GPA[:\s]+([0-9]\.[0-9]{2})",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1))
                if 0.0 < val <= 4.0:
                    gpa = round(val, 2)
                    break
            except ValueError:
                pass

    # USMLE Step 1
    step1_pass = None
    step1_first = None
    usmle_m = re.search(r"USMLE Step 1[^\n]*\n((?:[^\n]+\n){0,6})", text, re.IGNORECASE)
    if usmle_m:
        block = usmle_m.group(0).lower()
        if "pass" in block:
            step1_pass = True
            step1_first = "fail" not in block.split("pass")[0]
        elif "fail" in block:
            step1_pass = False
            step1_first = False
    if step1_pass is None:
        m = re.search(r"step\s*1[^\n]{0,40}(pass|fail)", text, re.IGNORECASE)
        if m:
            step1_pass = m.group(1).lower() == "pass"
            step1_first = True

    # Clinical rotation grades
    CORE_ROTATIONS = {
        "Internal Medicine": r"internal\s+medicine",
        "Surgery":           r"(?:general\s+)?surgery",
        "Pediatrics":        r"pediatrics?",
        "OB/GYN":            r"ob/?gyn|obstetrics|gynecology",
        "Neurology":         r"neurology",
    }
    GRADE_PAT = r"(honors?|high\s+pass|h/p|hp|pass|fail|p/f|[ABCDF]|com|ccd|s\b|u\b|lp)"
    rot_grades = {}
    for label, rot_pat in CORE_ROTATIONS.items():
        m = re.search(rot_pat + r"[^\n]{0,60}" + GRADE_PAT, text, re.IGNORECASE)
        if m:
            rot_grades[label] = m.group(m.lastindex).strip()

    # Infer grading system
    grading_sys = "unknown"
    if rot_grades:
        vals = [v.lower() for v in rot_grades.values()]
        has_honor = any(v in {"h", "honors", "honor"} for v in vals)
        has_hp    = any(v in {"hp", "high pass"} for v in vals)
        has_letter = any(re.match(r"^[a-f]$", v) for v in vals)
        has_pf    = any(v in {"p", "pass", "f", "fail"} for v in vals)
        if has_honor or has_hp:
            grading_sys = "H/HP/P/F"
        elif has_letter:
            grading_sys = "A-F"
        elif has_pf:
            grading_sys = "P/F_only"
        else:
            grading_sys = "mixed"

    return {
        "medical_school": med_school,
        "undergraduate_institution": undergrad,
        "undergraduate_gpa": gpa,
        "usmle_step1_passed": step1_pass,
        "usmle_step1_first_attempt": step1_first,
        "transcript_grading_system": grading_sys,
        "clinical_rotation_grades": rot_grades,
    }


def run_layer1(resume_text):
    """Layer 1: pure regex extraction — no LLM. Python computes all scores."""
    print("  [Layer 1] Extracting facts with regex (no LLM)...")
    raw = _extract_l1_facts(resume_text)

    med_school  = raw["medical_school"]
    undergrad   = raw["undergraduate_institution"]
    gpa         = raw["undergraduate_gpa"]
    step1_pass  = raw["usmle_step1_passed"]
    step1_first = raw["usmle_step1_first_attempt"]
    grading_sys = raw["transcript_grading_system"]
    rot_grades  = raw["clinical_rotation_grades"]

    msq = 4 if _is_top_school(med_school, TOP25_MEDICAL) else 0
    uq  = 2 if _is_top_school(undergrad,  TOP25_UNDERGRAD) else 0

    if gpa is None:      up = None
    elif gpa >= 3.8:     up = 4
    elif gpa >= 3.5:     up = 3
    elif gpa >= 3.25:    up = 2
    elif gpa >= 3.0:     up = 1
    else:                up = 0

    if step1_pass is None:                   usmle = None
    elif not step1_pass or not step1_first:  usmle = "F"
    else:                                    usmle = "P"

    msp = _score_msp(rot_grades, grading_sys)

    return {
        "MSQ":   {"score": msq,  "medical_school": med_school},
        "MSP":   {"score": msp,  "grading_system": grading_sys, "rotation_grades": rot_grades},
        "UQ":    {"score": uq,   "undergraduate": undergrad},
        "UP":    {"score": up,   "gpa": gpa},
        "USMLE": {"score": usmle, "passed": step1_pass, "first_attempt": step1_first},
    }



# ═════════════════════════════════════════════════════════════════════════════
# LAYER 2: LLM fact extraction + Python scoring
# Dimensions: SPE, SPO, PLE, PLO, SL, DT, ELW
# ═════════════════════════════════════════════════════════════════════════════

PROMPT_SPE = """Read this medical residency application. Extract ONLY facts. Do not score.

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

Resume:
{resume_text}

Output JSON only:
{{"md_phd": <true/false>, "research_roles": [{{"role": "<name>", "duration_text": "<text>", "duration_years": <decimal>}}]}}"""

PROMPT_SPO = """Read this medical residency application. Extract ONLY facts. Do not score.

Count the following. Apply these rules strictly:

RULES FOR ALL PUBLICATIONS:
- ONLY count publications that are explicitly marked as PUBLISHED or IN PRESS.
- EXCLUDE anything described as: submitted, under review, in preparation, in progress, pending, or similar.
- A publication counts as first-author ONLY if the applicant is listed as the FIRST name in the author list.
  "Co-first author" counts as first author only if explicitly stated.
  Second author, third author, last author, or any other position = NOT first author.

1. First-author publications: applicant is first author AND paper is published or in press in a peer-reviewed journal.
   DO NOT count submitted or under review papers even if the applicant is first author.

2. Non-first-author publications: applicant is NOT first author AND paper is published or in press in a peer-reviewed journal.
   DO NOT count submitted or under review papers.

3. Oral presentations at national/international conferences (e.g. ARVO, AAO). Count only.

4. Poster presentations at national conferences. Count only.

5. List the names of any peer-reviewed journals where published papers appear.
   Flag any high-impact ophthalmology journals (e.g. Ophthalmology, JAMA Ophthalmology, IOVS, American Journal of Ophthalmology).

Resume:
{resume_text}

Output JSON only:
{{"first_author_pubs": <int>, "non_first_author_pubs": <int>, "oral_presentations": <int>, "poster_presentations": <int>, "high_impact_journals": [<list of journal names>], "excluded_submitted": <int>}}"""

PROMPT_PLE = """Read this medical residency application. Answer ONE question only.

QUESTION: Does the applicant hold an MBA, MPH, Masters in Quality & Safety, or equivalent formal leadership/business/public health degree?
- Must be a completed or in-progress formal graduate degree
- MD, PhD, and standard medical degrees do NOT count
- Answer false if not 100% certain

Resume:
{resume_text}

Output JSON only:
{{"answer": <true/false>, "evidence": "<exact quote or empty>", "degree_name": "<name or empty>"}}"""

PROMPT_PLO_A = """Read this resume. Answer ONE question only.

QUESTION: Did this applicant found or lead a FOR-PROFIT business, OR hold a formal Director title at a company or hospital department?
- FOR-PROFIT business = commercial venture, startup, company. NOT student clubs or nonprofits.
- Director = formal paid leadership title. NOT student committee roles.
- Answer false if not 100% certain.

Resume:
{resume_text}

Output JSON only:
{{"answer": <true/false>, "evidence": "<exact quote or empty>"}}"""

PROMPT_PLO_B = """Read this resume. Answer ONE question only.

QUESTION: Did this applicant personally design AND lead a large-scale public health or quality improvement program affecting hundreds or thousands of people?
- Must be created and directed by them, not just participated in.
- Tutoring, yoga teaching, vision screening, health fair volunteering do NOT qualify.
- Answer false if not 100% certain.

Resume:
{resume_text}

Output JSON only:
{{"answer": <true/false>, "evidence": "<exact quote or empty>"}}"""

PROMPT_PLO_C = """Read this resume. Answer ONE question only.

QUESTION: Did this applicant personally build a software app, algorithm, database, or technical tool for healthcare or public health?
- Must be a concrete technical product built with code or engineering.
- Social media, podcast, event organizing, committee work do NOT count.
- Answer false if not 100% certain.

Resume:
{resume_text}

Output JSON only:
{{"answer": <true/false>, "evidence": "<exact quote or empty>"}}"""

PROMPT_PLO_REL = """Read this resume. Answer ONE question only.

QUESTION: Does the applicant explicitly reflect on what they personally LEARNED or how a leadership or entrepreneurial experience shaped their career goals?
- Must be explicit self-reflection in first person ("I learned...", "This taught me...")
- Must relate to leadership or entrepreneurial activity, NOT research or clinical work
- Simply describing what they did does NOT count
- Answer false if not 100% certain

Resume:
{resume_text}

Output JSON only:
{{"answer": <true/false>, "evidence": "<exact quote or empty>"}}"""

PROMPT_SL = """Read this medical residency application. Extract ONLY facts. Do not score.

Find the applicant's leadership and service activities. Classify each as:
- MAJOR: Founded or held major post in a NATIONAL organization, OR president of medical school class. Must explain how this shaped their leadership development.
- MODERATE: Founded or held top post in a LOCAL chapter of national org, local committee, or interest group.
- MINOR: Minor elected position, volunteer, tutor, mentor, admissions committee member, Big Sib, etc.
- NONE: No leadership activities.

Resume:
{resume_text}

Output JSON only:
{{"best_level": "<MAJOR/MODERATE/MINOR/NONE>", "activities": [{{"description": "<one sentence>", "level": "<MAJOR/MODERATE/MINOR/NONE>", "explains_development": <true/false>}}]}}"""

PROMPT_DT = """Read this medical residency application. Focus ONLY on the Personal Statement and essays.

QUESTION: Does the applicant make a meaningful and convincing argument about overcoming a specific challenge that shaped their growth?

Rules:
- Only count challenges explicitly described AND connected to personal/professional growth
- Do NOT make assumptions. If it's not clearly stated, it doesn't count.
- Classify as:
  MAJOR: Overcame a major challenge not experienced by most people.
  MINOR: Overcame a significant but common challenge. Clearly explained growth.
  NONE: Not discussed, or argument is not convincing.

Resume:
{resume_text}

Output JSON only:
{{"level": "<MAJOR/MINOR/NONE>", "evidence": "<exact quote from essay if applicable, otherwise empty>"}}"""

PROMPT_ELW = """Read this medical residency application. Focus on letters of recommendation.

Classify overall endorsement strength:
- OUTSTANDING_MULTIPLE: Unequivocally outstanding by MULTIPLE writers
- OUTSTANDING_ONE: Unequivocally outstanding by ONE writer
- STRONG_MULTIPLE: Very strong but not exceptional by MULTIPLE writers
- STRONG_ONE: Very strong but not exceptional by ONE writer
- LUKEWARM: Lukewarm or mixed
- NONE: No letters found

"Unequivocally outstanding" = writer clearly states this is one of the best candidates they have ever trained.

Also note any soft skills (teamwork, empathy, compassion, communication) mentioned by letter writers.

Resume:
{resume_text}

Output JSON only:
{{"level": "<level>", "evidence": "<exact quote or empty>", "soft_skill_mentions": [<list of soft skills mentioned>]}}"""


def score_spe(resume_text):
    f = call_model(PROMPT_SPE, resume_text)
    md_phd = f.get("md_phd", False)
    roles = f.get("research_roles", [])
    total = sum(r.get("duration_years", 0) for r in roles)
    if md_phd:         score = 4
    elif total >= 2.0: score = 2
    elif total >= 1.0: score = 1
    else:              score = 0
    return {"score": score, "md_phd": md_phd, "total_years": round(total, 2), "roles": roles}


def score_spo(resume_text):
    f = call_model(PROMPT_SPO, resume_text)
    fa       = f.get("first_author_pubs", 0)
    nfa      = f.get("non_first_author_pubs", 0)
    oral     = f.get("oral_presentations", 0)
    poster   = f.get("poster_presentations", 0)
    journals = f.get("high_impact_journals", [])
    excluded = f.get("excluded_submitted", 0)
    if fa >= 5:                 score = 4
    elif fa >= 3:               score = 3
    elif fa >= 1:               score = 2
    elif nfa >= 1 or oral >= 1: score = 1
    elif poster >= 1:           score = 0.5
    else:                       score = 0
    return {"score": score, "first_author": fa, "non_first_author": nfa,
            "oral": oral, "poster": poster, "high_impact_journals": journals,
            "excluded_submitted": excluded}


def score_ple(resume_text):
    f = call_model(PROMPT_PLE, resume_text)
    score = 2 if f.get("answer", False) else 0
    return {"score": score, "found": f.get("answer", False),
            "evidence": f.get("evidence", ""), "degree_name": f.get("degree_name", "")}


def score_plo(resume_text):
    a = call_model(PROMPT_PLO_A, resume_text)
    b = call_model(PROMPT_PLO_B, resume_text)
    c = call_model(PROMPT_PLO_C, resume_text)
    has_a = a.get("answer", False)
    has_b = b.get("answer", False)
    has_c = c.get("answer", False)
    if has_a or has_b:
        rel = call_model(PROMPT_PLO_REL, resume_text)
        has_rel = rel.get("answer", False)
        score = 4 if has_rel else 2
        logic = "A/B + reflection → 4" if has_rel else "A/B no reflection → 2"
        evidence = a.get("evidence") or b.get("evidence", "")
    elif has_c:
        score, logic = 2, "TYPE_C"
        evidence = c.get("evidence", "")
    else:
        score, logic, evidence = 0, "none found", ""
    return {"score": score, "logic": logic, "evidence": evidence,
            "has_a": has_a, "has_b": has_b, "has_c": has_c}


def score_sl(resume_text):
    f = call_model(PROMPT_SL, resume_text)
    level = f.get("best_level", "NONE")
    activities = f.get("activities", [])
    if level == "MAJOR":
        best = next((a for a in activities if a.get("level") == "MAJOR"), None)
        score = 4 if (best and best.get("explains_development")) else 2
    elif level == "MODERATE": score = 2
    elif level == "MINOR":    score = 0.5
    else:                     score = 0
    return {"score": score, "best_level": level, "activities": activities}


def score_dt(resume_text):
    f = call_model(PROMPT_DT, resume_text)
    level = f.get("level", "NONE")
    if level == "MAJOR":   score = 3.5
    elif level == "MINOR": score = 1.5
    else:                  score = 0
    return {"score": score, "level": level, "evidence": f.get("evidence", "")}


def score_elw(resume_text):
    f = call_model(PROMPT_ELW, resume_text)
    level = f.get("level", "NONE")
    score_map = {
        "OUTSTANDING_MULTIPLE": 4, "OUTSTANDING_ONE": 3,
        "STRONG_MULTIPLE": 2,      "STRONG_ONE": 1,
        "LUKEWARM": 0,             "NONE": 0,
    }
    return {"score": score_map.get(level, 0), "level": level,
            "evidence": f.get("evidence", ""),
            "soft_skill_mentions": f.get("soft_skill_mentions", [])}


def run_layer2(resume_text):
    """Layer 2: LLM extracts facts, Python scores the 7 LLM dimensions."""
    dims = [
        ("SPE", score_spe),
        ("SPO", score_spo),
        ("PLE", score_ple),
        ("PLO", score_plo),
        ("SL",  score_sl),
        ("DT",  score_dt),
        ("ELW", score_elw),
    ]
    results = {}
    for code, fn in dims:
        print(f"  [Layer 2] Scoring {code}...")
        try:
            results[code] = fn(resume_text)
            print(f"    → {results[code]['score']}")
        except Exception as e:
            results[code] = {"score": None, "error": str(e)}
            print(f"    → ERROR: {e}")
    return results


# ═════════════════════════════════════════════════════════════════════════════
# LAYER 3: Agent evaluation
# Each agent runs in two steps:
#   Step A: extract subjective signals from the raw text
#   Step B: combine layer 1+2 scores with step A signals → final judgment, output A/B/C
# ═════════════════════════════════════════════════════════════════════════════

# ── Pyatetsky: Step A — extract signals from raw text ──────────────────────────

PYATETSKY_EXTRACT_SYSTEM = """You are Dr. Dmitri Pyatetsky, a senior ophthalmology residency program director. You are reading a residency application to extract the specific signals YOU care about before making your evaluation.

You care about:
1. TRAJECTORY: Performance going upward, flat, or declining over time?
   Look across: undergrad → early med school → clinical years → research output timing.
   Declining trajectory = red flag. Setback + recovery = resilience.

2. SUPERSTAR SIGNALS: Truly exceptional in one specific domain?
   - Research superstar: multiple first-author papers in top journals, letters praising research specifically
   - Leadership/entrepreneurial superstar: founded real business or directed large-scale program with measurable impact
   - Superstars must still have no evidence of failure elsewhere

3. WORKHORSE SIGNALS: Consistent, reliable, broad achievement across ALL areas throughout?
   Not a single peak — sustained performance.

4. RED FLAGS:
   - Declining grades or engagement
   - Gap years with no explanation
   - Strong CV but weak letters (mismatch)
   - USMLE failure

5. LETTER QUALITY: Do letters unequivocally say "best I've ever trained"? Or strong but generic?"""

PYATETSKY_EXTRACT_USER = """Extract the signals YOU care about from this application. Quote or paraphrase specific content.

Application:
{resume_text}

Output JSON only:
{{
  "trajectory": {{
    "pattern": "upward | flat | declining | unclear",
    "evidence": "<specific examples showing the arc across time>"
  }},
  "superstar_signals": {{
    "research": "<specific evidence of research excellence, or none found>",
    "leadership_entrepreneurial": "<specific evidence, or none found>",
    "is_superstar": <true/false>
  }},
  "workhorse_signals": {{
    "consistent_performance": "<evidence of sustained achievement across all areas>",
    "broad_achievements": "<evidence across academics + research + leadership + service>",
    "is_workhorse": <true/false>
  }},
  "red_flags": ["<list any red flags, empty list if none>"],
  "letter_quality_signals": {{
    "unequivocal_praise": <true/false>,
    "quotes": "<key quotes from letters>",
    "cv_letter_mismatch": <true/false>
  }}
}}"""


# ── Pyatetsky: Step B — make final judgment ────────────────────────────────────

PYATETSKY_JUDGE_SYSTEM = """You are Dr. Dmitri Pyatetsky, a senior ophthalmology residency program director. You have already extracted key signals from the application. Now make your final evaluation using both those signals AND the numeric scores.

CLASSIFICATION:
- WORKHORSE: Consistent high-level performance across ALL dimensions throughout the entire application. Broad achievements. Clear resilience evidence. ~75% of accepted residents.
- SUPERSTAR: Genuinely exceptional in one specific domain AND meets minimum baseline everywhere else. ~25% of accepted residents.
- NOT_QUALIFIED: Multiple zeros in bottom-category dimensions AND weak LLM scores. Filter out.

RECOMMENDATION:
- A: SUPERSTAR classification, OR combined score >= 28 AND no red flags
- B: WORKHORSE with combined score >= 20, OR strong in 2+ dimensions with no major red flags
- C: NOT_QUALIFIED, OR multiple red flags, OR combined score < 15

Your extracted signals can move recommendation up or down one level."""

PYATETSKY_JUDGE_USER = """Make your final evaluation as Dr. Pyatetsky.

LAYER 1 SCORES (Python rules):
{layer1_summary}

LAYER 2 SCORES (LLM scoring):
{layer2_summary}

COMBINED TOTAL: {combined_total}

YOUR EXTRACTED SIGNALS:
{evidence}

Output JSON only:
{{
  "classification": "WORKHORSE | SUPERSTAR | NOT_QUALIFIED",
  "classification_rationale": "<2-3 sentences>",
  "scores_assessment": "<what the numeric scores tell you>",
  "signals_assessment": "<what your extracted signals add beyond the scores>",
  "strengths": ["<top 3 strengths with evidence>"],
  "concerns": ["<concerns, empty list if none>"],
  "filter_out": <true/false>,
  "recommendation": "A | B | C",
  "recommendation_rationale": "<why this recommendation>",
  "committee_note": "<one sentence for the committee>"
}}"""


# ── Mirza: Step A — extract signals from raw text ──────────────────────────────

MIRZA_EXTRACT_SYSTEM = """You are Dr. Mirza, an ophthalmology residency program director. You are reading a residency application to extract the specific signals YOU care about before making your evaluation.

You care about:
1. TEAMWORK SIGNALS: Explicit evidence of working in teams, handling disagreement, lifting others.
   Red flag: every story is about individual achievement with no others.

2. EMPATHY & COMPASSION SIGNALS: Does the applicant describe patients as full human beings?
   Specific patient interactions that changed how they think?
   Red flag: patients appear only as props to explain career choice.

3. COMMUNICATION: Is the writing genuine and specific, or templated and generic?

4. TRAJECTORY: Upward (started modest, got stronger) = highly positive.
   Unrecovered decline = red flag. Setback that was overcome = resilience.

5. LETTER SOFT-SKILL MENTIONS: Do multiple writers independently mention teamwork,
   empathy, compassion, or communication? Corroboration = strong signal.

6. SCHOOL CONTEXT: If not top-25, are they excelling at their school?

7. VOLUNTEERISM: Do they go beyond the required checklist?"""

MIRZA_EXTRACT_USER = """Extract the signals YOU care about from this application. Quote or paraphrase specific content.

Application:
{resume_text}

Output JSON only:
{{
  "teamwork": {{
    "signals": ["<specific examples of teamwork>"],
    "red_flags": ["<concerns>"],
    "rating": "strong | adequate | weak | absent"
  }},
  "empathy_compassion": {{
    "signals": ["<specific patient stories or empathy evidence>"],
    "red_flags": ["<concerns>"],
    "rating": "strong | adequate | weak | absent"
  }},
  "communication": {{
    "essay_voice": "genuine | templated | unclear",
    "evidence": "<what makes it genuine or templated>"
  }},
  "trajectory": {{
    "pattern": "upward | flat | declining | burst_then_absent | unclear",
    "evidence": "<specific examples>",
    "setbacks_and_recovery": "<any setbacks and whether they were overcome>"
  }},
  "letter_soft_skill_mentions": {{
    "mentions": ["<specific soft skills mentioned by letter writers>"],
    "corroboration": "<do multiple writers mention the same quality?>",
    "notable_absences": "<any expected letters missing?>"
  }},
  "school_context": {{
    "top25": <true/false>,
    "excelling_at_school": "<evidence they stand out at their institution>"
  }},
  "volunteerism_beyond_checklist": <true/false>,
  "volunteerism_evidence": "<specific evidence>"
}}"""


# ── Mirza: Step B — make final judgment ────────────────────────────────────────

MIRZA_JUDGE_SYSTEM = """You are Dr. Mirza, an ophthalmology residency program director. You have already extracted soft-skill signals from the application. Now make your final evaluation using both those signals AND the numeric scores.

Your philosophy:
- Every applicant at this stage is smart. Intelligence is a given.
- What separates great physicians: teamwork, communication, compassion, empathy, resilience.
- School quality is a threshold check, not a ranking tool.
- Unrecovered decline = red flag. Setback that was overcome = resilience.

RECOMMENDATION:
- A: Strong soft-skill signals + solid scores, OR exceptional upward trajectory compensating for weaker scores
- B: Adequate soft-skill signals + decent scores, OR strong scores but soft-skill signals unclear
- C: Absent soft-skill signals across the board, OR unrecovered decline, OR multiple red flags"""

MIRZA_JUDGE_USER = """Make your final evaluation as Dr. Mirza.

LAYER 1 SCORES (Python rules):
{layer1_summary}

LAYER 2 SCORES (LLM scoring):
{layer2_summary}

COMBINED TOTAL: {combined_total}

YOUR EXTRACTED SIGNALS:
{evidence}

Output JSON only:
{{
  "soft_skills_summary": {{
    "teamwork_rating": "strong | adequate | weak | absent",
    "empathy_rating": "strong | adequate | weak | absent",
    "communication_rating": "genuine | templated | unclear",
    "overall_soft_skills": "strong | adequate | weak | absent"
  }},
  "trajectory_assessment": "<upward/flat/declining and what it means>",
  "scores_context": "<how do the numeric scores look through your lens?>",
  "character_impression": "<2-3 sentences: who is this person as a human being?>",
  "rubric_blind_spots": "<important things the numeric rubric does not capture>",
  "concerns": ["<list concerns, empty if none>"],
  "filter_out": <true/false>,
  "recommendation": "A | B | C",
  "recommendation_rationale": "<why this recommendation>",
  "gut_reaction": "<one honest sentence>"
}}"""


# ═════════════════════════════════════════════════════════════════════════════
# FORMATTING HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _format_layer1(l1):
    lines = [
        f"  MSQ (Medical School Quality): {l1['MSQ']['score']}/4  [{l1['MSQ']['medical_school']}]",
        f"  MSP (Medical School Performance): {l1['MSP']['score']}/4  [system: {l1['MSP']['grading_system']}]",
        f"  UQ  (Undergrad Quality): {l1['UQ']['score']}/2  [{l1['UQ']['undergraduate']}]",
        f"  UP  (Undergrad Performance): {l1['UP']['score']}/4  [GPA: {l1['UP']['gpa']}]",
        f"  USMLE Step 1: {l1['USMLE']['score']}  [passed: {l1['USMLE']['passed']}, first attempt: {l1['USMLE']['first_attempt']}]",
    ]
    return "\n".join(lines)


def _format_layer2(l2):
    max_scores = {"SPE": 4, "SPO": 4, "PLE": 2, "PLO": 4, "SL": 4, "DT": 4, "ELW": 4}
    lines = [f"  {dim}: {data.get('score', 'N/A')}/{max_scores.get(dim, '?')}"
             for dim, data in l2.items()]
    total = sum(v.get("score", 0) or 0 for v in l2.values()
                if isinstance(v.get("score"), (int, float)))
    lines.append(f"  LLM TOTAL: {round(total, 2)}/26")
    return "\n".join(lines)


def _combined_total(l1, l2):
    l1_num = sum(v.get("score", 0) or 0 for k, v in l1.items()
                 if k != "USMLE" and isinstance(v.get("score"), (int, float)))
    l2_num = sum(v.get("score", 0) or 0 for v in l2.values()
                 if isinstance(v.get("score"), (int, float)))
    return round(l1_num + l2_num, 2)


# ═════════════════════════════════════════════════════════════════════════════
# LAYER 3 RUNNER FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def run_pyatetsky(resume_text, layer1, layer2):
    # Step A: extract signals from raw text
    print("  [Layer 3] Pyatetsky: extracting signals from text...")
    evidence = call_agent(
        PYATETSKY_EXTRACT_SYSTEM,
        PYATETSKY_EXTRACT_USER.format(resume_text=resume_text)
    )
    # Step B: combine scores + signals for final judgment
    print("  [Layer 3] Pyatetsky: making judgment...")
    judgment = call_agent(
        PYATETSKY_JUDGE_SYSTEM,
        PYATETSKY_JUDGE_USER.format(
            layer1_summary=_format_layer1(layer1),
            layer2_summary=_format_layer2(layer2),
            combined_total=_combined_total(layer1, layer2),
            evidence=json.dumps(evidence, indent=2, ensure_ascii=False)
        )
    )
    return {"evidence": evidence, "judgment": judgment}


def run_mirza(resume_text, layer1, layer2):
    # Step A: extract signals from raw text
    print("  [Layer 3] Mirza: extracting signals from text...")
    evidence = call_agent(
        MIRZA_EXTRACT_SYSTEM,
        MIRZA_EXTRACT_USER.format(resume_text=resume_text)
    )
    # Step B: combine scores + signals for final judgment
    print("  [Layer 3] Mirza: making judgment...")
    judgment = call_agent(
        MIRZA_JUDGE_SYSTEM,
        MIRZA_JUDGE_USER.format(
            layer1_summary=_format_layer1(layer1),
            layer2_summary=_format_layer2(layer2),
            combined_total=_combined_total(layer1, layer2),
            evidence=json.dumps(evidence, indent=2, ensure_ascii=False)
        )
    )
    return {"evidence": evidence, "judgment": judgment}


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"Reading: {RESUME_PATH}  |  Model: {MODEL}\n")
    with open(RESUME_PATH, "r", encoding="utf-8") as f:
        resume = f.read()

    # Layer 1
    print("=" * 60)
    print("LAYER 1: Python Rule-Based Scoring")
    print("=" * 60)
    layer1 = run_layer1(resume)
    for dim, data in layer1.items():
        print(f"  {dim}: {data.get('score', 'N/A')}")

    # Layer 2
    print("\n" + "=" * 60)
    print("LAYER 2: LLM Fact Extraction + Python Scoring")
    print("=" * 60)
    layer2 = run_layer2(resume)
    l2_total = sum(v.get("score", 0) or 0 for v in layer2.values()
                   if isinstance(v.get("score"), (int, float)))
    print(f"  LLM Total: {round(l2_total, 2)} / 26")

    # Layer 3
    print("\n" + "=" * 60)
    print("LAYER 3: Agent Evaluation")
    print("=" * 60)
    p_result = run_pyatetsky(resume, layer1, layer2)
    m_result = run_mirza(resume, layer1, layer2)

    p_rec = p_result["judgment"].get("recommendation", "?")
    m_rec = m_result["judgment"].get("recommendation", "?")
    agreement = p_rec == m_rec
    combined = _combined_total(layer1, layer2)

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"\n  Combined Score (L1+L2): {combined}")
    print(f"\n  Dr. Pyatetsky  →  {p_rec}")
    print(f"    Classification : {p_result['judgment'].get('classification', 'N/A')}")
    print(f"    Filter out     : {p_result['judgment'].get('filter_out', False)}")
    print(f"    Committee note : {p_result['judgment'].get('committee_note', '')}")
    print(f"\n  Dr. Mirza      →  {m_rec}")
    ss = m_result["judgment"].get("soft_skills_summary", {})
    print(f"    Teamwork       : {ss.get('teamwork_rating', 'N/A')}")
    print(f"    Empathy        : {ss.get('empathy_rating', 'N/A')}")
    print(f"    Filter out     : {m_result['judgment'].get('filter_out', False)}")
    print(f"    Gut reaction   : {m_result['judgment'].get('gut_reaction', '')}")
    print(f"\n  Agreement       : {'✓ YES' if agreement else '✗ NO — HUMAN REVIEW NEEDED'}")
    if not agreement:
        print(f"  Conflict        : Pyatetsky={p_rec}, Mirza={m_rec}")
    if p_result["judgment"].get("filter_out") or m_result["judgment"].get("filter_out"):
        print(f"  ⚠ At least one agent recommends filtering this applicant out.")

    # Full JSON output
    print("\n" + "=" * 60)
    print("FULL JSON OUTPUT")
    print("=" * 60)
    print(json.dumps({
        "layer1": layer1,
        "layer2": layer2,
        "layer3": {
            "pyatetsky": p_result,
            "mirza": m_result,
            "summary": {
                "combined_score": combined,
                "pyatetsky_recommendation": p_rec,
                "mirza_recommendation": m_rec,
                "agreement": agreement,
                "conflict_note": None if agreement else f"Pyatetsky={p_rec}, Mirza={m_rec} — human review needed",
                "either_filter_out": (
                    p_result["judgment"].get("filter_out", False) or
                    m_result["judgment"].get("filter_out", False)
                ),
            }
        }
    }, indent=2, ensure_ascii=False))
