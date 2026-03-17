import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

export type ChatRole = 'user' | 'assistant' | 'system'

export interface ChatMessage {
  id: string
  role: ChatRole
  content: string
  createdAt: number
}

export interface DialogItem {
  id: string
  title: string
  createdAt: number
  messages: ChatMessage[]
}

export interface TerminalLine {
  id: string
  ts: number
  stream: 'stdout' | 'stderr' | 'system'
  text: string
}

interface AppStateValue {
  dialogs: DialogItem[]
  activeDialogId: string
  setActiveDialogId: (id: string) => void
  createDialog: () => void
  deleteDialog: (id: string) => void
  appendDialogMessage: (dialogId: string, message: Omit<ChatMessage, 'id' | 'createdAt'>) => void
  terminalLines: TerminalLine[]
  appendTerminalLine: (line: Omit<TerminalLine, 'id' | 'ts'>) => void
  clearTerminal: () => void
  activeTab: 'chat' | 'terminal'
  setActiveTab: (tab: 'chat' | 'terminal') => void
  selectedModel: string
  setSelectedModel: (model: string) => void
  models: string[]
  addModel: (model: string) => void
  removeModel: (model: string) => void
}

const STORAGE_KEY = 'roampal_frontend_state_v3'

const AppStateContext = createContext<AppStateValue | null>(null)

const uid = () => `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

function loadInitialState() {
  const fallbackDialogId = uid()
  const fallback = {
    dialogs: [{ id: fallbackDialogId, title: 'Новый диалог', createdAt: Date.now(), messages: [] as ChatMessage[] }],
    activeDialogId: fallbackDialogId,
    terminalLines: [] as TerminalLine[],
    activeTab: 'chat' as const,
    selectedModel: 'default',
    models: ['default']
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return fallback
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed.dialogs) || parsed.dialogs.length === 0) return fallback
    return {
      dialogs: parsed.dialogs,
      activeDialogId: parsed.activeDialogId || parsed.dialogs[0].id,
      terminalLines: Array.isArray(parsed.terminalLines) ? parsed.terminalLines : [],
      activeTab: parsed.activeTab === 'terminal' ? 'terminal' : 'chat',
      selectedModel: parsed.selectedModel || 'default',
      models: Array.isArray(parsed.models) && parsed.models.length ? parsed.models : ['default']
    }
  } catch {
    return fallback
  }
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const initial = useMemo(loadInitialState, [])
  const [dialogs, setDialogs] = useState<DialogItem[]>(initial.dialogs)
  const [activeDialogId, setActiveDialogId] = useState(initial.activeDialogId)
  const [terminalLines, setTerminalLines] = useState<TerminalLine[]>(initial.terminalLines)
  const [activeTab, setActiveTab] = useState<'chat' | 'terminal'>(initial.activeTab as 'chat' | 'terminal')
  const [selectedModel, setSelectedModel] = useState<string>(initial.selectedModel)
  const [models, setModels] = useState<string[]>(initial.models)

  const persist = (next: Partial<ReturnType<typeof loadInitialState>>) => {
    const payload = {
      dialogs,
      activeDialogId,
      terminalLines,
      activeTab,
      selectedModel,
      models,
      ...next
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  }

  const createDialog = () => {
    const id = uid()
    const item: DialogItem = { id, title: 'Новый диалог', createdAt: Date.now(), messages: [] }
    const next = [item, ...dialogs]
    setDialogs(next)
    setActiveDialogId(id)
    persist({ dialogs: next, activeDialogId: id })
  }

  const deleteDialog = (id: string) => {
    const next = dialogs.filter((d) => d.id !== id)
    const safe = next.length ? next : [{ id: uid(), title: 'Новый диалог', createdAt: Date.now(), messages: [] }]
    const nextActive = safe.some((d) => d.id === activeDialogId) ? activeDialogId : safe[0].id
    setDialogs(safe)
    setActiveDialogId(nextActive)
    persist({ dialogs: safe, activeDialogId: nextActive })
  }

  const appendDialogMessage: AppStateValue['appendDialogMessage'] = (dialogId, message) => {
    const next = dialogs.map((d) => {
      if (d.id !== dialogId) return d
      const withMsg = [...d.messages, { ...message, id: uid(), createdAt: Date.now() }]
      const nextTitle = d.title === 'Новый диалог' && message.role === 'user'
        ? message.content.slice(0, 40) || d.title
        : d.title
      return { ...d, title: nextTitle, messages: withMsg }
    })
    setDialogs(next)
    persist({ dialogs: next })
  }

  const appendTerminalLine: AppStateValue['appendTerminalLine'] = (line) => {
    const next = [...terminalLines, { ...line, id: uid(), ts: Date.now() }].slice(-800)
    setTerminalLines(next)
    persist({ terminalLines: next })
  }

  const clearTerminal = () => {
    setTerminalLines([])
    persist({ terminalLines: [] })
  }

  const addModel = (model: string) => {
    const normalized = model.trim()
    if (!normalized || models.includes(normalized)) return
    const next = [normalized, ...models]
    setModels(next)
    setSelectedModel(normalized)
    persist({ models: next, selectedModel: normalized })
  }

  const removeModel = (model: string) => {
    const next = models.filter((m) => m !== model)
    const safe = next.length ? next : ['default']
    const nextSelected = safe.includes(selectedModel) ? selectedModel : safe[0]
    setModels(safe)
    setSelectedModel(nextSelected)
    persist({ models: safe, selectedModel: nextSelected })
  }

  return (
    <AppStateContext.Provider
      value={{
        dialogs,
        activeDialogId,
        setActiveDialogId,
        createDialog,
        deleteDialog,
        appendDialogMessage,
        terminalLines,
        appendTerminalLine,
        clearTerminal,
        activeTab,
        setActiveTab,
        selectedModel,
        setSelectedModel,
        models,
        addModel,
        removeModel
      }}
    >
      {children}
    </AppStateContext.Provider>
  )
}

export function useAppState() {
  const ctx = useContext(AppStateContext)
  if (!ctx) throw new Error('useAppState must be used inside AppStateProvider')
  return ctx
}
