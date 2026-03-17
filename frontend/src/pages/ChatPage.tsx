import { useMemo, useRef, useState } from 'react'
import { chatAPI, onlineAPI, sandboxAPI, voiceAPI } from '../api/client'
import { useAppState } from '../state/AppState'

// Hard system policy for model-driven autonomous tool usage.
const AGENT_SYSTEM_PROMPT = [
  'You are Roampal autonomous local agent.',
  'No manual confirmations and no additional planners.',
  'Model decides when and how to use web_search + sandbox.',
  'For any action-oriented user intent (text or voice), automatically run web_search first, then run required operations in sandbox.',
  'During execution, provide terminal-like step-by-step progress, then return one concise final result card.'
].join('\n')

const ACTION_INTENT_RE =
  /(найди|скачай|поищи|посмотри|уточни|установи|конвертируй|измени|запустить|запусти|проверь|разбери|проанализируй|find|search|download|inspect|install|convert|modify|run|verify|analy[sz]e|check|parse)/i

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

function speak(text: string) {
  if (!('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text.slice(0, 500))
  utterance.lang = 'ru-RU'
  window.speechSynthesis.speak(utterance)
}

function buildSandboxScript(query: string, results: Array<Record<string, any>>) {
  return [
    'from datetime import datetime',
    "def log(line):",
    "    print(f'[{datetime.now().strftime(\"%H:%M:%S\")}] {line}')",
    "log('$ agent start')",
    `query = ${JSON.stringify(query)}`,
    `results = ${JSON.stringify(results)}`,
    "log(f'query: {query}')",
    "log(f'search_results: {len(results)}')",
    "for idx, item in enumerate(results, 1):",
    "    title = item.get('title', 'Result')",
    "    url = item.get('url', '')",
    "    log(f'[{idx}] {title} -> {url}')",
    "log('$ sandbox analyze')",
    "if results:",
    "    log('analysis: using first results as context for autonomous decision')",
    "else:",
    "    log('analysis: no web results, fallback to local reasoning')",
    "log('$ done')"
  ].join('\n')
}

export default function ChatPage() {
  const { dialogs, activeDialogId, appendDialogMessage, appendTerminalLine, setActiveTab, selectedModel } = useAppState()

  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [listening, setListening] = useState(false)
  const [voiceSessionId, setVoiceSessionId] = useState<string | null>(null)
  const recognitionRef = useRef<BrowserRecognition | null>(null)

  const activeDialog = useMemo(() => dialogs.find((d) => d.id === activeDialogId), [dialogs, activeDialogId])
  const messages = activeDialog?.messages || []

  const runSandboxLive = async (code: string) => {
    let running = true
    const poll = window.setInterval(() => {
      if (running) appendTerminalLine({ stream: 'system', text: '[poll] sandbox running...' })
    }, 1000)

    try {
      appendTerminalLine({ stream: 'system', text: '$ sandbox execute --language python' })
      const result = await sandboxAPI.execute(code, 'python', 120)
      appendTerminalLine({ stream: result.exit_code === 0 ? 'stdout' : 'stderr', text: `exit_code=${result.exit_code}` })
      if (result.stdout) appendTerminalLine({ stream: 'stdout', text: result.stdout })
      if (result.stderr) appendTerminalLine({ stream: 'stderr', text: result.stderr })
      return result
    } finally {
      running = false
      window.clearInterval(poll)
    }
  }

  const autoToolsIfNeeded = async (text: string) => {
    if (!ACTION_INTENT_RE.test(text)) return null

    // Mandatory auto switch to terminal for agent actions.
    setActiveTab('terminal')
    appendTerminalLine({ stream: 'system', text: '$ agent detect-action-intent' })

    // Mandatory web_search before sandbox operations.
    appendTerminalLine({ stream: 'system', text: '$ web_search' })
    const searchResp = await onlineAPI.search(text, 5)
    const results = Array.isArray(searchResp?.results) ? searchResp.results : []
    appendTerminalLine({ stream: 'system', text: `web_search results=${results.length}` })

    // Sandbox operation with terminal-like output.
    const script = buildSandboxScript(text, results)
    const sandboxResp = await runSandboxLive(script)

    return { results, sandboxResp }
  }

  const sendMessage = async (raw?: string, source: 'text' | 'voice' = 'text') => {
    const text = (raw ?? input).trim()
    if (!text || loading || !activeDialog) return

    appendDialogMessage(activeDialog.id, { role: 'user', content: text })
    if (source === 'text') setInput('')
    setLoading(true)

    try {
      const toolContext = await autoToolsIfNeeded(text)

      const payloadMessages: Array<{ role: string; content: string }> = [
        { role: 'system', content: AGENT_SYSTEM_PROMPT },
        { role: 'system', content: `Selected model: ${selectedModel}` },
        ...[...messages, { id: 'tmp_user', role: 'user' as const, content: text, createdAt: Date.now() }].map((m) => ({
          role: m.role,
          content: m.content
        }))
      ]

      if (toolContext) {
        payloadMessages.push({
          role: 'system',
          content: `TOOL_CONTEXT: ${JSON.stringify({
            web_results_count: toolContext.results.length,
            sandbox_exit_code: toolContext.sandboxResp?.exit_code,
            sandbox_stdout_tail: String(toolContext.sandboxResp?.stdout || '').slice(-800),
            sandbox_stderr_tail: String(toolContext.sandboxResp?.stderr || '').slice(-800)
          })}`
        })
      }

      const response = await chatAPI.send(payloadMessages, true)
      const assistantText = response?.response || 'No response'

      // Exactly one final chat card with result summary.
      appendDialogMessage(activeDialog.id, { role: 'assistant', content: assistantText })
      speak(assistantText)
    } catch (error: any) {
      appendDialogMessage(activeDialog.id, {
        role: 'assistant',
        content: `❌ ${error?.response?.data?.detail || error?.message || 'request failed'}`
      })
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

    const voiceSession = await voiceAPI.startSession('duplex', 'female')
    setVoiceSessionId(voiceSession.voice_session_id)
    await voiceAPI.verifyMicrophone(
      voiceSession.voice_session_id,
      true,
      'browser_speech_recognition',
      'voice command path active'
    )

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      appendDialogMessage(activeDialogId, { role: 'assistant', content: '❌ SpeechRecognition is not supported.' })
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
    <div className="h-full flex flex-col overflow-hidden bg-white">
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`max-w-[85%] whitespace-pre-wrap rounded-xl px-3 py-2 text-sm ${
              msg.role === 'user' ? 'ml-auto bg-blue-600 text-white' : 'bg-neutral-100 text-neutral-900'
            }`}
          >
            {msg.content}
          </div>
        ))}
      </div>

      <div className="shrink-0 border-t border-neutral-200 p-2 flex gap-2">
        <button
          onClick={() => void toggleVoice()}
          className={`rounded-md px-3 py-2 text-sm text-white ${listening ? 'bg-red-600' : 'bg-neutral-700'}`}
        >
          {listening ? '🎙 stop' : '🎤 voice'}
        </button>

        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void sendMessage()
          }}
          placeholder="Type message or command..."
          className="min-w-0 flex-1 rounded-md border border-neutral-300 px-3 py-2 text-sm"
        />

        <button
          onClick={() => void sendMessage()}
          disabled={loading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-60"
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  )
}
