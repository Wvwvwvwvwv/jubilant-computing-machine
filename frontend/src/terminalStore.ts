export interface TerminalEntry {
  id: string
  text: string
  stream?: 'stdout' | 'stderr' | 'status'
  timestamp: string
}

export interface TerminalState {
  title: string
  entries: TerminalEntry[]
  active: boolean
  updatedAt: string
}

const STORAGE_KEY = 'roampal_terminal_state'
const EVENT_NAME = 'roampal-terminal-update'

const defaultState: TerminalState = {
  title: 'Терминал готов',
  entries: [
    {
      id: 'ready',
      text: 'Ожидание новой команды из чата…',
      stream: 'status',
      timestamp: new Date().toISOString(),
    },
  ],
  active: false,
  updatedAt: new Date().toISOString(),
}

let memoryState: TerminalState = defaultState

function cloneState(state: TerminalState): TerminalState {
  return {
    ...state,
    entries: [...state.entries],
  }
}

export function loadTerminalState(): TerminalState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return cloneState(memoryState)
    const parsed = JSON.parse(raw)
    if (!parsed || !Array.isArray(parsed.entries)) return cloneState(memoryState)
    memoryState = {
      title: typeof parsed.title === 'string' ? parsed.title : defaultState.title,
      entries: parsed.entries,
      active: Boolean(parsed.active),
      updatedAt: typeof parsed.updatedAt === 'string' ? parsed.updatedAt : new Date().toISOString(),
    }
    return cloneState(memoryState)
  } catch {
    return cloneState(memoryState)
  }
}

function persist(state: TerminalState) {
  memoryState = cloneState(state)
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(memoryState))
  } catch {
    // ignore storage issues
  }
  window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: cloneState(memoryState) }))
}

export function subscribeTerminalState(callback: (state: TerminalState) => void) {
  const handler = (event: Event) => {
    const custom = event as CustomEvent<TerminalState>
    callback(custom.detail ? cloneState(custom.detail) : loadTerminalState())
  }
  window.addEventListener(EVENT_NAME, handler)
  return () => window.removeEventListener(EVENT_NAME, handler)
}

export function resetTerminalState(message: string = 'Ожидание новой команды из чата…') {
  persist({
    title: 'Терминал очищен',
    active: false,
    updatedAt: new Date().toISOString(),
    entries: [
      {
        id: `reset-${Date.now()}`,
        text: message,
        stream: 'status',
        timestamp: new Date().toISOString(),
      },
    ],
  })
}

export function createTerminalSession(title: string, introLines: Array<{ text: string; stream?: 'stdout' | 'stderr' | 'status' }> = []) {
  const now = new Date().toISOString()
  persist({
    title,
    active: true,
    updatedAt: now,
    entries: introLines.map((line, index) => ({
      id: `entry-${Date.now()}-${index}`,
      text: line.text,
      stream: line.stream ?? 'status',
      timestamp: new Date().toISOString(),
    })),
  })
}

export function appendTerminalEntry(text: string, stream: 'stdout' | 'stderr' | 'status' = 'stdout') {
  const current = loadTerminalState()
  const next: TerminalState = {
    ...current,
    active: current.active,
    updatedAt: new Date().toISOString(),
    entries: [
      ...current.entries,
      {
        id: `entry-${Date.now()}-${Math.random().toString(16).slice(2)}`,
        text,
        stream,
        timestamp: new Date().toISOString(),
      },
    ],
  }
  persist(next)
}

export function finishTerminalSession(summary?: string) {
  const current = loadTerminalState()
  const next = {
    ...current,
    active: false,
    updatedAt: new Date().toISOString(),
    entries: summary
      ? [
          ...current.entries,
          {
            id: `entry-${Date.now()}-finish`,
            text: summary,
            stream: 'status' as const,
            timestamp: new Date().toISOString(),
          },
        ]
      : current.entries,
  }
  persist(next)
}
