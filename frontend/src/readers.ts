export type ReaderDef = {
  id: string
  short: string
  label: string
  hint: string
  reads: string
  looksFor: string
  returns: string
  detail: string
}

export const READERS: ReaderDef[] = [
  {
    id: 'statement',
    short: 'Statement',
    label: 'Personal statement',
    hint: 'Why ophthalmology',
    reads: 'The personal statement only.',
    looksFor:
      'A specific, credible reason for ophthalmology — lived clinical moments, sustained interest, and a path that fits residency, not generic medicine language.',
    returns: 'Green, yellow, or red, plus short paragraph snippets quoted from the statement.',
    detail:
      'This sub-agent ignores letters, research lists, and scores. It asks whether the statement itself would support inviting the applicant to interview, and it must cite continuous snippets from that section.',
  },
  {
    id: 'letters',
    short: 'Letters',
    label: 'Letters of recommendation',
    hint: 'What referees say',
    reads: 'Letters of recommendation and referee comments.',
    looksFor:
      'Concrete evidence of clinical judgment, technical skill, teamwork, and reliability — not empty praise or name-dropping alone.',
    returns: 'A color for the letter file, with cited sentences from the referees.',
    detail:
      'This sub-agent does not read the personal statement as its main source. It weighs whether the letters give faculty something specific to trust, and pulls short quoted fragments as proof.',
  },
  {
    id: 'research',
    short: 'Research',
    label: 'Research',
    hint: 'Their own role',
    reads: 'Research experiences, publications, posters, and project descriptions.',
    looksFor:
      'The applicant’s own role — study design, analysis, writing, presenting — not a bare list of titles or co-authorships.',
    returns: 'A color for research depth, with snippets that show what they actually did.',
    detail:
      'This sub-agent checks for ownership of the work. A long CV line without a described contribution tends toward yellow; clear methods or leadership in a project can support green.',
  },
  {
    id: 'clinical',
    short: 'Clinical',
    label: 'Clinical record',
    hint: 'Clerkships and MSPE',
    reads: 'Clerkship narratives, MSPE / Dean’s letter comments, and ophthalmology rotations when present.',
    looksFor:
      'How the applicant performed with patients and teams — preparation, judgment, communication, and any eye-related rotations.',
    returns: 'A color for the clinical file, citing MSPE or clerkship language.',
    detail:
      'This sub-agent stays on clinical narrative. It does not turn grades into points. Missing clinical text is yellow with a note that the section was not found.',
  },
  {
    id: 'commitment',
    short: 'Commitment',
    label: 'Ophthalmology commitment',
    hint: 'Time in the field',
    reads: 'Electives, mentors, shadowing, community vision work, and other longitudinal eye exposure outside the statement alone.',
    looksFor:
      'Repeated contact with ophthalmology over time — not a single elective mentioned once.',
    returns: 'A color for sustained commitment, cited from activities and experiences in the packet.',
    detail:
      'This sub-agent asks whether ophthalmology shows up as a pattern in the file. It is optional by default and pairs well with Statement when faculty want a second look at specialty fit.',
  },
]

export const DEFAULT_READERS = ['statement', 'letters', 'research', 'clinical']

export function readerById(id: string): ReaderDef | undefined {
  return READERS.find((reader) => reader.id === id)
}
