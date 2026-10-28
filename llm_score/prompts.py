"""LLM prompt templates for MSAI master's application screening.

JSON keys are unchanged so the API, Excel writer, and UI keep parsing the same
fields. The meaning of each key is the MSAI rubric below, not the old
ophthalmology residency rubric.
"""

BRIEF_PROMPT = """You are preparing a one-page briefing for faculty screening Northwestern's Master of Science in Artificial Intelligence (MSAI) applications.
Read the application excerpt below. Extract facts and short summaries only.
Do NOT assign rubric scores or recommendations.
Do NOT infer race, ethnicity, gender, age, disability, religion, or national origin, and do not treat those traits as strengths or weaknesses.

For each section:
- Write a 2-4 sentence summary for busy faculty.
- List concrete evidence (short quotes or paraphrases with section names).
- If information is missing, say "Not found in application" — do not infer.

The application is a master's packet: statement of purpose, education, research, projects, experience, and letters. There is no residency or clinical training to extract.

Application excerpt:
{application_text}

Output JSON only with this exact structure:
{{
  "scientific_pursuits_education": {{
    "summary": "<technical preparation and research/engineering experience>",
    "md_phd": <true if a research master's or PhD is already completed, else false>,
    "research_roles": [{{"role": "<string>", "duration": "<string>"}}],
    "evidence": ["<string>"]
  }},
  "scientific_pursuits_output": {{
    "summary": "<papers, talks, and substantial technical artifacts>",
    "first_author_pubs": <int>,
    "non_first_author_pubs": <int>,
    "oral_presentations": <int>,
    "poster_presentations": <int>,
    "highlights": ["<string>"]
  }},
  "professional_leadership_education": {{
    "summary": "<formal CS, math, statistics, or equivalent quantitative preparation>",
    "mba_mph_or_equivalent": <true if a completed quantitative or computing degree, or a clearly listed upper-level ML/math sequence, is present>,
    "evidence": ["<string>"]
  }},
  "professional_leadership_output": {{
    "summary": "<technical leadership, products, or tools others used>",
    "for_profit_or_director_roles": ["<founded, led, or directed technical work>"],
    "large_scale_qi_or_public_health": ["<large collaborative technical or community efforts, else empty>"],
    "technical_health_tools": ["<models, codebases, datasets, or products the applicant built>"],
    "evidence": ["<string>"]
  }},
  "social_leadership_service": {{
    "summary": "<teaching, mentoring, student orgs, and service>",
    "notable_activities": [{{"activity": "<string>", "scope": "<local|national|other>"}}],
    "evidence": ["<string>"]
  }},
  "resilience": {{
    "summary": "<what the statement of purpose claims about trajectory and program fit>",
    "challenges_described": ["<specific challenges only if the applicant states them>"],
    "growth_connection": "<how the statement links past work to MSAI goals, or empty>",
    "evidence": ["<string>"]
  }},
  "endorsements": {{
    "summary": "<what letters actually say about technical ability and readiness>",
    "letter_count": <int>,
    "standout_quotes": ["<string>"],
    "overall_tone": "<outstanding|strong|mixed|lukewarm|not_found>"
  }}
}}"""

_RUBRIC_SCORING_RULES = """
RUBRIC — Northwestern MSAI master's screening. Use ONLY these allowed scores.

Technical preparation (scientific_pursuits_education):
  4 = completed research master's or PhD, or at least 2 years of full-time research or ML/engineering work beyond coursework
  2 = at least 2 years of dedicated research, RA, or ML engineering (coursework alone does not count)
  1 = at least 1 year of dedicated research or a substantial technical internship
  0 = otherwise

Research and project output (scientific_pursuits_output):
  4 = first-author peer-reviewed paper, or a lead technical artifact with evidence others used it (shipped system, maintained open-source project, or public thesis with a clear individual contribution)
  3 = co-authored peer-reviewed paper, a selective oral presentation, or several substantial projects with a clear individual contribution
  2 = one substantial independent project (capstone, thesis, or internship deliverable) with technical depth
  1 = coursework projects only, or a poster without a paper
  0.5 = a poster or workshop abstract only, with little description of the applicant's role
  0 = none of the above

Formal quantitative preparation (professional_leadership_education):
  2 = degree in CS, statistics, mathematics, EE, or a closely related quantitative field, OR an explicit upper-level sequence in linear algebra, probability, algorithms, and machine learning with grades or course names listed
  0 = otherwise

Technical leadership (professional_leadership_output):
  4 = founded or led a technical product, research effort, or team AND reflects on what they learned
  2 = led a substantial project or team, or built a tool others used, without that reflection
  0 = otherwise

Collaboration and service (social_leadership):
  4 = sustained leadership (organization, teaching, mentoring, or community) with a short account of what they learned
  2 = consistent contribution (TA, officer, lab mentor, volunteer)
  0.5 = a minor or one-off role
  0 = none

Statement of purpose and trajectory (resilience):
  3.5 = the statement makes a specific, credible case for this MSAI program, tied to past work and concrete goals
  1.5 = goals are clear but program fit is generic, or the path is described without specifics
  0 = vague, missing, or not connected to the program

Letters (endorsement):
  4 = unequivocally outstanding across more than one letter, with specific technical examples
  3 = unequivocally outstanding in one letter
  2 = very strong across more than one letter
  1 = very strong in one letter
  0 = lukewarm, mixed, generic, or absent

Interview recommendation (reviewer_recommendation), letter grade only:
  A = interview — technical preparation and program fit are both strong
  B = consider — meets a plausible baseline and needs a human look
  C = do not interview unless a reviewer has a specific reason to override

Score only what the packet states. Do not reward or penalize demographics. Do not invent publications, grades, or letter quotes.
"""

DOC_A_PROMPT = (
    """You are Reviewer A, an independent screener for Northwestern's MSAI master's program.
You read for technical readiness: preparation, research and project output, quantitative background, and whether letters give specific evidence of technical ability.
Be conservative: award a score only when the criterion is clearly met.

You will receive a factual briefing and the application excerpt.
Use both, but check claims against the excerpt. Do not copy the briefing blindly.
Ignore clinical, USMLE, and residency framing. This is a master's application.

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
  "summary": "<your reviewer summary as Reviewer A>",
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
    """You are Reviewer B, an independent screener for Northwestern's MSAI master's program.
You read for program fit: the statement of purpose, trajectory, collaboration, and whether the applicant has made a specific case for this degree.
You still apply the same rubric. Weight the statement, trajectory, and collaboration more heavily than raw publication counts.
Be conservative: award a score only when the criterion is clearly met.

You review independently from Reviewer A. You will receive the same factual briefing and application excerpt.
Use both, but check claims against the excerpt. Do not copy the briefing blindly.
Ignore clinical, USMLE, and residency framing. This is a master's application.

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
  "summary": "<your reviewer summary as Reviewer B>",
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

DOC_C_PROMPT = (
    """You are Reviewer C, an independent screener for Northwestern's MSAI master's program.
You read for academic readiness. Judge whether the coursework and grades can support graduate machine learning work, and whether the letters corroborate the statement of purpose.
Weight formal quantitative preparation and consistency between the written claims and the record.
Be conservative: award a score only when the criterion is clearly met.

You review independently from Reviewer A and Reviewer B. You will receive the same factual briefing and application excerpt.
Use both, but check claims against the excerpt. Do not copy the briefing blindly.
Ignore clinical, USMLE, and residency framing. This is a master's application.

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
  "summary": "<your reviewer summary as Reviewer C>",
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
