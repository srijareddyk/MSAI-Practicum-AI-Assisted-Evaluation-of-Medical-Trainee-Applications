import { useEffect, useState } from 'react'
import { READERS } from './readers'
import type { ComponentRead, Job, Opinion } from './types'

const WORDS: Record<Opinion, string> = {
  green: 'Advance',
  yellow: 'Look again',
  red: 'Hold',
  split: 'Split',
}

const SLOTS: Record<string, { x: number; y: number }> = {
  statement: { x: 50, y: 8 },
  letters: { x: 88, y: 28 },
  research: { x: 88, y: 72 },
  clinical: { x: 50, y: 92 },
  academics: { x: 12, y: 72 },
  commitment: { x: 12, y: 28 },
}

function arrowEnd(x: number, y: number): { x: number; y: number } {
  const toward = 0.38
  return {
    x: x + (50 - x) * toward,
    y: y + (50 - y) * toward,
  }
}

export function prettyPacketName(raw: string): string {
  const stem = raw.replace(/\.pdf$/i, '')
  const beforeAu = stem.split(/_AU\d+/i)[0] || stem
  if (beforeAu.includes(',_') || beforeAu.includes(',')) {
    const [last, first] = beforeAu.split(/,_?/)
    const clean = (value: string) => value.replace(/_/g, ' ').trim()
    if (last && first) return `${clean(first)} ${clean(last)}`
  }
  return beforeAu.replace(/_/g, ' ').trim() || 'Application'
}

export default function CircleBoard({
  job,
  centerLabel,
  centerDetail,
  selectedIds,
  onToggle,
  disabled,
}: {
  job: Job | null
  centerLabel: string
  centerDetail: string
  selectedIds: string[]
  onToggle: (id: string) => void
  disabled?: boolean
}) {
  const [applicantIndex, setApplicantIndex] = useState(0)
  const [openId, setOpenId] = useState<string | null>(null)
  const applicant = job?.status === 'completed' ? job.applicants[applicantIndex] : undefined
  const reads = new Map((applicant?.components ?? []).map((read) => [read.id, read]))
  const open = openId ? reads.get(openId) ?? null : null
  const title =
    applicant?.applicant_name ||
    (centerLabel && centerLabel !== 'No packet yet' ? prettyPacketName(centerLabel) : 'No packet yet')

  useEffect(() => {
    setApplicantIndex(0)
    setOpenId(null)
  }, [job?.id])

  const onNode = (id: string, read: ComponentRead | undefined) => {
    if (read?.opinion || read?.error) {
      setOpenId(openId === id ? null : id)
      return
    }
    if (!disabled) onToggle(id)
  }

  return (
    <div className="bias-wrap">
      {job && job.applicants.length > 1 && (
        <div className="applicant-tabs" aria-label="Applications in this review">
          {job.applicants.map((item, index) => (
            <button
              key={item.file}
              type="button"
              className={`tab ${index === applicantIndex ? 'active' : ''}`}
              onClick={() => {
                setApplicantIndex(index)
                setOpenId(null)
              }}
            >
              {item.applicant_name || prettyPacketName(item.file)}
            </button>
          ))}
        </div>
      )}

      <div className="bias-stage" aria-label="Application in the center, readers at the sides">
        <div className="bias-ring" aria-hidden />
        <svg className="bias-arrows" viewBox="0 0 100 100" aria-hidden>
          {READERS.map((reader) => {
            const slot = SLOTS[reader.id]
            const end = arrowEnd(slot.x, slot.y)
            const read = reads.get(reader.id)
            const tone = read?.opinion ?? (selectedIds.includes(reader.id) ? 'waiting' : 'off')
            return (
              <line
                key={reader.id}
                x1={slot.x}
                y1={slot.y}
                x2={end.x}
                y2={end.y}
                className={`bias-arrow tone-${tone}`}
              />
            )
          })}
        </svg>

        <div className="bias-center application-center">
          <span className="bias-center-label">Application</span>
          <strong title={applicant?.file || centerLabel}>{title}</strong>
          <p>{centerDetail}</p>
        </div>

        {READERS.map((reader) => {
          const slot = SLOTS[reader.id]
          const read = reads.get(reader.id)
          const selected = selectedIds.includes(reader.id)
          const tone = read?.opinion ?? (selected ? 'waiting' : 'off')
          const opened = openId === reader.id
          const status = read?.opinion ? WORDS[read.opinion] : selected ? 'On' : 'Off'
          return (
            <button
              key={reader.id}
              type="button"
              className={`bias-node side-node tone-${tone} ${opened ? 'open' : ''} ${selected ? 'is-on' : ''}`}
              style={{ left: `${slot.x}%`, top: `${slot.y}%` }}
              aria-pressed={selected || opened}
              title={reader.hint}
              onClick={() => onNode(reader.id, read)}
            >
              <span className="bias-status">{status}</span>
              <strong>{reader.short}</strong>
            </button>
          )
        })}
      </div>

      {open && <Evidence read={open} />}
    </div>
  )
}

function Evidence({ read }: { read: ComponentRead }) {
  const tone = read.opinion ?? 'split'
  return (
    <article className={`evidence-panel tone-${tone}`}>
      <header>
        <div>
          <p className="evidence-label">{read.short}</p>
          <h3>{read.title}</h3>
        </div>
        <span className={`evidence-chip tone-${tone}`}>
          {read.opinion ? WORDS[read.opinion] : 'No color'}
        </span>
      </header>
      {read.error && <div className="error-banner">{read.error}</div>}
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
