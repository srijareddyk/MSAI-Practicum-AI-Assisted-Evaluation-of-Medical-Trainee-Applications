import { useCallback, useEffect, useMemo, useState } from 'react'
import { READERS, type ReaderDef } from './readers'

/** Most agents the circle shows and one review runs (each is one model call). */
export const MAX_AGENTS = 10

/** What the backend needs to build an agent's prompt. Must match llm_score/components.py. */
export const BUILTIN_PROMPTS: Record<string, { title: string; focus: string }> = {
  statement: {
    title: 'Personal statement',
    focus: 'whether the personal statement gives a specific, credible reason for ophthalmology.',
  },
  letters: {
    title: 'Letters',
    focus: 'whether the letters give specific evidence about clinical judgment, skill, and teamwork.',
  },
  research: {
    title: 'Research',
    focus: "whether the research describes the applicant's own role, not just a list of titles.",
  },
  clinical: {
    title: 'Clinical record',
    focus:
      'what the clerkships and the MSPE say about clinical performance, including any ophthalmology rotation.',
  },
  commitment: {
    title: 'Ophthalmology commitment',
    focus:
      'whether ophthalmology shows up outside the statement, in electives, mentors, or longitudinal exposure.',
  },
}

export type AgentDef = ReaderDef & {
  /** Name used in the prompt ("You are the {title} reader"). */
  title: string
  /** What the agent reads and judges. The app adds color rules and output format. */
  focus: string
  builtIn: boolean
  edited: boolean
}

type Override = { short: string; title: string; focus: string }
type CustomAgent = { id: string; short: string; title: string; focus: string }

type Stored = {
  overrides: Record<string, Override>
  custom: CustomAgent[]
  enabled: string[]
}

const STORAGE_KEY = 'ophtho-review.agents.v1'
const DEFAULT_ENABLED = ['statement', 'letters', 'research', 'clinical']

function load(): Stored {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<Stored>
      return {
        overrides: parsed.overrides ?? {},
        custom: Array.isArray(parsed.custom) ? parsed.custom : [],
        enabled: Array.isArray(parsed.enabled) ? parsed.enabled : DEFAULT_ENABLED,
      }
    }
  } catch {
    /* storage blocked or corrupt: start from defaults */
  }
  return { overrides: {}, custom: [], enabled: DEFAULT_ENABLED }
}

function save(state: Stored) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    /* private mode: changes last until the page closes */
  }
}

function builtInAgent(reader: ReaderDef, override?: Override): AgentDef {
  const base = BUILTIN_PROMPTS[reader.id]
  if (!override) return { ...reader, ...base, builtIn: true, edited: false }
  return {
    ...reader,
    short: override.short,
    label: override.title,
    title: override.title,
    focus: override.focus,
    hint: 'Edited perspective',
    looksFor: override.focus,
    detail: 'This built-in perspective was edited in this browser. Reset it to go back to the original prompt.',
    builtIn: true,
    edited: true,
  }
}

function customAgent(agent: CustomAgent): AgentDef {
  return {
    id: agent.id,
    short: agent.short,
    label: agent.title,
    title: agent.title,
    focus: agent.focus,
    hint: 'Custom perspective',
    reads: 'The whole packet, with identifiers removed.',
    looksFor: agent.focus,
    returns: 'Green, yellow, or red, a short reason, and quoted snippets from the packet.',
    detail: 'A perspective added in this browser. It follows the same color, bias, and evidence rules as the built-in agents.',
    builtIn: false,
    edited: false,
  }
}

function newId(title: string, taken: Set<string>): string {
  const slug =
    title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 24) || 'perspective'
  let id = `c-${slug}`
  let n = 2
  while (taken.has(id)) id = `c-${slug}-${n++}`
  return id
}

export type AgentInput = { short: string; title: string; focus: string }

export function useAgents() {
  const [state, setState] = useState<Stored>(load)

  useEffect(() => save(state), [state])

  const agents = useMemo<AgentDef[]>(
    () => [
      ...READERS.map((reader) => builtInAgent(reader, state.overrides[reader.id])),
      ...state.custom.map(customAgent),
    ],
    [state.overrides, state.custom],
  )

  const enabled = useMemo(
    () => state.enabled.filter((id) => agents.some((agent) => agent.id === id)),
    [state.enabled, agents],
  )

  const toggle = useCallback((id: string) => {
    setState((s) => ({
      ...s,
      enabled: s.enabled.includes(id) ? s.enabled.filter((x) => x !== id) : [...s.enabled, id],
    }))
  }, [])

  const add = useCallback(
    (input: AgentInput): string | null => {
      if (READERS.length + state.custom.length >= MAX_AGENTS) return null
      const taken = new Set([...READERS.map((r) => r.id), ...state.custom.map((c) => c.id)])
      const id = newId(input.title, taken)
      setState((s) => ({ ...s, custom: [...s.custom, { id, ...input }], enabled: [...s.enabled, id] }))
      return id
    },
    [state.custom],
  )

  const update = useCallback((id: string, input: AgentInput) => {
    setState((s) => {
      if (READERS.some((r) => r.id === id)) {
        return { ...s, overrides: { ...s.overrides, [id]: input } }
      }
      return { ...s, custom: s.custom.map((c) => (c.id === id ? { id, ...input } : c)) }
    })
  }, [])

  const remove = useCallback((id: string) => {
    setState((s) => ({
      ...s,
      custom: s.custom.filter((c) => c.id !== id),
      enabled: s.enabled.filter((x) => x !== id),
    }))
  }, [])

  const reset = useCallback((id: string) => {
    setState((s) => {
      const overrides = { ...s.overrides }
      delete overrides[id]
      return { ...s, overrides }
    })
  }, [])

  return {
    agents,
    enabled,
    canAdd: agents.length < MAX_AGENTS,
    toggle,
    add,
    update,
    remove,
    reset,
  }
}

/** Payload for the analyze API. */
export function toAgentDefs(agents: AgentDef[]) {
  return agents.map((agent) => ({
    id: agent.id,
    title: agent.title,
    short: agent.short,
    focus: agent.focus,
  }))
}
