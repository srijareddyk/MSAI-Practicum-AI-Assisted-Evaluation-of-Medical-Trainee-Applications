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
  scientific_pursuits_education: 'Technical preparation',
  scientific_pursuits_output: 'Research and projects',
  professional_leadership_education: 'Quantitative preparation',
  professional_leadership_output: 'Technical leadership',
  social_leadership: 'Collaboration and service',
  resilience: 'Statement and trajectory',
  endorsement: 'Letters',
  reviewer_recommendation: 'Recommendation',
}

const BRIEFING_SECTIONS: { key: string; title: string }[] = [
  { key: 'scientific_pursuits_education', title: 'Technical preparation' },
  { key: 'scientific_pursuits_output', title: 'Research and projects' },
  { key: 'professional_leadership_education', title: 'Quantitative preparation' },
  { key: 'professional_leadership_output', title: 'Technical leadership' },
  { key: 'social_leadership_service', title: 'Collaboration and service' },
  { key: 'resilience', title: 'Statement of purpose' },
  { key: 'endorsements', title: 'Letters' },
]

const STAGE_COPY: Record<string, string> = {
  queued: 'Queued',
  extracting: 'Reading the packet',
  briefing: 'Writing the factual brief',
  doc_a: 'Reviewer A, technical readiness',
  doc_b: 'Reviewer B, program fit',
  doc_c: 'Reviewer C, academic record',
  applicant_done: 'Packet complete',
  writing_excel: 'Writing the workbook',
  complete: 'Complete',
  error: 'Error',
}

function reportFileName(job: Job, applicant: ApplicantResult): string {
  const base = applicant.applicant_name || applicant.file.replace(/\.pdf$/i, '')
  const safe = base.trim().replace(/[^\w]+/g, '_').replace(/^_+|_+$/g, '') || 'applicant'
  return `MSAI_screening_${safe}_${job.id}`
}

function downloadReportPdf(job: Job, applicant: ApplicantResult): void {
  const previousTitle = document.title
  document.title = reportFileName(job, applicant)
  const restore = () => {
    document.title = previousTitle
    window.removeEventListener('afterprint', restore)
  }
  window.addEventListener('afterprint', restore)
  window.print()
  window.setTimeout(restore, 3000)
}

