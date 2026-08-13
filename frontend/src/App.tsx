import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  excelDownloadUrl,
  fetchHealth,
  fetchJob,
  markdownDownloadUrl,
  startAnalysis,
} from './api'
import type {
  AnalysisMode,
  ApplicantResult,
  HealthResponse,
  Job,
} from './types'
import './App.css'

const SCORE_LABELS: Record<string, string> = {
  scientific_pursuits_education: 'Scientific pursuits — education',
  scientific_pursuits_output: 'Scientific pursuits — output',
  professional_leadership_education: 'Professional leadership — education',
  professional_leadership_output: 'Professional leadership — output',
  social_leadership: 'Social leadership / service',
  resilience: 'Resilience',
  endorsement: 'Endorsement (letters)',
  reviewer_recommendation: 'Recommendation',
}

const STAGE_COPY: Record<string, string> = {
  queued: 'Queued…',
  extracting: 'Extracting facts from PDF…',
  briefing: 'Generating factual briefing…',
  doc_a: 'Doc A reviewing application…',
  doc_b: 'Doc B reviewing application…',
  applicant_done: 'Applicant complete…',
  writing_excel: 'Writing Excel workbook…',
  complete: 'Complete',
  error: 'Error',
}

function formatScore(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

function NBadge() {
  return <div className="n-badge" aria-hidden>N</div>
}

function Dropzone({
  files,
  onFiles,
}: {
  files: File[]
  onFiles: (files: File[]) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [active, setActive] = useState(false)

  const addFiles = (list: FileList | null) => {
    if (!list) return
    const pdfs = Array.from(list).filter((f) => f.name.toLowerCase().endsWith('.pdf'))
    if (!pdfs.length) return
    onFiles([...files, ...pdfs])
  }

  return (
    <>
      <div
        className={`dropzone ${active ? 'active' : ''}`}
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
        }}
        onDragOver={(e) => {
          e.preventDefault()
          setActive(true)
        }}
        onDragLeave={() => setActive(false)}
        onDrop={(e) => {
          e.preventDefault()
          setActive(false)
          addFiles(e.dataTransfer.files)
        }}
      >
        <div className="drop-icon">↑</div>
        <h3>Upload ERAS application PDFs</h3>
        <p>Drag and drop, or click to browse. Processing stays local via Ollama.</p>
        <input
          ref={inputRef}
          className="hidden-input"
          type="file"
          accept="application/pdf,.pdf"
          multiple
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>
      {files.length > 0 && (
        <ul className="file-list">
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`}>
              <span>{f.name}</span>
              <button
                type="button"
                aria-label={`Remove ${f.name}`}
                onClick={() => onFiles(files.filter((_, j) => j !== i))}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

function ObjectiveScores({ scores }: { scores: ApplicantResult['scores'] }) {
  const chips = [
    { key: 'msq', label: 'Med school quality', value: scores.medical_school_quality },
    { key: 'msp', label: 'Med school performance', value: scores.medical_school_performance },
    { key: 'uq', label: 'Undergrad quality', value: scores.undergraduate_quality },
    { key: 'up', label: 'Undergrad performance', value: scores.undergraduate_performance },
    {
      key: 'usmle',
      label: 'USMLE Step 1',
      value: scores.usmle_step1,
      tone: scores.usmle_step1 === 'P' ? 'pass' : scores.usmle_step1 === 'F' ? 'fail' : '',
    },
  ] as const

  return (
    <div className="score-band">
      {chips.map((c) => (
        <div key={c.key} className={`score-chip ${'tone' in c ? c.tone : ''}`}>
          <div className="value">{formatScore(c.value)}</div>
          <span className="label">{c.label}</span>
        </div>
      ))}
    </div>
  )
}

function AgentColumn({
  title,
  focus,
  review,
  variant,
}: {
  title: string
  focus: string
  review: ApplicantResult['doc_a']
  variant: 'doc-a' | 'doc-b'
}) {
  if (!review) {
    return (
      <div className={`agent-col ${variant}`}>
        <div className="agent-head">
          <h3>{title}</h3>
        </div>
        <p className="empty-state">Not run for this mode.</p>
      </div>
    )
  }

  const rec = review.scores.reviewer_recommendation
  const recClass = typeof rec === 'string' && ['A', 'B', 'C'].includes(rec) ? rec : 'none'

  return (
    <div className={`agent-col ${variant}`}>
      <div className="agent-head">
        <h3>{title}</h3>
        <span className={`rec-badge ${recClass}`} title="Reviewer recommendation">
          {formatScore(rec as string | null)}
        </span>
      </div>
      <p className="agent-focus">{focus}</p>
      {review.error && <div className="error-banner">{review.error}</div>}
      {review.summary && <p className="agent-summary">{review.summary}</p>}
      <table className="score-table">
        <thead>
          <tr>
            <th>Criterion</th>
            <th>Score</th>
            <th>Rationale</th>
          </tr>
        </thead>
        <tbody>
          {Object.keys(SCORE_LABELS)
            .filter((k) => k !== 'reviewer_recommendation')
            .map((key) => (
              <tr key={key}>
                <td>{SCORE_LABELS[key]}</td>
                <td className="num">{formatScore(review.scores[key])}</td>
                <td className="why">{review.rationale[key] || '—'}</td>
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  )
}

function BriefingView({ briefing }: { briefing: Record<string, unknown> | null }) {
  if (!briefing) return null
  if (briefing.error) {
    return (
      <div className="briefing-block">
        <h3>Factual briefing</h3>
        <div className="error-banner">{String(briefing.error)}</div>
      </div>
    )
  }

  const sections: { key: string; title: string }[] = [
    { key: 'scientific_pursuits_education', title: 'Scientific pursuits — education' },
    { key: 'scientific_pursuits_output', title: 'Scientific pursuits — output' },
    { key: 'professional_leadership_education', title: 'Professional leadership — education' },
    { key: 'professional_leadership_output', title: 'Professional leadership — output' },
    { key: 'social_leadership_service', title: 'Social leadership / service' },
    { key: 'resilience', title: 'Resilience' },
    { key: 'endorsements', title: 'Endorsements' },
  ]

  return (
    <div className="briefing-block">
      <h3>Factual briefing</h3>
      <div className="briefing-grid">
        {sections.map(({ key, title }) => {
          const block = briefing[key] as { summary?: string } | undefined
          if (!block || typeof block !== 'object') return null
          return (
            <div key={key} className="brief-item">
              <h4>{title}</h4>
              <p>{block.summary || 'No summary extracted.'}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ResultsView({ job }: { job: Job }) {
  const [selected, setSelected] = useState(0)
  const applicant = job.applicants[selected]

  useEffect(() => {
    setSelected(0)
  }, [job.id])

  if (!applicant) {
    return <p className="empty-state">No applicant results.</p>
  }

  return (
    <div>
      {job.applicants.length > 1 && (
        <div className="applicant-tabs">
          {job.applicants.map((a, i) => (
            <button
              key={a.file}
              type="button"
              className={`tab ${i === selected ? 'active' : ''}`}
              onClick={() => setSelected(i)}
            >
              {a.applicant_name || a.file}
            </button>
          ))}
        </div>
      )}

      <div className="applicant-header">
        <div>
          <h2>{applicant.applicant_name || 'Unnamed applicant'}</h2>
          <p className="applicant-meta">Source: {applicant.file}</p>
        </div>
        <div className="btn-row">
          <a className="btn btn-primary" href={excelDownloadUrl(job.id)}>
            Download Excel
          </a>
          {applicant.markdown_files.brief && (
            <a
              className="btn btn-ghost"
              href={markdownDownloadUrl(job.id, applicant.markdown_files.brief)}
            >
              Briefing MD
            </a>
          )}
          {applicant.markdown_files.doc_a && (
            <a
              className="btn btn-ghost"
              href={markdownDownloadUrl(job.id, applicant.markdown_files.doc_a)}
            >
              Doc A MD
            </a>
          )}
          {applicant.markdown_files.doc_b && (
            <a
              className="btn btn-ghost"
              href={markdownDownloadUrl(job.id, applicant.markdown_files.doc_b)}
            >
              Doc B MD
            </a>
          )}
        </div>
      </div>

      <h3 className="section-title" style={{ fontSize: '1.15rem' }}>
        Extracted facts
      </h3>
      <dl className="facts-grid">
        <div className="fact">
          <dt>Medical school</dt>
          <dd>{applicant.facts.medical_school || '—'}</dd>
        </div>
        <div className="fact">
          <dt>Undergraduate</dt>
          <dd>{applicant.facts.undergraduate_institution || '—'}</dd>
        </div>
        <div className="fact">
          <dt>Undergrad GPA</dt>
          <dd>
            {applicant.facts.undergraduate_cum_gpa != null
              ? applicant.facts.undergraduate_cum_gpa.toFixed(2)
              : '—'}
          </dd>
        </div>
        <div className="fact">
          <dt>USMLE Step 1</dt>
          <dd>
            {applicant.facts.usmle_step1_result || '—'}
            {applicant.facts.usmle_step1_times_taken != null
              ? ` · ${applicant.facts.usmle_step1_times_taken}×`
              : ''}
          </dd>
        </div>
      </dl>

      <h3 className="section-title" style={{ fontSize: '1.15rem' }}>
        Step 1 — objective scores
      </h3>
      <p className="section-sub">Rule-based rubric fields (no LLM).</p>
      <ObjectiveScores scores={applicant.scores} />

      {(applicant.doc_a || applicant.doc_b) && (
        <>
          <h3 className="section-title" style={{ fontSize: '1.15rem' }}>
            Doc A & Doc B reviews
          </h3>
          <p className="section-sub">
            Independent AI screeners with different emphases. Draft scores for faculty validation.
          </p>
          <div className="compare">
            <AgentColumn
              title="Doc A"
              focus="Research · publications · letters"
              review={applicant.doc_a}
              variant="doc-a"
            />
            <AgentColumn
              title="Doc B"
              focus="Leadership · service · resilience"
              review={applicant.doc_b}
              variant="doc-b"
            />
          </div>
        </>
      )}

      <BriefingView briefing={applicant.briefing} />

      {applicant.facts.notes?.length > 0 && (
        <div className="notes">
          <strong>Extraction notes</strong>
          <ul>
            {applicant.facts.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function progressPercent(job: Job): number {
  if (job.status === 'completed') return 100
  if (job.status === 'failed') return 100
  const total = job.progress.total || 1
  const index = job.progress.index ?? 0
  const stageWeights: Record<string, number> = {
    queued: 0.05,
    extracting: 0.15,
    briefing: 0.4,
    doc_a: 0.65,
    doc_b: 0.85,
    applicant_done: 0.95,
    writing_excel: 0.98,
  }
  const base = index / total
  const within = (stageWeights[job.stage] ?? 0.2) / total
  return Math.min(99, Math.round((base + within) * 100))
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [files, setFiles] = useState<File[]>([])
  const [mode, setMode] = useState<AnalysisMode>('full')
  const [model, setModel] = useState('qwen3:14b')
  const [job, setJob] = useState<Job | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setHealth(h)
        setModel(h.default_model)
      })
      .catch(() =>
        setHealth({
          status: 'down',
          template_present: false,
          default_model: 'qwen3:14b',
          ollama: { ok: false, available: false, requested: 'qwen3:14b' },
        }),
      )
  }, [])

  useEffect(() => {
    if (!job || job.status !== 'running') return
    const id = window.setInterval(async () => {
      try {
        const next = await fetchJob(job.id)
        setJob(next)
        if (next.status !== 'running') setBusy(false)
      } catch {
        /* keep polling */
      }
    }, 1200)
    return () => window.clearInterval(id)
  }, [job])

  const ollamaOk = health?.ollama.ok && health.ollama.available
  const apiOk = health?.status === 'ok'

  const statusLabel = useMemo(() => {
    if (!health) return 'Checking services…'
    if (!apiOk) return 'API offline'
    if (!health.template_present) return 'Rubric template missing'
    if (!health.ollama.ok) return 'Ollama unreachable'
    if (!health.ollama.available) return `Model ${health.default_model} not pulled`
    return 'Ready · local Ollama'
  }, [health, apiOk])

  const onSubmit = useCallback(async () => {
    setError(null)
    if (!files.length) {
      setError('Add at least one PDF to screen.')
      return
    }
    setBusy(true)
    setJob(null)
    try {
      const { job_id } = await startAnalysis(files, mode, model)
      const initial = await fetchJob(job_id)
      setJob(initial)
    } catch (err) {
      setBusy(false)
      setError(err instanceof Error ? err.message : 'Failed to start analysis')
    }
  }, [files, mode, model])

  const showResults = job?.status === 'completed' && job.applicants.length > 0

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand-mark" href="/">
          <NBadge />
          <div className="brand-text">
            <strong>Northwestern Medicine</strong>
            <span>Ophthalmology · Residency screening</span>
          </div>
        </a>
        <div className="status-pill">
          <span className={`status-dot ${ollamaOk && apiOk ? 'ok' : 'warn'}`} />
          {statusLabel}
        </div>
      </header>

      <section className="hero">
        <div className="hero-atmosphere" aria-hidden />
        <div className="hero-inner">
          <p className="hero-kicker">Feinberg School of Medicine</p>
          <h1>Northwestern</h1>
          <p className="hero-lead">
            AI-assisted evaluation of medical trainee applications — objective rubric scoring and
            dual local reviewers, private by design.
          </p>
        </div>
      </section>

      <main className="main">
        <div className="panel">
          <div className="panel-section">
            <h2 className="section-title">Screen applications</h2>
            <p className="section-sub">
              Upload ERAS PDFs and choose how deep the screen should go. Objective fields are
              scored by rules; narrative review uses a model that runs only on this machine.
            </p>

            <Dropzone files={files} onFiles={setFiles} />

            <div className="controls">
              <div className="field">
                <label>Screening depth</label>
                <div className="mode-group">
                  {(
                    [
                      [
                        'full',
                        'Complete review',
                        'Objective scores + dual faculty-style AI reviews',
                      ],
                      [
                        'briefing',
                        'Structured summary',
                        'Objective scores + factual briefing only',
                      ],
                      [
                        'step1',
                        'Objective metrics',
                        'Schools, GPA, USMLE — no AI narrative review',
                      ],
                    ] as const
                  ).map(([value, label, hint]) => (
                    <button
                      key={value}
                      type="button"
                      className={`mode-option ${mode === value ? 'selected' : ''}`}
                      onClick={() => setMode(value)}
                      disabled={busy}
                      title={hint}
                    >
                      <strong>{label}</strong>
                      <span>{hint}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="field">
                <label htmlFor="model">Local model</label>
                <input
                  id="model"
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  disabled={busy}
                />
              </div>

              <button
                type="button"
                className="btn btn-primary"
                onClick={onSubmit}
                disabled={busy || !files.length}
              >
                {busy ? 'Screening…' : 'Run screening'}
              </button>
            </div>

            <div className="privacy-note">
              <strong>Privacy (FERPA)</strong>
              <p>
                Applications are processed locally — nothing is sent to cloud LLM APIs. There is
                no fully automatic de-identification that is 100% reliable: names and identifiers
                appear throughout personal statements, letters, MSPEs, and publications. Treat
                uploads as identifiable education records and keep them on approved institutional
                systems.
              </p>
            </div>

            {error && <div className="error-banner">{error}</div>}
          </div>

          {job && job.status === 'running' && (
            <div className="panel-section progress-wrap">
              <h2 className="section-title">In progress</h2>
              <p className="stage-label">
                <strong>{STAGE_COPY[job.stage] || job.stage}</strong>
                {job.progress.applicant ? ` · ${job.progress.applicant}` : ''}
                {job.progress.total
                  ? ` · ${((job.progress.index ?? 0) + 1)} of ${job.progress.total}`
                  : ''}
              </p>
              <div className="progress-track">
                <div className="progress-bar" style={{ width: `${progressPercent(job)}%` }} />
              </div>
            </div>
          )}

          {job?.status === 'failed' && (
            <div className="panel-section">
              <div className="error-banner">
                Screening failed: {job.error || 'Unknown error'}
              </div>
            </div>
          )}

          {showResults && job && (
            <div className="panel-section">
              <h2 className="section-title">Results</h2>
              <p className="section-sub">
                Draft scores for faculty review — not final admissions decisions.
              </p>
              <ResultsView job={job} />
            </div>
          )}
        </div>
      </main>

      <footer className="footer">
        <strong>Northwestern University</strong> · MSAI Practicum · Local inference only · Do not
        upload real applicant data to public hosts
      </footer>
    </div>
  )
}
