import { useState } from 'react'
import { MAX_AGENTS, type AgentDef, type AgentInput } from './agents'
import { WORDS } from './CircleBoard'
import type { ApplicantResult, ComponentRead } from './types'

export type PanelTab = 'results' | 'perspectives'

type Props = {
  tab: PanelTab
  onTab: (tab: PanelTab) => void
  agents: AgentDef[]
  enabledIds: string[]
  applicant?: ApplicantResult
  openId: string | null
  onOpen: (id: string | null) => void
  busy: boolean
  canAdd: boolean
  onToggle: (id: string) => void
  onAdd: (input: AgentInput) => string | null
  onUpdate: (id: string, input: AgentInput) => void
  onRemove: (id: string) => void
  onReset: (id: string) => void
}

export default function SidePanel(props: Props) {
  const { tab, onTab, applicant } = props
  return (
    <aside className="side-panel" aria-label="Review details">
      <div className="side-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'results'}
          className={tab === 'results' ? 'active' : ''}
          onClick={() => onTab('results')}
        >
          Results
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'perspectives'}
          className={tab === 'perspectives' ? 'active' : ''}
          onClick={() => onTab('perspectives')}
        >
          Perspectives{' '}
          <span
            className="side-count"
            title={`${props.enabledIds.length} of ${props.agents.length} perspectives are on for the next review`}
          >
            {props.enabledIds.length}/{props.agents.length} on
          </span>
        </button>
      </div>
      <div className="side-body">
        {tab === 'results' ? (
          <Results applicant={applicant} openId={props.openId} onOpen={props.onOpen} onTab={onTab} />
        ) : (
          <Perspectives {...props} />
        )}
      </div>
    </aside>
  )
}

function Results({
  applicant,
  openId,
  onOpen,
  onTab,
}: {
  applicant?: ApplicantResult
  openId: string | null
  onOpen: (id: string | null) => void
  onTab: (tab: PanelTab) => void
}) {
  const reads = applicant?.components ?? []
  if (!applicant || !reads.length) {
    return (
      <div className="side-empty">
        <h3>No results yet</h3>
        <p>
          Upload a packet and press <b>Begin review</b>. Each perspective in the circle reads the packet
          and returns green, yellow, or red with quoted evidence.
        </p>
        <button type="button" className="btn btn-ghost" onClick={() => onTab('perspectives')}>
          Choose perspectives
        </button>
      </div>
    )
  }
  const open = openId ? reads.find((read) => read.id === openId) : undefined
  if (open) return <Evidence read={open} onBack={() => onOpen(null)} />

  const combined = applicant.combined
  return (
    <div className="results-summary">
      {combined && (
        <div className={`combined tone-${combined.opinion}`}>
          <span className={`evidence-chip tone-${combined.opinion}`}>{WORDS[combined.opinion]}</span>
          <p>{combined.summary}</p>
        </div>
      )}
      <ul className="result-list">
        {reads.map((read) => {
          const tone = read.opinion ?? 'split'
          return (
            <li key={read.id}>
              <button type="button" className={`result-row tone-${tone}`} onClick={() => onOpen(read.id)}>
                <span className={`dot tone-${tone}`} aria-hidden />
                <span className="result-text">
                  <strong>
                    {read.short}
                    <em>{read.opinion ? WORDS[read.opinion] : 'No color'}</em>
                  </strong>
                  <span>{read.reason || read.headline || read.error}</span>
                </span>
                <span className="chev" aria-hidden>
                  ›
                </span>
              </button>
            </li>
          )
        })}
      </ul>
      <p className="side-note">Click a perspective here or in the circle for its quoted evidence.</p>
    </div>
  )
}

function Evidence({ read, onBack }: { read: ComponentRead; onBack: () => void }) {
  const tone = read.opinion ?? 'split'
  return (
    <article className={`evidence-panel tone-${tone}`}>
      <button type="button" className="back-link" onClick={onBack}>
        ‹ All results
      </button>
      <header>
        <div>
          <p className="evidence-label">{read.short}</p>
          <h3>{read.title}</h3>
        </div>
        <span className={`evidence-chip tone-${tone}`}>{read.opinion ? WORDS[read.opinion] : 'No color'}</span>
      </header>
      {read.error && <div className="error-banner">{read.error}</div>}
      {read.reason && <p className="evidence-reason">{read.reason}</p>}
      {read.headline && <p className="evidence-headline">{read.headline}</p>}
      {read.evidence.length > 0 && (
        <div className="citation-list">
          {read.evidence.map((line) => (
            <blockquote key={line} className="citation">
              <p>{line}</p>
              <cite>From the application · {read.title}</cite>
            </blockquote>
          ))}
        </div>
      )}
      {read.concern && (
        <p className="evidence-concern">
          <span>Concern</span>
          {read.concern}
        </p>
      )}
    </article>
  )
}