function formatScore(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

function recommendationOf(review: ApplicantResult['doc_a']): string {
  const rec = review?.scores.reviewer_recommendation
  return typeof rec === 'string' ? rec : ''
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
        <div>
          <div className="drop-mark" aria-hidden>
            +
          </div>
          <h3>Upload application packets</h3>
          <p>PDF only. Statement of purpose, academic record, research, projects, and letters. Review runs on this computer.</p>
          <input
            ref={inputRef}
            className="hidden-input"
            type="file"
            accept="application/pdf,.pdf"
            multiple
            onChange={(e) => addFiles(e.target.files)}
          />
        </div>
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

function ObjectiveScores({ applicant }: { applicant: ApplicantResult }) {
  const { scores, facts } = applicant
  const chips: { key: string; label: string; value: number | string | null; tone?: string }[] = [
    { key: 'uq', label: 'Prior institution', value: scores.undergraduate_quality },
    { key: 'up', label: 'GPA band', value: scores.undergraduate_performance },
  ]
  const hasClinical =
    Boolean(facts.medical_school) ||
    Boolean(facts.usmle_step1_result) ||
    scores.medical_school_quality != null ||
    scores.medical_school_performance != null ||
    Boolean(scores.usmle_step1)

  if (hasClinical) {
    chips.push(
      { key: 'msq', label: 'Med school signal', value: scores.medical_school_quality },
      { key: 'msp', label: 'Clerkship signal', value: scores.medical_school_performance },
      {
        key: 'usmle',
        label: 'USMLE Step 1',
        value: scores.usmle_step1,
        tone: scores.usmle_step1 === 'P' ? 'pass' : scores.usmle_step1 === 'F' ? 'fail' : '',
      },
    )
  }

  return (
    <div className="score-band">
      {chips.map((c) => (
        <div key={c.key} className={`score-chip ${c.tone || ''}`}>
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
  variant: 'doc-a' | 'doc-b' | 'doc-c'
}) {
  if (!review) {
    return (
      <div className={`agent-col ${variant}`}>
        <div className="agent-head">
          <h3>{title}</h3>
        </div>
        <p className="empty-state">Not run in this mode.</p>
      </div>
    )
  }

  const rec = review.scores.reviewer_recommendation
  const recClass = typeof rec === 'string' && ['A', 'B', 'C'].includes(rec) ? rec : 'none'

  return (
    <div className={`agent-col ${variant}`}>
      <div className="agent-head">
        <h3>{title}</h3>
        <span className={`rec-badge ${recClass}`} title="Interview recommendation">
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
            <th>Why</th>
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
        <h3>Factual brief</h3>
        <div className="error-banner">{String(briefing.error)}</div>
      </div>
    )
  }

  return (
    <div className="briefing-block">
      <h3>Factual brief</h3>
      <div className="briefing-grid">
        {BRIEFING_SECTIONS.map(({ key, title }) => {
          const block = briefing[key] as { summary?: string } | undefined
          if (!block || typeof block !== 'object') return null
          return (
            <div key={key} className="brief-item">
              <h4>{title}</h4>
              <p>{block.summary || 'Nothing extracted.'}</p>
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

  const recA = recommendationOf(applicant.doc_a)
  const recB = recommendationOf(applicant.doc_b)
  const recC = recommendationOf(applicant.doc_c)
  const letters = [recA, recB, recC].filter(Boolean)
  const split = new Set(letters).size > 1
  const tally = job.applicants.reduce(
    (acc, item) => {
      const letter = recommendationOf(item.doc_a)
      if (letter === 'A' || letter === 'B' || letter === 'C') acc[letter] += 1
      return acc
    },
    { A: 0, B: 0, C: 0 },
  )

  return (
    <div>
      {job.applicants.length > 1 && (
        <>
          <div className="pool no-print" aria-label="Reviewer A recommendations in this batch">
            <span className="pool-chip">
              Reviewer A in this batch · <b>{tally.A}</b> interview · <b>{tally.B}</b> consider ·{' '}
              <b>{tally.C}</b> hold
            </span>
          </div>
          <div className="applicant-tabs no-print">
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
        </>
      )}

      <div className="print-letterhead print-only">
        <div className="print-brand">
          <strong>Northwestern University</strong>
          <span>MSAI admissions review</span>
        </div>
        <div className="print-stamp">
          <span>{new Date().toLocaleString()}</span>
          <span>
            Model: {job.model} · Depth: {job.mode}
          </span>
        </div>
      </div>

      <div className="applicant-header">
        <div>
          <h2>{applicant.applicant_name || 'Unnamed applicant'}</h2>
          <p className="applicant-meta">Packet: {applicant.file}</p>
        </div>
        <div className="btn-row no-print">
          <a className="btn btn-primary" href={excelDownloadUrl(job.id)}>
            Excel
          </a>
          <button type="button" className="btn btn-primary" onClick={() => downloadReportPdf(job, applicant)}>
            PDF
          </button>
          {applicant.markdown_files.brief && (
            <a className="btn btn-ghost" href={markdownDownloadUrl(job.id, applicant.markdown_files.brief)}>
              Brief
            </a>
          )}
          {applicant.markdown_files.doc_a && (
            <a className="btn btn-ghost" href={markdownDownloadUrl(job.id, applicant.markdown_files.doc_a)}>
              Reviewer A
            </a>
          )}
          {applicant.markdown_files.doc_b && (
            <a className="btn btn-ghost" href={markdownDownloadUrl(job.id, applicant.markdown_files.doc_b)}>
              Reviewer B
            </a>
          )}
          {applicant.markdown_files.doc_c && (
            <a className="btn btn-ghost" href={markdownDownloadUrl(job.id, applicant.markdown_files.doc_c)}>
              Reviewer C
            </a>
          )}
        </div>
      </div>

      {split && (
        <div className="split-banner">
          The reviewers do not agree
          {recA ? ` — A ${recA}` : ''}
          {recB ? `, B ${recB}` : ''}
          {recC ? `, C ${recC}` : ''}. Read the rationales before an interview decision.
        </div>
      )}

      <h3 className="section-title" style={{ fontSize: '1.2rem' }}>
        Record on file
      </h3>
      <dl className="facts-grid">
        <div className="fact">
          <dt>Prior institution</dt>
          <dd>{applicant.facts.undergraduate_institution || '—'}</dd>
        </div>
        <div className="fact">
          <dt>Cumulative GPA</dt>
          <dd>
            {applicant.facts.undergraduate_cum_gpa != null
              ? applicant.facts.undergraduate_cum_gpa.toFixed(2)
              : '—'}
          </dd>
        </div>
        {applicant.facts.medical_school && (
          <div className="fact">
            <dt>Medical school</dt>
            <dd>{applicant.facts.medical_school}</dd>
          </div>
        )}
        {applicant.facts.usmle_step1_result && (
          <div className="fact">
            <dt>USMLE Step 1</dt>
            <dd>
              {applicant.facts.usmle_step1_result}
              {applicant.facts.usmle_step1_times_taken != null
                ? ` · ${applicant.facts.usmle_step1_times_taken}×`
                : ''}
            </dd>
          </div>
        )}
      </dl>

      <h3 className="section-title" style={{ fontSize: '1.2rem' }}>
        Academic record signals
      </h3>
      <p className="section-sub">Institution and GPA taken from the document text. No model is used for these fields.</p>
      <ObjectiveScores applicant={applicant} />

      {(applicant.doc_a || applicant.doc_b || applicant.doc_c) && (
        <>
          <h3 className="section-title" style={{ fontSize: '1.2rem' }}>
            Committee reads
          </h3>
          <p className="section-sub">
            Three independent reads of the same rubric. These are drafts for the admissions committee, not decisions.
          </p>
          <div className="compare">
            <AgentColumn
              title="Reviewer A"
              focus="Technical readiness: preparation, research, projects, and letters that speak to the work."
              review={applicant.doc_a}
              variant="doc-a"
            />
            <AgentColumn
              title="Reviewer B"
              focus="Program fit: the statement of purpose, trajectory, and collaboration."
              review={applicant.doc_b}
              variant="doc-b"
            />
            <AgentColumn
              title="Reviewer C"
              focus="Academic record: coursework, grades, and whether the letters support the statement."
              review={applicant.doc_c}
              variant="doc-c"
            />
          </div>
        </>
      )}

      <BriefingView briefing={applicant.briefing} />

      <details className="rubric">
        <summary>Score scale</summary>
        <ul>
          <li>Technical preparation: 4, 2, 1, or 0</li>
          <li>Research and projects: 4, 3, 2, 1, 0.5, or 0</li>
          <li>Quantitative preparation: 2 or 0</li>
          <li>Technical leadership: 4, 2, or 0</li>
          <li>Collaboration: 4, 2, 0.5, or 0</li>
          <li>Statement and trajectory: 3.5, 1.5, or 0</li>
          <li>Letters: 4 down to 0</li>
          <li>Recommendation: A interview, B consider, C do not interview</li>
        </ul>
      </details>

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

      <p className="print-disclaimer print-only">
        Draft scores from a local model for faculty review. Not an admissions decision. Education
        records — keep on approved systems.
      </p>
    </div>
  )
}

function progressPercent(job: Job): number {
  if (job.status === 'completed' || job.status === 'failed') return 100
  const total = job.progress.total || 1
  const index = job.progress.index ?? 0
  const stageWeights: Record<string, number> = {
    queued: 0.05,
    extracting: 0.15,
    briefing: 0.4,
    doc_a: 0.65,
    doc_b: 0.7,
    doc_c: 0.88,
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
  const [model, setModel] = useState('qwen3:8b')
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
          default_model: 'qwen3:8b',
          ollama: { ok: false, available: false, requested: 'qwen3:8b' },
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
    if (!health) return 'Checking local services'
    if (!apiOk) return 'API offline'
    if (!health.template_present) return 'Rubric workbook missing'
    if (!health.ollama.ok) return 'Ollama unreachable'
    if (!health.ollama.available) return `Pull ${health.default_model} first`
    return 'Ready on this machine'
  }, [health, apiOk])

  const onSubmit = useCallback(async () => {
    setError(null)
    if (!files.length) {
      setError('Add at least one application PDF.')
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
      setError(err instanceof Error ? err.message : 'Could not start the review')
    }
  }, [files, mode, model])

  const showResults = job?.status === 'completed' && job.applicants.length > 0

  return (
    <div className="shell">
      <aside className="rail no-print">
        <a className="brand" href="/">
          <div className="mark" aria-hidden>
            M
          </div>
          <div>
            <strong>MSAI Admissions</strong>
            <span>Northwestern</span>
          </div>
        </a>
        <div className="status-pill">
          <span className={`status-dot ${ollamaOk && apiOk ? 'ok' : ''}`} />
          {statusLabel}
        </div>
        <div className="rail-block">
          <h2>Review sequence</h2>
          <ol className="steps">
            <li>
              <span className="step-n">1</span>
              <span>
                <b>Record.</b> Institution and GPA, when the PDF text contains them.
              </span>
            </li>
            <li>
              <span className="step-n">2</span>
              <span>
                <b>Brief.</b> A local model extracts facts and does not score them.
              </span>
            </li>
            <li>
              <span className="step-n">3</span>
              <span>
                <b>Three readers.</b> Technical readiness, program fit, and academic record.
              </span>
            </li>
          </ol>
        </div>
        <p className="rail-note">
          McCormick School of Engineering. Draft reviews for the admissions committee. Faculty decide
          who is invited to interview.
        </p>
      </aside>

      <div className="workspace">
        <header className="page-head no-print">
          <div>
            <p className="kicker">Master of Science in Artificial Intelligence</p>
            <h1>Application review</h1>
            <p className="lede">
              A local review of each application: a factual brief, then three independent reads for
              the admissions committee.
            </p>
          </div>
        </header>

        <div className="desk">
          <section className="desk-section no-print">
            <h2 className="section-title">Applications</h2>
            <p className="section-sub">
              One PDF per applicant. Include the statement of purpose, education, research and
              projects, and letters of recommendation.
            </p>
            <Dropzone files={files} onFiles={setFiles} />
            <div className="controls">
              <div className="field">
                <label>Review depth</label>
                <div className="mode-group">
                  {(
                    [
                      ['full', 'Complete review', 'Record, brief, and three readers'],
                      ['briefing', 'Factual summary', 'Record and a brief, no scores'],
                      ['step1', 'Record only', 'Institution and GPA, no model'],
                    ] as const
                  ).map(([value, label, hint]) => (
                    <button
                      key={value}
                      type="button"
                      className={`mode-option ${mode === value ? 'selected' : ''}`}
                      onClick={() => setMode(value)}
                      disabled={busy}
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
                {busy ? 'Reviewing…' : 'Begin review'}
              </button>
            </div>
            <div className="privacy">
              <strong>Education records</strong>
              Files stay on this machine. Nothing is sent to a cloud model. Names remain in the
              statement and the letters, so treat every upload as an education record.
            </div>
            {error && <div className="error-banner">{error}</div>}
          </section>

          {job && job.status === 'running' && (
            <section className="desk-section no-print">
              <h2 className="section-title">In progress</h2>
              <p className="stage-label">
                <strong>{STAGE_COPY[job.stage] || job.stage}</strong>
                {job.progress.applicant ? ` · ${job.progress.applicant}` : ''}
                {job.progress.total
                  ? ` · ${(job.progress.index ?? 0) + 1} of ${job.progress.total}`
                  : ''}
              </p>
              <div className="progress-track">
                <div className="progress-bar" style={{ width: `${progressPercent(job)}%` }} />
              </div>
            </section>
          )}

          {job?.status === 'failed' && (
            <section className="desk-section no-print">
              <div className="error-banner">Review failed: {job.error || 'Unknown error'}</div>
            </section>
          )}

          {showResults && job && (
            <section className="desk-section" id="print-report">
              <h2 className="section-title no-print">Review</h2>
              <p className="section-sub no-print">
                Draft scores for the committee. An interview invitation is still a faculty decision.
              </p>
              <ResultsView job={job} />
            </section>
          )}
        </div>
        <p className="footer no-print">
          Northwestern University · McCormick School of Engineering · MSAI admissions review
        </p>
      </div>
    </div>
  )
}
