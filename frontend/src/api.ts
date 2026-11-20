import type { HealthResponse, Job, PromptCatalog } from './types'

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error('Unable to reach the screening API')
  return res.json()
}

export async function startAnalysis(
  files: File[],
  agents: string[],
  model: string,
): Promise<{ job_id: string }> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  form.append('mode', 'full')
  form.append('model', model)
  form.append('agents', agents.join(','))

  const res = await fetch('/api/analyze', { method: 'POST', body: form })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Failed to start analysis')
  }
  return res.json()
}

export async function fetchPromptCatalog(): Promise<PromptCatalog> {
  const res = await fetch('/api/dev/prompts')
  if (!res.ok) throw new Error('Unable to load the prompt catalog')
  return res.json()
}

export async function fetchLocalPackets(): Promise<{ file: string; label: string }[]> {
  const res = await fetch('/api/local-packets')
  if (!res.ok) throw new Error('Unable to list applications on this machine')
  const body = await res.json()
  return body.packets
}

export async function startLocalAnalysis(
  packets: string[],
  agents: string[],
  model: string,
): Promise<{ job_id: string }> {
  const form = new FormData()
  form.append('packets', packets.join('|'))
  form.append('mode', 'full')
  form.append('model', model)
  form.append('agents', agents.join(','))
  const res = await fetch('/api/analyze-local', { method: 'POST', body: form })
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
