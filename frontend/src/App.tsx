import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { fetchHealth, fetchJob, startAnalysis } from './api'
import type { HealthResponse, Job } from './types'
import CircleBoard from './CircleBoard'
import DevDesk from './DevDesk'
import { DEFAULT_READERS, READERS, readerById } from './readers'
import './App.css'

const STAGE_COPY: Record<string, string> = {
  queued: 'Queued',
  extracting: 'Reading the packet',
  statement: 'Personal statement sub-agent',
  letters: 'Letters sub-agent',
  research: 'Research sub-agent',
  clinical: 'Clinical sub-agent',
  academics: 'Academics sub-agent',
  commitment: 'Commitment sub-agent',
  writing_excel: 'Saving the file',
  complete: 'Complete',
  error: 'Error',
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
        className={`dropzone ${active ? 'active' : ''} ${files.length ? 'has-files' : ''}`}
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
          <h3>{files.length ? 'Add another PDF' : 'Upload a residency packet'}</h3>
          <p>PDF only. Packets are read on this computer; the review agents call the configured model.</p>
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

function progressPercent(job: Job): number {
  if (job.status === 'completed' || job.status === 'failed') return 100
  const total = job.progress.total || 1
  const index = job.progress.index ?? 0
  const stageWeights: Record<string, number> = {
    queued: 0.05,
    extracting: 0.12,
    statement: 0.28,
    letters: 0.42,
    research: 0.56,
    clinical: 0.7,
    academics: 0.82,
    commitment: 0.9,
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
  const [readers, setReaders] = useState<string[]>([...DEFAULT_READERS])
  const [focusId, setFocusId] = useState<string>(DEFAULT_READERS[0])
  const [model, setModel] = useState('qwen3:8b')
  const [job, setJob] = useState<Job | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [desk, setDesk] = useState<'review' | 'dev'>('review')

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
  const focused = readerById(focusId) || READERS[0]

  const statusLabel = useMemo(() => {
    if (!health) return 'Checking services'
    if (!apiOk) return 'API offline'
    if (!health.template_present) return 'Rubric workbook missing'
    const gemini = health.provider === 'gemini'
    if (!health.ollama.ok) return gemini ? 'Gemini unreachable — check API key' : 'Ollama unreachable'
    if (!health.ollama.available)
      return gemini ? `${health.default_model} not available for this key` : `Pull ${health.default_model} first`
    return gemini ? `Ready · Gemini ${health.default_model}` : 'Ready on this machine'
  }, [health, apiOk])

  const toggleReader = useCallback((id: string) => {
    setFocusId(id)
    setReaders((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )
  }, [])

  const onSubmit = useCallback(async () => {
    setError(null)
    if (!files.length) {
      setError('Upload a PDF to begin.')
      return
    }
    if (readers.length < 2) {
      setError('Turn on at least two sub-agents before starting.')
      return
    }
    setBusy(true)
    setJob(null)
    try {
      const { job_id } = await startAnalysis(files, readers, model)
      const initial = await fetchJob(job_id)
      setJob(initial)
    } catch (err) {
      setBusy(false)
      setError(err instanceof Error ? err.message : 'Could not start the review')
    }
  }, [files, readers, model])

  return (
    <div className="shell">
      <aside className="rail no-print">
        <a className="brand" href="/">
          <div className="mark" aria-hidden>
            O
          </div>
          <div>
            <strong>Ophthalmology</strong>
            <span>Northwestern</span>
          </div>
        </a>
        <nav className="rail-nav" aria-label="Desk">
          <button type="button" className={desk === 'review' ? 'active' : ''} onClick={() => setDesk('review')}>
            Review
          </button>
          <button type="button" className={desk === 'dev' ? 'active' : ''} onClick={() => setDesk('dev')}>
            Developer
          </button>
        </nav>
        <div className="status-pill">
          <span className={`status-dot ${ollamaOk && apiOk ? 'ok' : ''}`} />
          {statusLabel}
        </div>
        <div className="rail-block">
          <h2>Sub-agents</h2>
          <ul className="agent-rail">
            {READERS.map((reader) => {
              const on = readers.includes(reader.id)
              return (
                <li key={reader.id}>
                  <button
                    type="button"
                    className={`agent-rail-btn ${focusId === reader.id ? 'focused' : ''} ${on ? 'on' : ''}`}
                    onClick={() => setFocusId(reader.id)}
                  >
                    <strong>{reader.short}</strong>
                    <span>{reader.reads}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
        <p className="rail-note">
          Each sub-agent reads one part of the packet, returns a color, and cites a short snippet.
          Faculty decide who is invited to interview.
        </p>
      </aside>

      <div className="workspace">
        <header className="page-head no-print">
          <div>
            <p className="kicker">Department of Ophthalmology</p>
            <h1>{desk === 'dev' ? 'Sub-agent prompts' : 'Residency review'}</h1>
            <p className="lede">
              {desk === 'dev'
                ? 'Inspect the exact prompt template or the filled prompt that went to each local sub-agent.'
                : 'Upload a packet, choose which sub-agents run, then open a color for cited evidence from the file.'}
            </p>
          </div>
        </header>

        <div className="desk">
          {desk === 'review' && (
            <section className="desk-section no-print">
              <div className="agent-brief">
                <div className="agent-brief-head">
                  <div>
                    <p className="evidence-label">What this sub-agent does</p>
                    <h2 className="section-title">{focused.label}</h2>
                  </div>
                  <button
                    type="button"
                    className={`btn ${readers.includes(focused.id) ? 'btn-primary' : 'btn-ghost'}`}
                    onClick={() => toggleReader(focused.id)}
                    disabled={busy}
                  >
                    {readers.includes(focused.id) ? 'Remove from review' : 'Include in review'}
                  </button>
                </div>
                <p className="agent-detail">{focused.detail}</p>
                <dl className="agent-facts">
                  <div>
                    <dt>Reads</dt>
                    <dd>{focused.reads}</dd>
                  </div>
                  <div>
                    <dt>Looks for</dt>
                    <dd>{focused.looksFor}</dd>
                  </div>
                  <div>
                    <dt>Returns</dt>
                    <dd>{focused.returns}</dd>
                  </div>
                </dl>
                <div className="agent-picker" role="group" aria-label="Choose sub-agents">
                  {READERS.map((reader) => {
                    const on = readers.includes(reader.id)
                    return (
                      <button
                        key={reader.id}
                        type="button"
                        className={`agent-pill ${on ? 'on' : ''} ${focusId === reader.id ? 'focused' : ''}`}
                        onClick={() => {
                          setFocusId(reader.id)
                          if (!busy) {
                            setReaders((current) =>
                              current.includes(reader.id)
                                ? current
                                : [...current, reader.id],
                            )
                          }
                        }}
                        disabled={busy}
                      >
                        <span>{reader.short}</span>
                        <small>{on ? 'On' : 'Off'}</small>
                      </button>
                    )
                  })}
                </div>
                <p className="agent-hint">
                  Select a sub-agent to read what it does. Use <b>Include in review</b> /{' '}
                  <b>Remove from review</b> to change who runs. At least two must stay on.
                </p>
              </div>

              <div className="upload-block">
                <Dropzone files={files} onFiles={setFiles} />
                <div className="controls">
                  <div className="field">
                    <label htmlFor="model">Model</label>
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
                    disabled={busy || !files.length || readers.length < 2}
                  >
                    {busy ? 'Reviewing…' : 'Begin review'}
                  </button>
                </div>
              </div>

              <div className="board-block">
                <div className="board-head">
                  <h2 className="section-title">Application in the center</h2>
                  <p className="section-sub">
                    Side cards are the sub-agents. After a review they turn green, yellow, or red. Click a
                    finished card for paragraph snippets cited from the packet.
                  </p>
                </div>
                <CircleBoard
                  job={job?.status === 'completed' ? job : null}
                  centerLabel={files[0]?.name.replace(/\.pdf$/i, '') || 'No packet yet'}
                  centerDetail={files.length ? `${files.length} uploaded` : 'Upload a PDF above'}
                  selectedIds={readers}
                  disabled={busy}
                  onToggle={toggleReader}
                />
              </div>

              {error && <div className="error-banner">{error}</div>}
            </section>
          )}

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

          {desk === 'dev' && (
            <section className="desk-section dev-section no-print">
              <h2 className="section-title">Prompts for each sub-agent</h2>
              <p className="section-sub">
                Template is the standing instruction. After you run a review, switch to{' '}
                <b>Sent to the model</b> to see the exact filled prompt each selected sub-agent received.
              </p>
              <DevDesk job={job} />
            </section>
          )}
        </div>
        <p className="footer no-print">
          Northwestern University · Department of Ophthalmology · Residency review
        </p>
      </div>
    </div>
  )
}
