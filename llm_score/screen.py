import ollama
import json

RESUME_PATH = "output.txt"
MODEL = "qwen3:14b"

def call_model(prompt: str, resume_text: str) -> dict:
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt.format(resume_text=resume_text)}],
        options={"temperature": 0.1},
        think=True,
    )
    raw = response["message"]["content"].strip()
    try:
        return json.loads(raw[raw.find("{"):raw.rfind("}")+1])
    except:
        return {}


# ── SPE: Scientific Pursuits - Education/Experience ───────────────────────────
PROMPT_SPE = """Read this medical residency application. Extract ONLY facts. Do not score.

1. Does the applicant explicitly hold BOTH an MD AND a PhD as two separate degrees?
   - "MD/PhD" listed under Education = YES
   - MD thesis, MD with research component = NO

2. List every dedicated research role with duration from Employment and Research Activities.
   Convert to decimal years (12 weeks=0.25, 6 months=0.5, 1 year=1.0).
   Exclude coursework and clinical rotations.

Resume:
{resume_text}

Output JSON only:
{{"md_phd": <true/false>, "research_roles": [{{"role": "<name>", "duration_text": "<text>", "duration_years": <decimal>}}]}}"""

def score_spe(resume_text):
    f = call_model(PROMPT_SPE, resume_text)
    md_phd = f.get("md_phd", False)
    roles = f.get("research_roles", [])
    total = sum(r.get("duration_years", 0) for r in roles)
    if md_phd: score = 4
    elif total >= 2.0: score = 2
    elif total >= 1.0: score = 1
    else: score = 0
    return {"score": score, "md_phd": md_phd, "total_years": round(total, 2), "roles": roles}


# ── SPO: Scientific Pursuits - Output ────────────────────────────────────────
PROMPT_SPO = """Read this medical residency application. Extract ONLY facts. Do not score.

Count the applicant's publications and presentations:
1. Lead/first-author publications in peer-reviewed journals (count only)
2. Non-first-author publications in peer-reviewed journals (count only)
3. Oral presentations at national/international conferences like ARVO (count only)
4. Poster presentations at national conferences (count only)

Only count items explicitly listed. Do not infer or assume.

Resume:
{resume_text}

Output JSON only:
{{"first_author_pubs": <int>, "non_first_author_pubs": <int>, "oral_presentations": <int>, "poster_presentations": <int>}}"""

def score_spo(resume_text):
    f = call_model(PROMPT_SPO, resume_text)
    fa = f.get("first_author_pubs", 0)
    nfa = f.get("non_first_author_pubs", 0)
    oral = f.get("oral_presentations", 0)
    poster = f.get("poster_presentations", 0)
    if fa >= 5: score = 4
    elif fa >= 3: score = 3
    elif fa >= 1: score = 2
    elif nfa >= 1 or oral >= 1: score = 1
    elif poster >= 1: score = 0.5
    else: score = 0
    return {"score": score, "first_author": fa, "non_first_author": nfa, "oral": oral, "poster": poster}


# ── PLE: Professional Leadership - Education ──────────────────────────────────
PROMPT_PLE = """Read this medical residency application. Answer ONE question only.

QUESTION: Does the applicant hold an MBA, MPH, Masters in Quality & Safety, or equivalent formal leadership/business/public health degree?
- Must be a completed or in-progress formal graduate degree
- MD, PhD, and standard medical degrees do NOT count
- Answer false if not 100% certain

Resume:
{resume_text}

Output JSON only:
{{"answer": <true/false>, "evidence": "<exact quote or empty>"}}"""

def score_ple(resume_text):
    f = call_model(PROMPT_PLE, resume_text)
    score = 2 if f.get("answer", False) else 0
    return {"score": score, "found": f.get("answer", False), "evidence": f.get("evidence", "")}


# ── PLO: Professional Leadership - Output ─────────────────────────────────────
PROMPT_PLO_A = """Read this resume. Answer ONE question only.

QUESTION: Did this applicant found or lead a FOR-PROFIT business, OR hold a formal Director title at a company or hospital department?
- FOR-PROFIT business = commercial venture, startup, company. NOT student clubs or nonprofits.
- Director = formal paid leadership title. NOT student committee roles.
- Research, publications, mentoring, volunteering do NOT count.
- Answer false if not 100% certain.

Resume:
{resume_text}

Output JSON only:
{{"answer": <true/false>, "evidence": "<exact quote or empty>"}}"""

PROMPT_PLO_B = """Read this resume. Answer ONE question only.

QUESTION: Did this applicant personally design AND lead a large-scale public health or quality improvement program affecting hundreds or thousands of people?
- Must be created and directed by them, not just participated in.
- Tutoring, yoga teaching, vision screening, health fair volunteering do NOT qualify.
- Research and publications do NOT count.
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

def score_plo(resume_text):
    a = call_model(PROMPT_PLO_A, resume_text)
    b = call_model(PROMPT_PLO_B, resume_text)
    c = call_model(PROMPT_PLO_C, resume_text)
    has_a, has_b, has_c = a.get("answer", False), b.get("answer", False), c.get("answer", False)
    if has_a or has_b:
        rel = call_model(PROMPT_PLO_REL, resume_text)
        has_rel = rel.get("answer", False)
        score = 4 if has_rel else 2
        logic = "A/B + relevance" if has_rel else "A/B no relevance → 2"
    elif has_c:
        score, logic = 2, "TYPE_C"
    else:
        score, logic = 0, "none found"
    return {"score": score, "logic": logic, "has_a": has_a, "has_b": has_b, "has_c": has_c}


# ── SL: Social Leadership & Service ──────────────────────────────────────────
PROMPT_SL = """Read this medical residency application. Extract ONLY facts. Do not score.

