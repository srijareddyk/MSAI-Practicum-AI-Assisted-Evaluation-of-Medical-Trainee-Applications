export type AnalysisMode = 'full' | 'briefing' | 'step1'

export type JobStatus = 'running' | 'completed' | 'failed'

export interface HealthResponse {
  status: string
  template_present: boolean
  default_model: string
  ollama: {
    ok: boolean
    available: boolean
    models?: string[]
    error?: string
    requested: string
  }
}

export interface Step1Scores {
  medical_school_quality: number | null
  medical_school_performance: number | null
  undergraduate_quality: number | null
  undergraduate_performance: number | null
  usmle_step1: string | null
}

export interface ExtractedFacts {
  medical_school: string | null
  undergraduate_institution: string | null
  undergraduate_cum_gpa: number | null
  usmle_step1_times_taken: number | null
  usmle_step1_result: string | null
  notes: string[]
}

export interface AgentReview {
  summary: string | null
  scores: Record<string, number | string | null>
  rationale: Record<string, string>
  error: string | null
}

export interface ApplicantResult {
  file: string
  applicant_name: string | null
  stripped_chars: number
  briefing: Record<string, unknown> | null
  doc_a: AgentReview | null
  doc_b: AgentReview | null
  facts: ExtractedFacts
  scores: Step1Scores
  markdown_files: Record<string, string>
}

export interface JobProgress {
  index?: number
  total?: number
  file?: string
  applicant?: string
}

export interface Job {
  id: string
  status: JobStatus
  stage: string
  progress: JobProgress
  mode: AnalysisMode
  model: string
  files: string[]
  applicants: ApplicantResult[]
  excel_name: string | null
  error: string | null
  created_at: string
  updated_at: string
}
