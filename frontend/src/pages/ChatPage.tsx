import { useMemo, useRef, useState } from 'react'
import { chatAPI, onlineAPI, sandboxAPI, voiceAPI } from '../api/client'
import { useAppState } from '../state/AppState'

const AGENT_PROMPT = [
  'Ты локальный автономный агент Roampal.',
  'Никакого ручного подтверждения: сам выбирай web_search и sandbox при любых action-oriented запросах.',
  'Если задача содержит поиск/скачивание/анализ/установку/изменение/запуск/проверку, сначала собери контекст, затем выполни действие и верни итог.',
  'Пиши кратко: шаги, результат, риски.'
].join('\n')

const ACTION_RE = /(найди|скачай|поищи|посмотри|уточни|установи|конвертируй|измени|запустить|запусти|проверь|разбери|проанализируй|search|download|install|convert|run|analy[sz]e)/i

type BrowserRecognition = {
  lang: string
  interimResults: boolean
  maxAlternatives: number
  continuous: boolean
  onresult: ((event: any) => void) | null
  onerror: ((event: any) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

function safeSpeak(text: string) {
  if (!('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text.slice(0, 400))
  utterance.lang = 'ru-RU'
  window.speechSynthesis.speak(utterance)
}

export default function ChatPage() {
  const {
    dialogs,
    activeDialogId,
    appendDialogMessage,
    appendTerminalLine,
    setActiveTab,
    selectedModel
  } = useAppState()

  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [voiceSessionId, setVoiceSessionId] = useState<string | null>(null)
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef<BrowserRecognition | null>(null)

  const activeDialog = useMemo(() => dialogs.find((d) => d.id === activeDialogId), [dialogs, activeDialogId])
  const messages = activeDialog?.messages || []

  const runSandboxWithPolling = async (code: string, language: string = 'python', timeout = 120) => {
    let running = true
    const pollId = window.setInterval(() => {
      if (!running) return
      appendTerminalLine({ stream: 'system', text: '...sandbox still running (poll: 1s)' })
    }, 1000)

    try {
      const result = await sandboxAPI.execute(code, language, timeout)
      appendTerminalLine({ stream: result.exit_code === 0 ? 'stdout' : 'stderr', text: `exit_code=${result.exit_code}` })
      if (result.stdout) appendTerminalLine({ stream: 'stdout', text: result.stdout })
      if (result.stderr) appendTerminalLine({ stream: 'stderr', text: result.stderr })
      return result
    } finally {
      running = false
      window.clearInterval(pollId)
    }
  }

  const executeAgentPipeline = async (userText: string) => {
    const triggered = ACTION_RE.test(userText)
    if (!triggered) return { triggered: false }

    setActiveTab('terminal')
    appendTerminalLine({ stream: 'system', text: `[agent] trigger detected: ${userText}` })

    const search = await onlineAPI.search(userText, 3)
    const results = Array.isArray(search?.results) ? search.results : []
    appendTerminalLine({ stream: 'system', text: `[agent] web_search returned ${results.length} items` })

    const scriptLines = [
      "import json",
      "print('AGENT: starting automated analysis')",
      `query = ${JSON.stringify(userText)}`,
      `results = ${JSON.stringify(results)}`,
      "print('QUERY:', query)",
      "for idx, item in enumerate(results, 1):",
      "    title = item.get('title', 'Result')",
      "    url = item.get('url', '')",
      "    print(f'[{idx}] {title} -> {url}')",
      "print('AGENT: completed analysis')"
    ]

    const sandbox = await runSandboxWithPolling(scriptLines.join('\n'))
    return { triggered: true, results, sandbox }
  }

  const sendMessage = async (rawText?: string, source: 'text' | 'voice' = 'text') => {
    const content = (rawText ?? input).trim()
    if (!content || loading || !activeDialog) return

    appendDialogMessage(activeDialog.id, { role: 'user', content })
    if (source === 'text') setInput('')
    setLoading(true)

    try {
      const agentContext = await executeAgentPipeline(content)

      const dialogNow = dialogs.find((d) => d.id === activeDialog.id) || activeDialog
      const payloadMessages = [
        { role: 'system', content: AGENT_PROMPT },
        { role: 'system', content: `Текущая модель: ${selectedModel}` },
        ...dialogNow.messages.map((m) => ({ role: m.role, content: m.content }))
      ]

      if (agentContext.triggered) {
        const summary = {
          search_count: agentContext.results.length,
          sandbox_exit_code: agentContext.sandbox?.exit_code,
          sandbox_stdout_tail: String(agentContext.sandbox?.stdout || '').slice(-500),
          sandbox_stderr_tail: String(agentContext.sandbox?.stderr || '').slice(-500)
        }
        payloadMessages.push({ role: 'system', content: `AGENT_TOOL_CONTEXT: ${JSON.stringify(summary)}` })
      }

      const response = await chatAPI.send(payloadMessages, true)
      const text = response?.response || 'Пустой ответ от модели.'
      appendDialogMessage(activeDialog.id, { role: 'assistant', content: text })
      safeSpeak(text)
    } catch (error: any) {
      appendDialogMessage(activeDialog.id, { role: 'assistant', content: `❌ ${error?.response?.data?.detail || error?.message || 'chat error'}` })
    } finally {
      setLoading(false)
    }
  }

  const toggleVoice = async () => {
    if (listening) {
      recognitionRef.current?.stop()
      setListening(false)
      if (voiceSessionId) await voiceAPI.stopSession(voiceSessionId)
      setVoiceSessionId(null)
      return
    }

    const session = await voiceAPI.startSession('duplex', 'female')
    setVoiceSessionId(session.voice_session_id)
    await voiceAPI.verifyMicrophone(session.voice_session_id, true, 'browser_speech', 'local_whisper_cpp control-plane active')

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      appendDialogMessage(activeDialogId, { role: 'assistant', content: '❌ SpeechRecognition not supported in this browser.' })
      return
    }

    const rec: BrowserRecognition = new SpeechRecognition()
    rec.lang = 'ru-RU'
    rec.interimResults = false
    rec.maxAlternatives = 1
    rec.continuous = true
    rec.onresult = (event: any) => {
      const transcript = event.results?.[event.results.length - 1]?.[0]?.transcript?.trim()
      if (transcript) void sendMessage(transcript, 'voice')
    }
    rec.onerror = () => setListening(false)
    rec.onend = () => setListening(false)
    rec.start()
    recognitionRef.current = rec
    setListening(true)
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((msg) => (
          <div key={msg.id} className={`max-w-[85%] rounded px-3 py-2 text-sm whitespace-pre-wrap ${msg.role === 'user' ? 'ml-auto bg-blue-600' : 'bg-neutral-800'}`}>
            {msg.content}
          </div>
        ))}
      </div>

      <div className="border-t border-neutral-800 p-3 flex gap-2">
        <button
          onClick={() => void toggleVoice()}
          className={`rounded px-3 py-2 text-sm ${listening ? 'bg-red-600' : 'bg-neutral-700'}`}
          title="PTT/continuous voice"
        >
          {listening ? '🎙️ stop' : '🎤 voice'}
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void sendMessage()
          }}
          placeholder="Введите сообщение или команду..."
          className="min-w-0 flex-1 rounded border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm"
        />
        <button
          disabled={loading}
          onClick={() => void sendMessage()}
          className="rounded bg-blue-600 px-4 py-2 text-sm disabled:opacity-60"
        >
          {loading ? '...' : 'Отправить'}
        </button>
      </div>
    </div>
  )
}
