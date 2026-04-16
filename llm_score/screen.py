import ollama
import json

RESUME_PATH = "output.txt"
MODEL = "qwen3:14b"

PROMPT_PLO = """You are a strict medical residency application reviewer. Read the resume carefully and reason step by step.

## Your task
Determine if the applicant has any of the following. Read each definition carefully.

---
CRITERION A — For-profit business founder or company/department director:
The applicant must have:
- Founded or led a FOR-PROFIT commercial business or startup, OR
- Held a formal paid title of Director at a company or hospital department

This does NOT include:
- Student organizations or clubs (even if they "founded" them)
- Volunteer groups or nonprofits
- Committee roles (wellness chair, social chair, admissions committee)
- Podcast involvement or social media
- Research or academic roles

---
CRITERION B — Large-scale public health or QI program director:
The applicant must have:
- Personally designed AND directed a public health or quality improvement program
- That program must have affected hundreds or thousands of people at an institutional or population level

This does NOT include:
- Tutoring individual students
- Teaching yoga or tennis to small groups
- Volunteering at health fairs or vision screening events
- Participating in someone else's program

---
CRITERION C — Built a technical product:
The applicant must have:
- Personally built a software app, algorithm, database, or technical tool
- For use in healthcare, public health, or medical efficiency

This does NOT include:
- Creating podcast content or social media posts
- Organizing events or meetings
- Serving on a committee
- Educational content creation without a technical product

---

## Instructions
For EACH criterion, reason through it step by step:
1. List any activities from the resume that COULD be relevant
2. Apply the definition strictly
3. State your conclusion (yes or no)

Then give your final answers.

## Resume
{resume_text}

## Output - JSON only, no other text:
{{
  "criterion_a": {{
    "reasoning": "<step by step reasoning>",
    "answer": <true or false>,
    "evidence": "<exact quote if true, empty string if false>"
  }},
  "criterion_b": {{
    "reasoning": "<step by step reasoning>",
    "answer": <true or false>,
    "evidence": "<exact quote if true, empty string if false>"
  }},
  "criterion_c": {{
    "reasoning": "<step by step reasoning>",
    "answer": <true or false>,
    "evidence": "<exact quote if true, empty string if false>"
  }}
}}
"""

PROMPT_RELEVANCE = """Read this resume. Answer one question only.

QUESTION: Does the applicant explicitly reflect on what they personally LEARNED or how a specific leadership or entrepreneurial experience (not research, not clinical work) shaped their identity or career goals?

The reflection must:
- Be written in first person ("I learned...", "This taught me...", "I grew...")
- Refer specifically to a leadership or entrepreneurial activity
- Go beyond simply describing what they did

This does NOT count:
- Describing research experience
- Describing clinical rotations
- Describing mentoring or teaching activities

Resume:
{resume_text}

Output - JSON only:
{{"answer": <true or false>, "evidence": "<exact quote if true, empty string if false>"}}
"""

def call_model(prompt: str, resume_text: str) -> dict:
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt.format(resume_text=resume_text)}],
        options={"temperature": 0.1},
        think=False,
    )
    raw = response["message"]["content"].strip()
    return json.loads(raw[raw.find("{"):raw.rfind("}")+1])

def score_plo(resume_text: str) -> dict:
    facts = call_model(PROMPT_PLO, resume_text)

    has_a = facts["criterion_a"]["answer"]
    has_b = facts["criterion_b"]["answer"]
    has_c = facts["criterion_c"]["answer"]

    if has_a or has_b:
        rel = call_model(PROMPT_RELEVANCE, resume_text)
        has_relevance = rel["answer"]
        ev_r = rel.get("evidence", "")
        if has_relevance:
            score, logic = 4, "A/B + relevance explained"
        else:
            score, logic = 2, "A/B found but relevance NOT explained -> 2"
    elif has_c:
        score, logic = 2, "TYPE_C only"
        has_relevance, ev_r = False, ""
    else:
        score, logic = 0, "none found"
        has_relevance, ev_r = False, ""

    return {
        "score": score, "logic": logic,
        "criterion_a": facts["criterion_a"],
        "criterion_b": facts["criterion_b"],
        "criterion_c": facts["criterion_c"],
        "has_relevance": has_relevance if (has_a or has_b) else None,
        "ev_r": ev_r,
    }

if __name__ == "__main__":
    print(f"Reading: {RESUME_PATH}  |  Model: {MODEL}\n")
    with open(RESUME_PATH, "r", encoding="utf-8") as f:
        resume_text = f.read()

    print("=" * 55)
    print("DIMENSION 2: Professional Leadership Output")
    print("=" * 55)
    result = score_plo(resume_text)

    for key, label in [("criterion_a", "A - For-profit/Director"),
                       ("criterion_b", "B - Large-scale QI/Public health"),
                       ("criterion_c", "C - Technical product")]:
        c = result[key]
        print(f"\n[{label}]")
        print(f"  Reasoning : {c['reasoning']}")
        print(f"  Answer    : {c['answer']}")
        if c["evidence"]:
            print(f"  Evidence  : {c['evidence'][:120]}")

    if result["has_relevance"] is not None:
        print(f"\n[Relevance explained] : {result['has_relevance']}")
        if result["ev_r"]:
            print(f"  Evidence  : {result['ev_r'][:120]}")

    print(f"\nScore  : {result['score']} / 4")
    print(f"Logic  : {result['logic']}")