function Perspectives({
  agents,
  enabledIds,
  busy,
  canAdd,
  onToggle,
  onAdd,
  onUpdate,
  onRemove,
  onReset,
}: Props) {
  // null = closed, 'new' = adding, otherwise the id being edited
  const [editing, setEditing] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const editingAgent = agents.find((agent) => agent.id === editing)

  if (editing) {
    return (
      <AgentForm
        initial={editingAgent}
        onCancel={() => setEditing(null)}
        onSave={(input) => {
          if (editing === 'new') onAdd(input)
          else onUpdate(editing, input)
          setEditing(null)
        }}
      />
    )
  }

  return (
    <div className="perspectives">
      <div className="perspectives-head">
        <p>
          Turn perspectives on or off for the next review. At least two must be on. Each one is a separate
          model call.
        </p>
        <button
          type="button"
          className="btn btn-primary"
          disabled={busy || !canAdd}
          onClick={() => setEditing('new')}
        >
          + Add perspective
        </button>
        {!canAdd && <small className="side-note">The circle holds up to {MAX_AGENTS} perspectives.</small>}
      </div>
      <ul className="perspective-list">
        {agents.map((agent) => {
          const on = enabledIds.includes(agent.id)
          return (
            <li key={agent.id} className={`perspective ${on ? 'on' : ''}`}>
              <div className="perspective-top">
                <label className="switch">
                  <input
                    type="checkbox"
                    checked={on}
                    disabled={busy}
                    onChange={() => onToggle(agent.id)}
                    aria-label={`Include ${agent.title}`}
                  />
                  <span aria-hidden />
                </label>
                <div className="perspective-name">
                  <strong>{agent.title}</strong>
                  <span className="perspective-tag">
                    {agent.builtIn ? (agent.edited ? 'Built-in · edited' : 'Built-in') : 'Custom'}
                  </span>
                </div>
              </div>
              <p className="perspective-focus">{agent.focus}</p>
              {confirmDelete === agent.id ? (
                <div className="perspective-actions confirm">
                  <span>Delete “{agent.short}”?</span>
                  <button
                    type="button"
                    className="link-btn danger"
                    onClick={() => {
                      onRemove(agent.id)
                      setConfirmDelete(null)
                    }}
                  >
                    Delete
                  </button>
                  <button type="button" className="link-btn" onClick={() => setConfirmDelete(null)}>
                    Keep
                  </button>
                </div>
              ) : (
                <div className="perspective-actions">
                  <button type="button" className="link-btn" disabled={busy} onClick={() => setEditing(agent.id)}>
                    Edit
                  </button>
                  {agent.builtIn && agent.edited && (
                    <button type="button" className="link-btn" disabled={busy} onClick={() => onReset(agent.id)}>
                      Reset to original
                    </button>
                  )}
                  {!agent.builtIn && (
                    <button
                      type="button"
                      className="link-btn danger"
                      disabled={busy}
                      onClick={() => setConfirmDelete(agent.id)}
                    >
                      Delete
                    </button>
                  )}
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function AgentForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: AgentDef
  onSave: (input: AgentInput) => void
  onCancel: () => void
}) {
  const [title, setTitle] = useState(initial?.title ?? '')
  const [short, setShort] = useState(initial?.short ?? '')
  const [focus, setFocus] = useState(initial?.focus ?? '')
  const [shortTouched, setShortTouched] = useState(Boolean(initial))
  const circleName = shortTouched ? short : title.split(/\s+/)[0] ?? ''
  const valid = title.trim().length > 1 && focus.trim().length > 9 && circleName.trim().length > 0

  return (
    <form
      className="agent-form"
      onSubmit={(e) => {
        e.preventDefault()
        if (!valid) return
        onSave({ title: title.trim(), short: circleName.trim(), focus: focus.trim() })
      }}
    >
      <h3>{initial ? `Edit ${initial.title}` : 'Add a perspective'}</h3>
      <label className="form-field">
        <span>Name</span>
        <input
          type="text"
          value={title}
          maxLength={60}
          placeholder="e.g. Leadership and teaching"
          onChange={(e) => setTitle(e.target.value)}
          autoFocus
        />
      </label>
      <label className="form-field">
        <span>Label in the circle</span>
        <input
          type="text"
          value={circleName}
          maxLength={16}
          placeholder="e.g. Leadership"
          onChange={(e) => {
            setShortTouched(true)
            setShort(e.target.value)
          }}
        />
        <small>Keep it to one or two words so it fits the circle.</small>
      </label>
      <label className="form-field">
        <span>What should it look for?</span>
        <textarea
          value={focus}
          rows={5}
          maxLength={1000}
          placeholder="e.g. whether the applicant has led teams, taught peers, or organized projects, with concrete examples."
          onChange={(e) => setFocus(e.target.value)}
        />
        <small>
          Describe what this perspective should judge. The app adds the green / yellow / red rules, the no-bias
          rules, the quoted-evidence rules, and the output format for you. Names and contact details are
          removed from the packet before it is sent.
        </small>
      </label>
      <div className="form-actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={!valid}>
          {initial ? 'Save changes' : 'Add to circle'}
        </button>
      </div>
    </form>
  )
}
