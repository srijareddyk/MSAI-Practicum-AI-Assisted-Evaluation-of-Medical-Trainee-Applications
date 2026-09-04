import type { AnalysisMode, HealthResponse, Job } from './types'

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error('Unable to reach the screening API')
  return res.json()
}

export async function startAnalysis(
  files: File[],
  mode: AnalysisMode,
  model: string,
): Promise<{ job_id: string }> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  form.append('mode', mode)
  form.append('model', model)

  const res = await fetch('/api/analyze', { method: 'POST', body: form })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Failed to start analysis')
  }
  return res.json()
}

export async function fetchJob(jobId: string): Promise<Job> {
  const res = await fetch(`/api/jobs/${jobId}`)
  if (!res.ok) throw new Error('Job not found')
  return res.json()
}

export function excelDownloadUrl(jobId: string): string {
  return `/api/jobs/${jobId}/excel`
}

export function markdownDownloadUrl(jobId: string, filename: string): string {
  return `/api/jobs/${jobId}/markdown/${encodeURIComponent(filename)}`
}

export interface DeveloperOverview {
  provider: string
  default_model: string
  formula: string
  pricing: Array<{
    model: string
    input_usd_per_million: number
    output_usd_per_million: number
  }>
  example: {
    model: string
    input_tokens: number
    output_tokens: number
    input_rate: number
    output_rate: number
    estimated_usd: number
    note: string
  }
  totals: {
    jobs: number
    calls: number
    tokens: number
    estimated_usd: number
  }
  jobs: Job[]
}

export interface RedactedPayload {
  file: string
  kept_on_this_computer: {
    applicant_name: string | null
    source_chars: number | null
    stripped_chars?: number | null
  }
  sent_to_azure: string
  azure_chars: number
  redaction_notes: string[]
  placeholder_counts: Record<string, number>
}

export async function fetchDeveloperOverview(): Promise<DeveloperOverview> {
  const res = await fetch('/api/developer/overview')
  if (!res.ok) throw new Error('Unable to load developer overview')
  return res.json()
}

export async function fetchJobRedacted(jobId: string): Promise<{ payloads: RedactedPayload[] }> {
  const res = await fetch(`/api/jobs/${jobId}/redacted`)
  if (!res.ok) throw new Error('No redacted payload for this job')
  return res.json()
}

export async function previewRedaction(files: File[]): Promise<{ payloads: RedactedPayload[] }> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  const res = await fetch('/api/developer/preview', { method: 'POST', body: form })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Preview failed')
  }
  return res.json()
}
