import { useState } from 'react'
import type { AgentDef } from './agents'
import type { ApplicantResult, ComponentRead, Opinion } from './types'

export const WORDS: Record<Opinion, string> = {
  green: 'Advance',
  yellow: 'Look again',
  red: 'Hold',
  split: 'Split',
}

/** Even spacing around the ring, starting at 12 o'clock. Units are % of the stage. */
function slotFor(index: number, count: number): { x: number; y: number } {
  const angle = -Math.PI / 2 + (index * 2 * Math.PI) / Math.max(count, 1)
  return { x: 50 + 40 * Math.cos(angle), y: 50 + 41 * Math.sin(angle) }
}

function arrowEnd(x: number, y: number): { x: number; y: number } {
  const toward = 0.42
  return { x: x + (50 - x) * toward, y: y + (50 - y) * toward }
}

export default function CircleBoard({
  agents,
  enabledIds,
  applicant,
  centerDetail,
  openId,
  onOpen,
  onToggle,
  disabled,
}: {
  agents: AgentDef[]
  enabledIds: string[]
  /** The finished result being shown, if any. */
  applicant?: ApplicantResult
  centerDetail: string
  openId: string | null
  onOpen: (id: string | null) => void
  onToggle: (id: string) => void
  disabled?: boolean
}) {
  const [hoverId, setHoverId] = useState<string | null>(null)
  const reads = new Map((applicant?.components ?? []).map((read) => [read.id, read]))
  const dense = agents.length > 8

  const onNode = (id: string, read: ComponentRead | undefined) => {
    if (read) {
      onOpen(openId === id ? null : id)
      return
    }
    if (!disabled) onToggle(id)
  }

  const hovered = hoverId ? agents.findIndex((agent) => agent.id === hoverId) : -1

  return (
    <div className="bias-stage" aria-label="Application in the center, perspectives around it">
      <div className="bias-ring" aria-hidden />
      <svg className="bias-arrows" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>
        {agents.map((agent, index) => {
          const slot = slotFor(index, agents.length)
          const end = arrowEnd(slot.x, slot.y)
          const read = reads.get(agent.id)
          const tone = read?.opinion ?? (enabledIds.includes(agent.id) ? 'waiting' : 'off')
          return (
            <line
              key={agent.id}
              x1={slot.x}
              y1={slot.y}
              x2={end.x}
              y2={end.y}
              className={`bias-arrow tone-${tone}`}
              vectorEffect="non-scaling-stroke"
            />
          )
        })}
      </svg>

      <div className="bias-center application-center">
        <span className="bias-center-label">Application</span>
        <strong>{applicant?.applicant_name || 'Applicant'}</strong>
        <p>{centerDetail}</p>
      </div>

      {agents.map((agent, index) => {
        const slot = slotFor(index, agents.length)
        const read = reads.get(agent.id)
        const selected = enabledIds.includes(agent.id)
        const tone = read?.opinion ?? (read?.error ? 'split' : selected ? 'waiting' : 'off')
        const status = read?.opinion
          ? WORDS[read.opinion]
          : read?.error
            ? 'No color'
            : selected
              ? 'On'
              : 'Off'
        return (
          <button
            key={agent.id}
            type="button"
            className={`bias-node side-node tone-${tone} ${openId === agent.id ? 'open' : ''} ${selected ? 'is-on' : ''} ${dense ? 'dense' : ''}`}
            style={{ left: `${slot.x}%`, top: `${slot.y}%` }}
            aria-pressed={selected}
            aria-describedby={hoverId === agent.id ? 'agent-tip' : undefined}
            onClick={() => onNode(agent.id, read)}
            onMouseEnter={() => setHoverId(agent.id)}
            onMouseLeave={() => setHoverId(null)}
            onFocus={() => setHoverId(agent.id)}
            onBlur={() => setHoverId(null)}
          >
            <span className="bias-status">{status}</span>
            <strong>{agent.short}</strong>
          </button>
        )
      })}

      {hovered >= 0 && (
        <Tip
          agent={agents[hovered]}
          read={reads.get(agents[hovered].id)}
          slot={slotFor(hovered, agents.length)}
          enabled={enabledIds.includes(agents[hovered].id)}
          disabled={disabled}
        />
      )}
    </div>
  )
}

function Tip({
  agent,
  read,
  slot,
  enabled,
  disabled,
}: {
  agent: AgentDef
  read?: ComponentRead
  slot: { x: number; y: number }
  enabled: boolean
  disabled?: boolean
}) {
  const below = slot.y < 50
  const tone = read?.opinion ?? 'split'
  let body: string
  let foot: string
  if (read) {
    body = read.reason || read.headline || read.error || 'No reason returned.'
    foot = 'Click for evidence'
  } else {
    body = agent.focus.charAt(0).toUpperCase() + agent.focus.slice(1)
    foot = disabled ? 'Review running' : enabled ? 'Click to turn off' : 'Click to turn on'
  }
  return (
    <div
      id="agent-tip"
      role="tooltip"
      className={`agent-tip ${below ? 'below' : 'above'} ${read ? `tone-${tone}` : ''}`}
      style={{ left: `${Math.min(Math.max(slot.x, 18), 82)}%`, top: `${slot.y}%` }}
    >
      {read?.opinion && <span className="agent-tip-word">{WORDS[read.opinion]}</span>}
      <p>{body}</p>
      <small>{foot}</small>
    </div>
  )
}
