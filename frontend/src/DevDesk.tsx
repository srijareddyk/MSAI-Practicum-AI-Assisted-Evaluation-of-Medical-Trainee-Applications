import { useEffect, useMemo, useState } from 'react'
import { fetchPromptCatalog } from './api'
import { READERS, readerById } from './readers'
import type { Job, PromptCatalog } from './types'

export default function DevDesk({ job }: { job: Job | null }) {
  const [catalog, setCatalog] = useState<PromptCatalog | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [source, setSource] = useState<'template' | 'sent'>('template')
  const [applicantIndex, setApplicantIndex] = useState(0)
  const [openId, setOpenId] = useState<string>(READERS[0].id)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    fetchPromptCatalog()
      .then(setCatalog)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Unable to load the prompt catalog'),
      )
  }, [])

  useEffect(() => {
    setApplicantIndex(0)
    setSource('template')
    setOpenId(READERS[0].id)
  }, [job?.id])

  useEffect(() => {
    const hasSent =
      job?.status === 'completed' &&
      job.applicants.some((item) => item.prompts_sent && Object.keys(item.prompts_sent).length > 0)
    if (hasSent) setSource('sent')
  }, [job?.id, job?.status])

  const applicant = job?.applicants[applicantIndex]
  const generation = catalog?.generation

  const agentPanels = useMemo(() => {
    if (!catalog) return []
    return READERS.map((reader) => {
      const spec = catalog.prompts.find((item) => item.id === reader.id)
      const sent = applicant?.prompts_sent?.[reader.id]
      const body = source === 'sent' ? sent || '' : spec?.template || ''
      return {
        reader,
        spec,
        body,
        sent: Boolean(sent),
        chars: body.length,
      }
    })
  }, [applicant, catalog, source])

  const excerpt =
    source === 'sent'
      ? applicant?.prompts_sent?.application_excerpt || ''
      : 'After a review, this panel shows the exact packet excerpt filled into {application_text} for every selected sub-agent.'

  const openPanel = agentPanels.find((panel) => panel.reader.id === openId) || agentPanels[0]

  const copy = async () => {
    if (!openPanel?.body) return
    await navigator.clipboard.writeText(openPanel.body)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1200)
  }

  if (error) return <div className="error-banner">{error}</div>
  if (!catalog || !openPanel) return <p className="empty-state">Loading sub-agent prompts…</p>

  return (
    <div className="dev-desk">
      <div className="dev-hero">
        <div>
          <p className="dev-kicker">Sub-agent prompts</p>
          <h3>Exact text sent to each reader</h3>
          <p>
            Every selected reader is a separate local model call. Open an agent below to see the full
            prompt template, or the filled prompt after a review finishes.
          </p>
        </div>
        <div className="dev-toolbar">
          <div className="dev-source" role="group" aria-label="Prompt source">
            <button
              type="button"
              className={source === 'template' ? 'selected' : ''}
              onClick={() => setSource('template')}
            >
              Template
            </button>
            <button
              type="button"
              className={source === 'sent' ? 'selected' : ''}
              onClick={() => setSource('sent')}
              disabled={!job || job.status !== 'completed'}
            >
              Sent to the model
            </button>
          </div>
          {source === 'sent' && job && job.applicants.length > 1 && (
            <div className="applicant-tabs">
              {job.applicants.map((item, index) => (
                <button
                  key={item.file}
                  type="button"
                  className={`tab ${index === applicantIndex ? 'active' : ''}`}
                  onClick={() => setApplicantIndex(index)}
                >
                  {item.applicant_name || item.file}
                </button>
              ))}
            </div>
          )}
          <button type="button" className="btn btn-ghost" onClick={copy} disabled={!openPanel.body}>
            {copied ? 'Copied' : 'Copy prompt'}
          </button>
        </div>
      </div>

      {generation && (
        <p className="dev-settings">
          Model <b>{generation.model}</b>
          {' · '}
          thinking {generation.think ? 'on' : 'off'}
          {' · '}
          context {generation.num_ctx}
          {' · '}
          JSON mode {generation.json_mode ? 'on' : 'off'}
          {' · '}
          kept loaded {generation.keep_alive}
          {openPanel.spec ? ` · up to ${openPanel.spec.max_tokens} new tokens` : ''}
          {source === 'sent' && openPanel.chars
            ? ` · ${openPanel.chars.toLocaleString()} characters in this call`
            : ''}
        </p>
      )}

      <div className="dev-agent-strip" role="tablist" aria-label="Sub-agents">
        {agentPanels.map((panel) => {
          const active = panel.reader.id === openPanel.reader.id
          const ran = source === 'sent' && panel.sent
          const skipped = source === 'sent' && !panel.sent
          return (
            <button
              key={panel.reader.id}
              type="button"
              role="tab"
              aria-selected={active}
              className={`dev-agent-chip ${active ? 'active' : ''} ${ran ? 'ran' : ''} ${skipped ? 'skipped' : ''}`}
              onClick={() => setOpenId(panel.reader.id)}
            >
              <strong>{panel.reader.short}</strong>
              <span>
                {source === 'template'
                  ? 'Template'
                  : ran
                    ? 'Prompt sent'
                    : 'Not called'}
              </span>
            </button>
          )
        })}
        <button
          type="button"
          role="tab"
          aria-selected={openId === 'excerpt'}
          className={`dev-agent-chip ${openId === 'excerpt' ? 'active' : ''}`}
          onClick={() => setOpenId('excerpt')}
        >
          <strong>Excerpt</strong>
          <span>Shared packet text</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={openId === 'rubric'}
          className={`dev-agent-chip ${openId === 'rubric' ? 'active' : ''}`}
          onClick={() => setOpenId('rubric')}
        >
          <strong>Colors</strong>
          <span>Shared rules</span>
        </button>
      </div>

      {openId === 'rubric' ? (
        <div className="dev-main">
          <div className="dev-main-head">
            <h3>Color rules shared by every sub-agent</h3>
            <p>These lines are embedded in each reader prompt. The product never assigns points.</p>
          </div>
          <pre className="dev-prompt">{catalog.rubric}</pre>
        </div>
      ) : openId === 'excerpt' ? (
        <div className="dev-main">
          <div className="dev-main-head">
            <h3>Packet excerpt</h3>
            <p>
              {source === 'sent' && applicant
                ? `Filled into every selected sub-agent for ${applicant.applicant_name || applicant.file}.`
                : 'Placeholder {application_text} is replaced with this excerpt at call time.'}
            </p>
          </div>
          <pre className="dev-prompt">{excerpt || 'Run a review to capture the excerpt that was sent.'}</pre>
        </div>
      ) : (
        <div className="dev-main">
          <div className="dev-main-head">
            <p className="evidence-label">{openPanel.reader.hint}</p>
            <h3>
              {openPanel.reader.label}
              <span className="dev-agent-id"> · {openPanel.reader.id}</span>
            </h3>
            <p>{readerById(openPanel.reader.id)?.detail}</p>
            <dl className="dev-role">
              <div>
                <dt>Reads</dt>
                <dd>{openPanel.reader.reads}</dd>
              </div>
              <div>
                <dt>Looks for</dt>
                <dd>{openPanel.reader.looksFor}</dd>
              </div>
              <div>
                <dt>Returns</dt>
                <dd>{openPanel.reader.returns}</dd>
              </div>
            </dl>
            {source === 'sent' && !openPanel.sent && (
              <p className="dev-vars">This sub-agent was not selected for the last review, so no prompt was sent.</p>
            )}
            {source === 'template' && openPanel.spec && (
              <p className="dev-vars">
                Placeholders: {openPanel.spec.variables.map((name) => `{${name}}`).join(', ')}
              </p>
            )}
          </div>
          <pre className="dev-prompt">
            {openPanel.body ||
              (source === 'sent'
                ? 'No prompt was sent for this sub-agent.'
                : 'Prompt template missing from the catalog.')}
          </pre>
        </div>
      )}
    </div>
  )
}
