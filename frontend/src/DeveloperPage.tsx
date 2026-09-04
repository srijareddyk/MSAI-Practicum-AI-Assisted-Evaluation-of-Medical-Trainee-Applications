import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  fetchDeveloperOverview,
  fetchJobRedacted,
  previewRedaction,
  type DeveloperOverview,
  type RedactedPayload,
} from './api'

const TOKEN_RE =
  /(\[APPLICANT\]|\[EMAIL\]|\[PHONE\]|\[ADDRESS\]|\[DATE\]|\[SSN\]|\[URL\]|\[AAMC_ID\]|\[APPLICANT_ID\]|\[REDACTED\])/g

function formatUsd(value: number): string {
  if (value < 0.01) return `$${value.toFixed(4)}`
  return `$${value.toFixed(3)}`
}

function HighlightedPayload({ text }: { text: string }) {
  const parts = text.split(TOKEN_RE)
  return (
    <pre className="dev-payload">
      {parts.map((part, i) =>
        part.startsWith('[') && part.endsWith(']') ? (
          <mark key={`${part}-${i}`} className="dev-token">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </pre>
  )
}

export default function DeveloperPage() {
  const [overview, setOverview] = useState<DeveloperOverview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedJob, setSelectedJob] = useState<string>('')
  const [payloads, setPayloads] = useState<RedactedPayload[]>([])
  const [loadingPayload, setLoadingPayload] = useState(false)
  const [inputTokens, setInputTokens] = useState(19189)
  const [outputTokens, setOutputTokens] = useState(2322)

  useEffect(() => {
    fetchDeveloperOverview()
      .then((data) => {
        setOverview(data)
        const first = data.jobs[0]?.id
        if (first) setSelectedJob(first)
        if (data.example) {
          setInputTokens(data.example.input_tokens)
          setOutputTokens(data.example.output_tokens)
        }
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  const loadJobPayload = useCallback(async (jobId: string) => {
    setLoadingPayload(true)
    setError(null)
    try {
      const result = await fetchJobRedacted(jobId)
      setPayloads(result.payloads)
    } catch (err) {
      setPayloads([])
      setError(err instanceof Error ? err.message : 'Could not load redacted text')
    } finally {
      setLoadingPayload(false)
    }
  }, [])

  useEffect(() => {
    if (selectedJob) void loadJobPayload(selectedJob)
  }, [selectedJob, loadJobPayload])

  const onPreviewFiles = async (list: FileList | null) => {
    if (!list?.length) return
    const pdfs = Array.from(list).filter((f) => f.name.toLowerCase().endsWith('.pdf'))
    if (!pdfs.length) return
    setLoadingPayload(true)
    setError(null)
    try {
      const result = await previewRedaction(pdfs)
      setPayloads(result.payloads)
      setSelectedJob('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed')
    } finally {
      setLoadingPayload(false)
    }
  }

  const rate = overview?.pricing.find((p) => p.model === overview.default_model) ?? {
    input_usd_per_million: 0.4,
    output_usd_per_million: 1.6,
  }
  const calcUsd =
    (inputTokens / 1_000_000) * rate.input_usd_per_million +
    (outputTokens / 1_000_000) * rate.output_usd_per_million

  const selectedUsage = useMemo(
    () => overview?.jobs.find((j) => j.id === selectedJob)?.llm_usage,
    [overview, selectedJob],
  )

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand-mark" href="/">
          <div className="n-badge" aria-hidden>
            N
          </div>
          <div className="brand-text">
            <strong>Optival · Developer</strong>
            <span>Faculty demo · what Azure receives</span>
          </div>
        </a>
        <a className="status-pill" href="/">
          Back to screening
        </a>
      </header>

      <section className="hero">
        <div className="hero-atmosphere" aria-hidden />
        <div className="hero-inner">
          <p className="hero-kicker">Local only · not on Vercel</p>
          <h1>Developer</h1>
          <p className="hero-lead">
            Azure never gets the PDF. It gets this stripped, identifier-redacted text. Names stay
            on this computer for the Excel file.
          </p>
        </div>
      </section>

      <main className="main">
        <div className="panel">
          {error && <div className="error-banner">{error}</div>}

          <div className="panel-section">
            <h2 className="section-title">Cost conversion</h2>
            <p className="section-sub">
              {overview?.formula}. Student credit is billed in USD at Azure Global Standard list
              price.
            </p>
            <table className="dev-table">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Input / 1M tokens</th>
                  <th>Output / 1M tokens</th>
                </tr>
              </thead>
              <tbody>
                {(overview?.pricing ?? []).map((row) => (
                  <tr key={row.model} className={row.model === overview?.default_model ? 'is-active' : ''}>
                    <td>{row.model}</td>
                    <td>${row.input_usd_per_million.toFixed(2)}</td>
                    <td>${row.output_usd_per_million.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {overview?.example && (
              <p className="usage-note">
                First complete review on this account: {overview.example.input_tokens.toLocaleString()}{' '}
                input + {overview.example.output_tokens.toLocaleString()} output ={' '}
                {formatUsd(overview.example.estimated_usd)} ({overview.example.note})
              </p>
            )}
            <div className="dev-calc">
              <label>
                Input tokens
                <input
                  type="number"
                  min={0}
                  value={inputTokens}
                  onChange={(e) => setInputTokens(Number(e.target.value) || 0)}
                />
              </label>
              <label>
                Output tokens
                <input
                  type="number"
                  min={0}
                  value={outputTokens}
                  onChange={(e) => setOutputTokens(Number(e.target.value) || 0)}
                />
              </label>
              <div className="dev-calc-result">
                <span>Estimated credit</span>
                <strong>{formatUsd(calcUsd)}</strong>
              </div>
            </div>
            {overview && (
              <dl className="usage-grid" style={{ marginTop: '1rem' }}>
                <div>
                  <dt>Jobs on disk</dt>
                  <dd>{overview.totals.jobs}</dd>
                </div>
                <div>
                  <dt>Tracked calls</dt>
                  <dd>{overview.totals.calls}</dd>
                </div>
                <div>
                  <dt>Tracked tokens</dt>
                  <dd>{overview.totals.tokens.toLocaleString()}</dd>
                </div>
                <div>
                  <dt>Tracked credit</dt>
                  <dd>{formatUsd(overview.totals.estimated_usd)}</dd>
                </div>
              </dl>
            )}
          </div>

          <div className="panel-section">
            <h2 className="section-title">What Azure receives</h2>
            <p className="section-sub">
              Load a past screening, or drop a PDF here to redact locally without calling Azure.
            </p>
            <div className="dev-toolbar">
              <label className="field" style={{ minWidth: '14rem' }}>
                Past job
                <select value={selectedJob} onChange={(e) => setSelectedJob(e.target.value)}>
                  <option value="">Choose a job…</option>
                  {(overview?.jobs ?? []).map((job) => (
                    <option key={job.id} value={job.id}>
                      {job.files[0] || job.id} ({job.id})
                    </option>
                  ))}
                </select>
              </label>
              <label className="btn btn-ghost">
                Preview PDF (no Azure)
                <input
                  type="file"
                  accept="application/pdf"
                  multiple
                  hidden
                  onChange={(e) => {
                    void onPreviewFiles(e.target.files)
                    e.target.value = ''
                  }}
                />
              </label>
            </div>
            {selectedUsage && selectedUsage.calls > 0 && (
              <p className="usage-note">
                This job: {selectedUsage.calls} calls · {selectedUsage.prompt_tokens.toLocaleString()}{' '}
                input · {selectedUsage.completion_tokens.toLocaleString()} output ·{' '}
                {formatUsd(selectedUsage.estimated_usd)}
              </p>
            )}
            {loadingPayload && <p className="stage-label">Building redacted payload…</p>}
            {payloads.map((payload) => (
              <article key={payload.file} className="dev-payload-wrap">
                <header className="applicant-header">
                  <div>
                    <h2>{payload.file}</h2>
                    <p className="applicant-meta">
                      {payload.azure_chars.toLocaleString()} characters sent to Azure
                      {payload.kept_on_this_computer.applicant_name
                        ? ` · name kept locally as ${payload.kept_on_this_computer.applicant_name}`
                        : ''}
                    </p>
                  </div>
                </header>
                {payload.placeholder_counts && Object.keys(payload.placeholder_counts).length > 0 && (
                  <ul className="dev-tags">
                    {Object.entries(payload.placeholder_counts).map(([tag, count]) => (
                      <li key={tag}>
                        {tag} × {count}
                      </li>
                    ))}
                  </ul>
                )}
                {payload.redaction_notes.length > 0 && (
                  <p className="usage-note">{payload.redaction_notes.join(' · ')}</p>
                )}
                <HighlightedPayload text={payload.sent_to_azure} />
              </article>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
