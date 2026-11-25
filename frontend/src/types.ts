export type AnalysisMode = 'full' | 'briefing' | 'step1'

export type JobStatus = 'running' | 'completed' | 'failed'

export interface HealthResponse {
  status: string
  template_present: boolean
  default_model: string
  provider?: string
  ollama: {
    provider?: string
    ok: boolean
    available: boolean
    models?: string[]
    error?: string
    requested: string
  }
}

export interface Step1Scores {
  undergraduate_quality: number | null
  undergraduate_performance: number | null
}

export interface ExtractedFacts {
  undergraduate_institution: string | null
  undergraduate_cum_gpa: number | null
  work_experience: string | null
  notes: string[]
}

export interface AgentReview {
  summary: string | null
  scores: Record<string, number | string | null>
  rationale: Record<string, string>
  error: string | null
}

export type Opinion = 'green' | 'yellow' | 'red' | 'split'

export interface ComponentRead {
  id: string
  title: string
  short: string
  opinion: Opinion | null
  /** 10–15 word "why this color", shown on hover. */
  reason?: string | null
  headline: string | null
  evidence: string[]
  concern: string | null
  error: string | null
}

export interface CombinedRead {
  opinion: Opinion
  summary: string
}

export interface ApplicantResult {
  file: string
  applicant_name: string | null
  stripped_chars: number
  briefing: Record<string, unknown> | null
  doc_a: AgentReview | null
  doc_b: AgentReview | null
  doc_c: AgentReview | null
  facts: ExtractedFacts
  scores: Step1Scores
  markdown_files: Record<string, string>
  prompts_sent?: Record<string, string>
  components?: ComponentRead[]
  combined?: CombinedRead | null
}

export interface PromptSpec {
  id: string
  title: string
  audience: string
  max_tokens: number
  variables: string[]
  template: string
}

export interface PromptCatalog {
  rubric: string
  generation: {
    model: string
    provider?: string
    think: boolean
    keep_alive: string
    num_ctx: number
    repeat_last_n: number
    json_mode: boolean
    attempts: {
      temperature: number
      repeat_penalty: number
      num_predict: string
      when?: string
    }[]
  }
  prompts: PromptSpec[]
}

export interface JobProgress {
  index?: number
  total?: number
  file?: string
  applicant?: string
  /** Short name of the agent currently running. */
  agent?: string
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
