import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { fetchHealth, fetchJob, startAnalysis } from './api'
import type { HealthResponse, Job } from './types'
import CircleBoard, { WORDS } from './CircleBoard'
import DevDesk from './DevDesk'
import SidePanel, { type PanelTab } from './SidePanel'
import { toAgentDefs, useAgents } from './agents'
import './App.css'

const STAGE_COPY: Record<string, string> = {
  queued: 'Queued',
  extracting: 'Reading the packet',
  redacting: 'Removing names and contact details',
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
              <span>
                Application {i + 1} · PDF, {Math.max(1, Math.round(f.size / 1024))} KB
              </span>
              <button
                type="button"
                aria-label={`Remove application ${i + 1}`}
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

function progressPercent(job: Job, agentIds: string[]): number {
  if (job.status === 'completed' || job.status === 'failed') return 100
  const total = job.progress.total || 1
  const index = job.progress.index ?? 0
  const agentAt = agentIds.indexOf(job.stage)
  const fixed: Record<string, number> = {
    queued: 0.03,
    extracting: 0.08,
    redacting: 0.12,
    applicant_done: 0.96,
    writing_excel: 0.98,
  }
  const within = agentAt >= 0 ? 0.15 + (0.8 * agentAt) / Math.max(agentIds.length, 1) : (fixed[job.stage] ?? 0.1)
  return Math.min(99, Math.round(((index + within) / total) * 100))
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [files, setFiles] = useState<File[]>([])
  const store = useAgents()
  const { agents, enabled } = store
  const [panelTab, setPanelTab] = useState<PanelTab>('perspectives')
  const [openId, setOpenId] = useState<string | null>(null)
  const [applicantIndex, setApplicantIndex] = useState(0)
  /** Agents sent with the running/last review, so progress and the circle match it. */
  const [runAgentIds, setRunAgentIds] = useState<string[]>([])
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
        if (next.status !== 'running') {
          setBusy(false)
          setApplicantIndex(0)
          setOpenId(null)
          if (next.status === 'completed') setPanelTab('results')
        }
      } catch {
        /* keep polling */
      }
    }, 1200)
    return () => window.clearInterval(id)
  }, [job])

  const ollamaOk = health?.ollama.ok && health.ollama.available
  const apiOk = health?.status === 'ok'
  const done = job?.status === 'completed' ? job : null
  const applicant = done?.applicants[applicantIndex]
  // After a review the circle shows the perspectives that actually ran.
  const circleAgents = useMemo(() => {
    if (!applicant?.components?.length) return agents
    const ran = new Set(applicant.components.map((read) => read.id))
    const shown = agents.filter((agent) => ran.has(agent.id))
    // A perspective deleted after the run still shows, named as it was then.
    for (const read of applicant.components) {
      if (!shown.some((agent) => agent.id === read.id)) {
        shown.push({
          id: read.id,
          short: read.short,
          label: read.title,
          title: read.title,
          focus: read.title,
          hint: '',
          reads: '',
          looksFor: '',
          returns: '',
          detail: '',
          builtIn: false,
          edited: false,
        })
      }
    }
    return shown
  }, [agents, applicant])

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

  const onToggle = useCallback(
    (id: string) => {
      // Changing who runs starts a fresh board.
      if (done) setJob(null)
      store.toggle(id)
    },
    [done, store],
  )

  const onSubmit = useCallback(async () => {
    setError(null)
    if (!files.length) {
      setError('Upload a PDF to begin.')
      return
    }
    if (enabled.length < 2) {
      setError('Turn on at least two perspectives before starting.')
      return
    }
    const running = agents.filter((agent) => enabled.includes(agent.id))
    setBusy(true)
    setJob(null)
    setOpenId(null)
    setRunAgentIds(running.map((agent) => agent.id))
    try {
      const { job_id } = await startAnalysis(files, toAgentDefs(running), model)
      const initial = await fetchJob(job_id)
      setJob(initial)
    } catch (err) {
      setBusy(false)
      setError(err instanceof Error ? err.message : 'Could not start the review')
    }
  }, [files, enabled, agents, model])

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
          <h2>Perspectives</h2>
          <ul className="agent-rail">
            {agents.map((agent) => {
              const on = enabled.includes(agent.id)
              return (
                <li key={agent.id}>
                  <button
                    type="button"
                    className={`agent-rail-btn ${on ? 'on' : ''}`}
                    onClick={() => {
                      setDesk('review')
                      setPanelTab('perspectives')
                    }}
                  >
                    <strong>{agent.short}</strong>
                    <span>{agent.builtIn ? agent.reads : 'Custom perspective'}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
        <p className="rail-note">
          Each perspective reads one part of the packet, returns a color, and cites a short snippet.
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
                : 'Upload a packet, choose which perspectives run, then hover or click a color for the reason and cited evidence.'}
            </p>
          </div>
        </header>

        <div className="desk">
          {desk === 'review' && (
            <section className="desk-section no-print">
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
                    disabled={busy || !files.length || enabled.length < 2}
                  >
                    {busy ? 'Reviewing…' : `Begin review · ${enabled.length} perspectives`}
                  </button>
                </div>
                {error && <div className="error-banner">{error}</div>}
                {job?.status === 'running' && (
                  <div className="progress-inline">
                    <p className="stage-label">
                      <strong>
                        {job.progress.agent
                          ? `${job.progress.agent} perspective`
                          : STAGE_COPY[job.stage] || 'Working'}
                      </strong>
                      {job.progress.applicant ? ` · ${job.progress.applicant}` : ''}
                      {job.progress.total && job.progress.total > 1
                        ? ` · ${(job.progress.index ?? 0) + 1} of ${job.progress.total}`
                        : ''}
                    </p>
                    <div className="progress-track">
                      <div className="progress-bar" style={{ width: `${progressPercent(job, runAgentIds)}%` }} />
                    </div>
                  </div>
                )}
                {job?.status === 'failed' && (
                  <div className="error-banner">Review failed: {job.error || 'Unknown error'}</div>
                )}
              </div>

              {done && done.applicants.length > 1 && (
                <div className="applicant-tabs" aria-label="Applications in this review">
                  {done.applicants.map((item, index) => (
                    <button
                      key={item.file}
                      type="button"
                      className={`tab ${index === applicantIndex ? 'active' : ''}`}
                      onClick={() => {
                        setApplicantIndex(index)
                        setOpenId(null)
                      }}
                    >
                      {item.applicant_name || `Applicant ${index + 1}`}
                    </button>
                  ))}
                </div>
              )}

              <div className="review-grid">
                <div className="board-sticky">
                  <CircleBoard
                    agents={circleAgents}
                    enabledIds={applicant ? circleAgents.map((agent) => agent.id) : enabled}
                    applicant={applicant}
                    centerDetail={
                      applicant?.combined
                        ? `${WORDS[applicant.combined.opinion]} · ${applicant.components?.length ?? 0} perspectives`
                        : files.length
                          ? `${files.length} packet${files.length > 1 ? 's' : ''} ready`
                          : 'Upload a PDF above'
                    }
                    openId={openId}
                    onOpen={(id) => {
                      setOpenId(id)
                      setPanelTab('results')
                    }}
                    onToggle={onToggle}
                    disabled={busy}
                  />
                  <p className="board-hint">
                    {applicant
                      ? 'Hover a perspective for the short reason. Click it for quoted evidence.'
                      : 'Click a perspective to turn it on or off. Hover to see what it looks for.'}
                  </p>
                </div>
                <SidePanel
                  tab={panelTab}
                  onTab={setPanelTab}
                  agents={agents}
                  enabledIds={enabled}
                  applicant={applicant}
                  openId={openId}
                  onOpen={setOpenId}
                  busy={busy}
                  canAdd={store.canAdd}
                  onToggle={onToggle}
                  onAdd={store.add}
                  onUpdate={store.update}
                  onRemove={store.remove}
                  onReset={store.reset}
                />
              </div>
            </section>
          )}

          {desk === 'dev' && (
            <section className="desk-section dev-section no-print">
              <h2 className="section-title">Prompts for each sub-agent</h2>
              <p className="section-sub">
                Template is the standing instruction. After you run a review, switch to{' '}
                <b>Sent to the model</b> to see the exact filled prompt each selected sub-agent received.
              </p>
              <DevDesk job={job} agents={agents} />
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