Find the applicant's leadership and service activities. For each one, classify as:
- MAJOR: Founded or held major post in a NATIONAL organization, OR president of medical school class. Must explain how this shaped their leadership development.
- MODERATE: Founded or held top post in a LOCAL chapter of national org, local committee, or interest group.
- MINOR: Minor elected position (VP, Treasurer), volunteer, tutor, mentor, admissions committee member, Big Sib, etc.
- NONE: No leadership activities.

Resume:
{resume_text}

Output JSON only:
{{"best_level": "<MAJOR/MODERATE/MINOR/NONE>", "activities": [{{"description": "<one sentence>", "level": "<MAJOR/MODERATE/MINOR/NONE>", "explains_development": <true/false>}}]}}"""

def score_sl(resume_text):
    f = call_model(PROMPT_SL, resume_text)
    level = f.get("best_level", "NONE")
    activities = f.get("activities", [])
    if level == "MAJOR":
        best = next((a for a in activities if a.get("level") == "MAJOR"), None)
        score = 4 if (best and best.get("explains_development")) else 2
    elif level == "MODERATE": score = 2
    elif level == "MINOR": score = 0.5
    else: score = 0
    return {"score": score, "best_level": level, "activities": activities}


# ── DT: Resilience / Grit / Distance Travelled ───────────────────────────────
PROMPT_DT = """Read this medical residency application. Focus ONLY on the Personal Statement and essays.

QUESTION: Does the applicant make a meaningful and convincing argument about overcoming a specific challenge that shaped their growth?

Rules:
- Only count challenges explicitly described AND connected to personal/professional growth
- Do NOT make assumptions. If it's not clearly stated, it doesn't count.
- Classify as:
  MAJOR: Overcame a major challenge not experienced by most people. Getting to where they are is itself a noteworthy accomplishment.
  MINOR: Overcame a significant but common challenge. Clearly explained how it shaped their growth.
  NONE: Not discussed, or argument is not convincing.

Resume:
{resume_text}

Output JSON only:
{{"level": "<MAJOR/MINOR/NONE>", "evidence": "<exact quote from essay if applicable, otherwise empty>"}}"""

def score_dt(resume_text):
    f = call_model(PROMPT_DT, resume_text)
    level = f.get("level", "NONE")
    if level == "MAJOR": score = 3.5
    elif level == "MINOR": score = 1.5
    else: score = 0
    return {"score": score, "level": level, "evidence": f.get("evidence", "")}


# ── ELW: Endorsement by Letter Writers ───────────────────────────────────────
PROMPT_ELW = """Read this medical residency application. Focus on letters of recommendation or descriptions of endorsements.

Classify the overall endorsement strength:
- OUTSTANDING_MULTIPLE: Unequivocally outstanding endorsement by MULTIPLE letter writers
- OUTSTANDING_ONE: Unequivocally outstanding endorsement by ONE letter writer
- STRONG_MULTIPLE: Very strong (but not exceptional) endorsement by MULTIPLE letters
- STRONG_ONE: Very strong (but not exceptional) endorsement by ONE letter
- LUKEWARM: Lukewarm or mixed recommendation
- NONE: No letters found

"Unequivocally outstanding" means the writer clearly states this is one of the best candidates they have ever trained/worked with.

Resume:
{resume_text}

Output JSON only:
{{"level": "<OUTSTANDING_MULTIPLE/OUTSTANDING_ONE/STRONG_MULTIPLE/STRONG_ONE/LUKEWARM/NONE>", "evidence": "<exact quote or empty>"}}"""

def score_elw(resume_text):
    f = call_model(PROMPT_ELW, resume_text)
    level = f.get("level", "NONE")
    score_map = {
        "OUTSTANDING_MULTIPLE": 4,
        "OUTSTANDING_ONE": 3,
        "STRONG_MULTIPLE": 2,
        "STRONG_ONE": 1,
        "LUKEWARM": 0,
        "NONE": 0,
    }
    score = score_map.get(level, 0)
    return {"score": score, "level": level, "evidence": f.get("evidence", "")}


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Reading: {RESUME_PATH}  |  Model: {MODEL}\n")
    with open(RESUME_PATH, "r", encoding="utf-8") as f:
        resume = f.read()

    results = {}

    dims = [
        ("SPE", "Scientific Pursuits - Education/Experience", score_spe),
        ("SPO", "Scientific Pursuits - Output",               score_spo),
        ("PLE", "Professional Leadership - Education",        score_ple),
        ("PLO", "Professional Leadership - Output",           score_plo),
        ("SL",  "Social Leadership & Service",                score_sl),
        ("DT",  "Resilience / Grit / Distance Travelled",     score_dt),
        ("ELW", "Endorsement by Letter Writers",              score_elw),
    ]

    for code, label, fn in dims:
        print(f"Scoring {code}...")
        try:
            r = fn(resume)
            results[code] = r
            print(f"  → Score: {r['score']}")
        except Exception as e:
            results[code] = {"score": None, "error": str(e)}
            print(f"  → ERROR: {e}")

    print("\n" + "=" * 55)
    print("FINAL SCORES SUMMARY")
    print("=" * 55)
    max_scores = {"SPE": 4, "SPO": 4, "PLE": 2, "PLO": 4, "SL": 4, "DT": 4, "ELW": 4}
    total = 0
    for code, label, _ in dims:
        r = results[code]
        score = r.get("score")
        mx = max_scores[code]
        print(f"  {code:4s}  {label:45s}  {score} / {mx}")
        if score is not None:
            total += score
    print(f"\n  TOTAL: {total} / 26")
    print("\nDetailed results:")
    print(json.dumps(results, indent=2, ensure_ascii=False))
