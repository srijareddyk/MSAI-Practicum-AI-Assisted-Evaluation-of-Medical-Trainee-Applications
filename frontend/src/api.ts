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
