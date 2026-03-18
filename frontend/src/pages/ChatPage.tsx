import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, ThumbsUp, ThumbsDown, Mic, Square } from 'lucide-react'
import { chatAPI } from '../api/client'
import { appendTerminalEntry, createTerminalSession, finishTerminalSession } from '../terminalStore'

interface Message {
  role: 'user' | 'assistant'
  content: string
  id?: string
}

interface ChatDraftState {
  messages: Message[]
  useMemory: boolean
  input: string
}

const CHAT_MESSAGES_KEY = 'chat_messages'
const CHAT_USE_MEMORY_KEY = 'chat_use_memory'
const CHAT_INPUT_KEY = 'chat_input'

let chatDraftState: ChatDraftState | null = null

function loadMessages(): Message[] {
  if (chatDraftState) {
    return chatDraftState.messages
  }

  try {
    const saved = localStorage.getItem(CHAT_MESSAGES_KEY)
    const parsed = saved ? JSON.parse(saved) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function loadUseMemory(): boolean {
  if (chatDraftState) {
    return chatDraftState.useMemory
  }

  try {
    const saved = localStorage.getItem(CHAT_USE_MEMORY_KEY)
    return saved ? Boolean(JSON.parse(saved)) : true
  } catch {
    return true
  }
}

function loadInput(): string {
  if (chatDraftState) {
    return chatDraftState.input
  }

  try {
    return localStorage.getItem(CHAT_INPUT_KEY) || ''
  } catch {
    return ''
  }
}

function persistState(messages: Message[], useMemory: boolean, input: string) {
  chatDraftState = { messages, useMemory, input }

  try {
    localStorage.setItem(CHAT_MESSAGES_KEY, JSON.stringify(messages))
    localStorage.setItem(CHAT_USE_MEMORY_KEY, JSON.stringify(useMemory))
    localStorage.setItem(CHAT_INPUT_KEY, input)
  } catch {
    // ignore storage errors (quota/private mode)
  }
}

function inferAutonomousMode(prompt: string): 'off' | 'auto' {
  const lowered = prompt.toLowerCase()
  const actionMarkers = ['установ', 'скачай', 'запусти', 'выполни', 'install', 'download', 'run ', 'execute', 'pkg install', 'apt install', 'pip install']
  const researchMarkers = ['найди', 'поищи', 'резюме', 'summary', 'summar', 'обзор', 'расскажи', 'прочитай', 'readme', 'github.com', 'http://', 'https://']

  if (actionMarkers.some((marker) => lowered.includes(marker))) {
    return 'auto'
  }

  if (researchMarkers.some((marker) => lowered.includes(marker))) {
    return 'off'
  }

  return 'auto'
}

export default function ChatPage() {
  const navigate = useNavigate()
  const [messages, setMessages] = useState<Message[]>(loadMessages)
  const [input, setInput] = useState(loadInput)
  const [loading, setLoading] = useState(false)
  const [useMemory, setUseMemory] = useState<boolean>(loadUseMemory)
  const [isDictating, setIsDictating] = useState(false)

  const messagesRef = useRef(messages)
  const useMemoryRef = useRef(useMemory)
  const inputRef = useRef(input)
  const recognitionRef = useRef<any>(null)

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
    }
  }, [])

  const updateMessages = (next: Message[] | ((prev: Message[]) => Message[])) => {
    const computed = typeof next === 'function' ? (next as (p: Message[]) => Message[])(messagesRef.current) : next
    messagesRef.current = computed
    persistState(computed, useMemoryRef.current, inputRef.current)
    setMessages(computed)
  }

  const updateUseMemory = (next: boolean) => {
    useMemoryRef.current = next
    setUseMemory(next)
    persistState(messagesRef.current, next, inputRef.current)
  }

  const updateInput = (next: string) => {
    inputRef.current = next
    setInput(next)
    persistState(messagesRef.current, useMemoryRef.current, next)
  }

  const stopDictation = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    setIsDictating(false)
  }

  const startDictation = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      updateMessages(prev => [...prev, {
        role: 'assistant',
        content: '❌ Браузер не поддерживает SpeechRecognition для диктовки в чат.'
      }])
      return
    }

    try {
      const rec = new SpeechRecognition()
      rec.lang = 'ru-RU'
      rec.interimResults = true
      rec.maxAlternatives = 1
      rec.continuous = true

      let lastSegment = ''
      rec.onresult = (event: any) => {
        const parts: string[] = []
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          parts.push(event.results[i][0].transcript)
        }
        const segment = parts.join(' ').trim()
        if (!segment) return

        const base = inputRef.current.endsWith(lastSegment)
          ? inputRef.current.slice(0, inputRef.current.length - lastSegment.length).trim()
          : inputRef.current
        const nextInput = [base, segment].filter(Boolean).join(' ').trim()
        lastSegment = segment
        updateInput(nextInput)
      }

      rec.onerror = (event: any) => {
        setIsDictating(false)
        updateMessages(prev => [...prev, {
          role: 'assistant',
          content: `❌ Ошибка диктовки: ${event?.error || 'unknown'}`
        }])
      }
      rec.onend = () => {
        setIsDictating(false)
        recognitionRef.current = null
      }

      recognitionRef.current = rec
      rec.start()
      setIsDictating(true)
    } catch (e: any) {
      setIsDictating(false)
      updateMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ Не удалось запустить диктовку: ${e?.message || 'unknown'}`
      }])
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const prompt = input.trim()
    const autonomousMode = inferAutonomousMode(prompt)
    const sandboxModeLabel = autonomousMode === 'off' ? 'Sandbox: пропущен для research-only запроса' : 'Sandbox: auto'
    const userMessage: Message = { role: 'user', content: prompt }
    const nextMessages = [...messagesRef.current, userMessage]

    updateMessages(nextMessages)
    updateInput('')
    setLoading(true)

    createTerminalSession(`Автозапуск для: ${prompt}`, [
      { text: '$ roampal chat --web-search on --sandbox auto', stream: 'status' },
      { text: `> ${prompt}`, stream: 'stdout' },
      { text: 'Подготовка запроса без ручного подтверждения…', stream: 'status' },
      { text: 'Web search: enabled', stream: 'status' },
      { text: sandboxModeLabel, stream: 'status' },
      { text: 'Terminal attached to current chat run.', stream: 'status' },
    ])
    navigate('/terminal')

    try {
      appendTerminalEntry('Запрос отправлен в /api/chat/…', 'status')
      const response = await chatAPI.send(nextMessages, useMemoryRef.current, {
        autonomousMode,
        webSearch: true
      })

      if (response.autonomous?.triggered) {
        appendTerminalEntry(`task_id=${response.autonomous.task_id || 'n/a'}`, 'status')
        appendTerminalEntry(`language=${response.autonomous.language || 'n/a'} exit_code=${String(response.autonomous.exit_code ?? 'n/a')}`, 'status')
        if (response.autonomous.stdout) {
          appendTerminalEntry(response.autonomous.stdout, 'stdout')
        }
        if (response.autonomous.stderr) {
          appendTerminalEntry(response.autonomous.stderr, 'stderr')
        }
        appendTerminalEntry(`status=${response.autonomous.status || 'unknown'}`, response.autonomous.exit_code === 0 ? 'status' : 'stderr')
      } else {
        appendTerminalEntry(autonomousMode === 'off' ? 'Sandbox пропущен: research-only запрос обработан через web/context chat.' : 'Sandbox не запускался: backend обработал запрос как обычный chat-response.', 'status')
      }

      finishTerminalSession('Сессия завершена.')
      updateMessages(prev => [...prev, {
        role: 'assistant',
        content: response.response,
        id: response.interaction_id
      }])
    } catch (error: any) {
      console.error('Chat error:', error)
      const detail = error?.response?.data?.detail
      const message = detail ? `❌ ${detail}` : '❌ Ошибка соединения с сервером'
      appendTerminalEntry(message, 'stderr')
      finishTerminalSession('Сессия завершена с ошибкой.')
      updateMessages(prev => [...prev, {
        role: 'assistant',
        content: message
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = async (messageId: string, helpful: boolean) => {
    try {
      await chatAPI.feedback(messageId, helpful)
    } catch (error) {
      console.error('Feedback error:', error)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0b0b0c' }}>
      <div style={{
        padding: '1rem 1rem 0.5rem',
        borderBottom: '1px solid #1f2329',
        background: 'linear-gradient(180deg, rgba(15,16,18,1) 0%, rgba(11,11,12,1) 100%)'
      }}>
        <div style={{ fontSize: '0.95rem', color: '#d8dee9', fontWeight: 600 }}>Авто-чат</div>
        <div style={{ marginTop: '0.35rem', fontSize: '0.82rem', color: '#8b93a1' }}>
          Web search и sandbox включаются автоматически, а live-лог уходит во вкладку «Терминал».
        </div>
      </div>

      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%'
            }}
          >
            <div style={{
              background: msg.role === 'user' ? 'linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%)' : '#17191d',
              border: msg.role === 'user' ? '1px solid rgba(96, 165, 250, 0.28)' : '1px solid #23272f',
              padding: '0.85rem 1rem',
              borderRadius: '1rem',
              color: '#f3f4f6',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              boxShadow: '0 10px 25px rgba(0, 0, 0, 0.18)'
            }}>
              {msg.content}
            </div>

            {msg.role === 'assistant' && msg.id && (
              <div style={{
                display: 'flex',
                gap: '0.5rem',
                marginTop: '0.5rem',
                fontSize: '0.875rem'
              }}>
                <button
                  onClick={() => handleFeedback(msg.id!, true)}
                  style={{
                    background: 'transparent',
                    border: '1px solid #2a3038',
                    borderRadius: '0.6rem',
                    padding: '0.35rem 0.6rem',
                    color: '#8b93a1',
                    cursor: 'pointer'
                  }}
                >
                  <ThumbsUp size={14} />
                </button>
                <button
                  onClick={() => handleFeedback(msg.id!, false)}
                  style={{
                    background: 'transparent',
                    border: '1px solid #2a3038',
                    borderRadius: '0.6rem',
                    padding: '0.35rem 0.6rem',
                    color: '#8b93a1',
                    cursor: 'pointer'
                  }}
                >
                  <ThumbsDown size={14} />
                </button>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ alignSelf: 'flex-start' }}>
            <div style={{
              background: '#17191d',
              border: '1px solid #23272f',
              padding: '0.75rem 1rem',
              borderRadius: '1rem',
              color: '#d1d5db'
            }}>
              Выполняю запрос, смотри live-лог во вкладке «Терминал»…
            </div>
          </div>
        )}
      </div>

      <div style={{
        padding: '1rem',
        borderTop: '1px solid #1f2329',
        display: 'flex',
        gap: '0.5rem',
        alignItems: 'center',
        background: '#101113'
      }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: '#c7ced9' }}>
          <input
            type="checkbox"
            checked={useMemory}
            onChange={(e) => updateUseMemory(e.target.checked)}
          />
          Память
        </label>

        <input
          type="text"
          value={input}
          onChange={(e) => updateInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Напиши задачу — web search и sandbox включатся автоматически"
          style={{
            flex: 1,
            background: '#17191d',
            border: '1px solid #2a3038',
            borderRadius: '0.9rem',
            padding: '0.85rem 1rem',
            color: '#fff',
            outline: 'none'
          }}
        />

        <button
          onClick={isDictating ? stopDictation : startDictation}
          style={{
            background: isDictating ? '#dc2626' : '#1f2937',
            border: '1px solid #2a3038',
            borderRadius: '0.9rem',
            padding: '0.8rem',
            cursor: 'pointer',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title={isDictating ? 'Остановить диктовку' : 'Начать диктовку'}
        >
          {isDictating ? <Square size={18} /> : <Mic size={18} />}
        </button>

        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          style={{
            background: loading || !input.trim() ? '#1e3a8a' : '#2563eb',
            border: 'none',
            borderRadius: '0.9rem',
            padding: '0.85rem 1rem',
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            opacity: loading || !input.trim() ? 0.65 : 1
          }}
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
