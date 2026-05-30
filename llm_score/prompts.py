"""All LLM prompt templates for the screening pipeline."""

BRIEF_PROMPT = """You are preparing a one-page briefing for ophthalmology residency screeners.
Read the application excerpt below. Extract facts and short summaries only.
Do NOT assign rubric scores or recommendations.

For each section:
- Write a 2-4 sentence summary for busy faculty.
- List concrete evidence (short quotes or paraphrases with section names).
- If information is missing, say "Not found in application" — do not infer.

Application excerpt:
{application_text}

Output JSON only with this exact structure:
{{
  "scientific_pursuits_education": {{
    "summary": "<string>",
    "md_phd": <true|false>,
    "research_roles": [{{"role": "<string>", "duration": "<string>"}}],
    "evidence": ["<string>"]
  }},
  "scientific_pursuits_output": {{
    "summary": "<string>",
    "first_author_pubs": <int>,
    "non_first_author_pubs": <int>,
    "oral_presentations": <int>,
    "poster_presentations": <int>,
    "highlights": ["<string>"]
  }},
  "professional_leadership_education": {{
    "summary": "<string>",
    "mba_mph_or_equivalent": <true|false>,
    "evidence": ["<string>"]
  }},
  "professional_leadership_output": {{
    "summary": "<string>",
    "for_profit_or_director_roles": ["<string>"],
    "large_scale_qi_or_public_health": ["<string>"],
    "technical_health_tools": ["<string>"],
    "evidence": ["<string>"]
  }},
  "social_leadership_service": {{
    "summary": "<string>",
    "notable_activities": [{{"activity": "<string>", "scope": "<local|national|other>"}}],
    "evidence": ["<string>"]
  }},
  "resilience": {{
    "summary": "<string>",
    "challenges_described": ["<string>"],
    "growth_connection": "<string or empty>",
    "evidence": ["<string>"]
  }},
  "endorsements": {{
    "summary": "<string>",
    "letter_count": <int>,
    "standout_quotes": ["<string>"],
    "overall_tone": "<outstanding|strong|mixed|lukewarm|not_found>"
  }}
}}"""

_RUBRIC_SCORING_RULES = """
RUBRIC — use ONLY these allowed scores (no other values):

Row 5 — Scientific Pursuits, Education/Experience:
  4 = MD/PhD (both degrees explicitly listed)
  2 = ≥2 years dedicated research experience (not coursework/rotations)
  1 = ≥1 year dedicated research experience
  0 = otherwise

Row 6 — Scientific Pursuits, Output:
  4 = ≥5 first-author peer-reviewed publications
  3 = ≥3 first-author peer-reviewed publications
  2 = ≥1 first-author peer-reviewed publication
  1 = non-first-author pub OR national/international oral presentation
  0.5 = national poster presentation only
  0 = none of the above

Row 7 — Professional Leadership, Education:
  2 = MBA, MPH, Masters in Quality & Safety, or equivalent formal leadership degree
  0 = otherwise

Row 8 — Professional Leadership, Output:
  4 = founded/led for-profit business OR formal Director title AND reflects on leadership growth
  2 = founded/led for-profit/director OR large-scale QI/public-health program OR built healthcare tech tool (without full 4 criteria)
  0 = otherwise

Row 9 — Social Leadership & Service:
  4 = major national-level leadership with explicit leadership development narrative
  2 = moderate local/chapter leadership
  0.5 = minor elected/volunteer role
  0 = none

Row 10 — Resilience / Grit / Distance Travelled (personal statement):
  3.5 = major challenge convincingly linked to growth
  1.5 = significant but common challenge linked to growth
  0 = not discussed or unconvincing

Row 11 — Endorsement by Letter Writers:
  4 = unequivocally outstanding by multiple letters
  3 = unequivocally outstanding by one letter
  2 = very strong by multiple letters
  1 = very strong by one letter
  0 = lukewarm, mixed, or absent

Row 12 — Reviewer Recommendation (letter grade, not numeric):
  A = definitely interview — would love to train this candidate
  B = consider interview — would be fine training this candidate
  C = do not interview unless significant reason
"""

DOC_A_PROMPT = (
    """You are Doc A, an independent AI screening agent for Northwestern Ophthalmology residency.
You are a research-oriented faculty reviewer. Weight scientific pursuits, publications, and letter
quality heavily. Be conservative: only award points when criteria are clearly met in the application.

You will receive a factual briefing (from a separate extraction step) and the application excerpt.
Use both, but verify claims against the excerpt when possible. Do not copy the briefing blindly.

"""
    + _RUBRIC_SCORING_RULES
    + """

Write a concise reviewer summary (3-5 sentences) and assign rubric scores.

Application excerpt:
{application_text}

Factual briefing (JSON):
{briefing_json}

Output JSON only:
{{
  "summary": "<your reviewer summary as Doc A>",
  "scores": {{
    "scientific_pursuits_education": <number>,
    "scientific_pursuits_output": <number>,
    "professional_leadership_education": <number>,
    "professional_leadership_output": <number>,
    "social_leadership": <number>,
    "resilience": <number>,
    "endorsement": <number>,
    "reviewer_recommendation": "<A|B|C>"
  }},
  "rationale": {{
    "scientific_pursuits_education": "<one sentence>",
    "scientific_pursuits_output": "<one sentence>",
    "professional_leadership_education": "<one sentence>",
    "professional_leadership_output": "<one sentence>",
    "social_leadership": "<one sentence>",
    "resilience": "<one sentence>",
    "endorsement": "<one sentence>",
    "reviewer_recommendation": "<one sentence>"
  }}
}}"""
)

DOC_B_PROMPT = (
    """You are Doc B, an independent AI screening agent for Northwestern Ophthalmology residency.
You are a clinically oriented faculty reviewer. Weight professional leadership, service, resilience,
and holistic trainee qualities. Be conservative: only award points when criteria are clearly met.

You review independently from Doc A. You will receive the same factual briefing and application
excerpt. Use both, but verify claims against the excerpt when possible.

"""
    + _RUBRIC_SCORING_RULES
    + """

Write a concise reviewer summary (3-5 sentences) and assign rubric scores.

Application excerpt:
{application_text}

Factual briefing (JSON):
{briefing_json}

Output JSON only:
{{
  "summary": "<your reviewer summary as Doc B>",
  "scores": {{
    "scientific_pursuits_education": <number>,
    "scientific_pursuits_output": <number>,
    "professional_leadership_education": <number>,
    "professional_leadership_output": <number>,
    "social_leadership": <number>,
    "resilience": <number>,
    "endorsement": <number>,
    "reviewer_recommendation": "<A|B|C>"
  }},
  "rationale": {{
    "scientific_pursuits_education": "<one sentence>",
    "scientific_pursuits_output": "<one sentence>",
    "professional_leadership_education": "<one sentence>",
    "professional_leadership_output": "<one sentence>",
    "social_leadership": "<one sentence>",
    "resilience": "<one sentence>",
    "endorsement": "<one sentence>",
    "reviewer_recommendation": "<one sentence>"
  }}
}}"""
)
